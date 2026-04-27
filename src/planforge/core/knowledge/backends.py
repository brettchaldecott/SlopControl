"""Pluggable vector backends for the PlanForge Knowledge Base.

Primary: Qdrant local mode with built-in FastEmbed (ONNX, CPU-only).
Fallback: Brute-force cosine (zero dependencies).
"""

from __future__ import annotations

import logging
import math
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding helper (delegates to sentence-transformers if available,
# otherwise uses a naive fallback so the brute-force backend works)
# ---------------------------------------------------------------------------

def _naive_embed(texts: list[str], _dim: int = 384) -> list[list[float]]:
    """Fallback embedding: simple character-ngram hashing into fixed dims."""
    results = []
    for text in texts:
        vec = [0.0] * _dim
        text = text.lower()
        for i in range(len(text) - 2):
            idx = hash((text[i], text[i + 1], text[i + 2])) % _dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        results.append([v / norm for v in vec])
    return results


def _get_embedder():
    """Return the best available embedding function."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Loaded sentence-transformers for embeddings")

        def embed(texts: list[str]) -> list[list[float]]:
            return model.encode(texts).tolist()
        return embed
    except Exception:
        logger.warning("sentence-transformers unavailable; using naive fallback embeddings")
        return _naive_embed


EMBED = _get_embedder()


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class IndexEntry(Protocol):
    id: str
    text: str
    source: str
    level: int


class VectorBackend(ABC):
    """Abstract vector index backend."""

    @abstractmethod
    def upsert(self, entries: list[dict[str, Any]], collection: str) -> None:
        """Add or update entries with embeddings."""
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        collection: str,
        k: int = 5,
        filter_source: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top-k nearest entries."""
        ...

    @abstractmethod
    def delete_source(self, source: str, collection: str) -> None:
        """Remove all chunks belonging to a given source file."""
        ...

    @abstractmethod
    def persist(self) -> None:
        """Flush index to disk."""
        ...


# ---------------------------------------------------------------------------
# 1. Qdrant local mode (primary) — single dependency, built-in embeddings
# ---------------------------------------------------------------------------

class QdrantBackend(VectorBackend):
    """Qdrant in local mode with built-in FastEmbed.

    Creates a directory on disk and uses ONNX Runtime for
    embeddings.  Switching to a remote Qdrant server later is
    only a change of the ``path`` init parameter to ``url``.

    Collections used:
        ``knowledge_chunks``    – raw note chunks
        ``knowledge_summaries`` – RAPTOR tree summaries
    """

    def __init__(
        self,
        path: str,
        dim: int = 384,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        from qdrant_client import QdrantClient

        self.dim = dim
        self.model = model
        self._path = path
        self._client = QdrantClient(path=path)
        self._ensure_collections()

    # -------------------------------------------------------------------
    # Collection helpers
    # -------------------------------------------------------------------

    def _ensure_collections(self) -> None:
        from qdrant_client import models

        for name, distance in (
            ("knowledge_chunks", models.Distance.COSINE),
            ("knowledge_summaries", models.Distance.COSINE),
        ):
            self._client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=self.dim, distance=distance),
                exist_ok=True,
            )

    # -------------------------------------------------------------------
    # FastEmbed helper
    # -------------------------------------------------------------------

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Use Qdrant's built-in FastEmbed to avoid heavy PyTorch deps."""
        from qdrant_client import models as qmodels

        docs = [qmodels.Document(text=t, model=self.model) for t in texts]
        # compute returns a list of embedding vectors
        return self._client.compute(docs)  # type: ignore[return-value]

    # -------------------------------------------------------------------
    # VectorBackend interface
    # -------------------------------------------------------------------

    def upsert(self, entries: list[dict[str, Any]], collection: str) -> None:
        from qdrant_client.models import PointStruct

        if not entries:
            return

        texts = [e["text"] for e in entries]
        vectors = self._embed(texts)

        points = []
        for e, vec in zip(entries, vectors):
            points.append(
                PointStruct(
                    id=e["id"],
                    vector=vec,
                    payload={
                        "text": e["text"],
                        "source": e.get("source", ""),
                        "level": e.get("level", 0),
                    },
                )
            )

        self._client.upsert(collection_name=collection, points=points)

    def search(
        self,
        query: str,
        collection: str,
        k: int = 5,
        filter_source: str | None = None,
    ) -> list[dict[str, Any]]:
        from qdrant_client import models as qmodels

        # Compute query embedding
        (qvec,) = self._embed([query])

        must: list[Any] = []
        if filter_source:
            must.append(
                qmodels.FieldCondition(
                    key="source",
                    match=qmodels.MatchValue(value=filter_source),
                )
            )

        query_filter = qmodels.Filter(must=must) if must else None

        results = self._client.query_points(
            collection_name=collection,
            query=qvec,
            query_filter=query_filter,
            limit=k,
        )

        return [
            {
                "id": p.id,
                "text": p.payload.get("text", ""),
                "source": p.payload.get("source", ""),
                "level": p.payload.get("level", 0),
                "score": p.score,
            }
            for p in results.points
        ]

    def delete_source(self, source: str, collection: str) -> None:
        from qdrant_client import models as qmodels

        self._client.delete(
            collection_name=collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="source",
                            match=qmodels.MatchValue(value=source),
                        )
                    ]
                )
            ),
        )

    def persist(self) -> None:
        # Qdrant client already writes to disk; just close nicely.
        self._client.close()


# ---------------------------------------------------------------------------
# 2. Brute-force fallback (zero deps, always works)
# ---------------------------------------------------------------------------

class BruteForceBackend(VectorBackend):
    """In-memory cosine similararity search."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self._entries: dict[str, dict[str, Any]] = {}
        self._embeddings: dict[str, list[float]] = {}

    def upsert(self, entries: list[dict[str, Any]], collection: str) -> None:
        texts = [e["text"] for e in entries]
        embeddings = EMBED(texts)
        for e, emb in zip(entries, embeddings):
            key = f"{collection}:{e['id']}"
            self._entries[key] = e
            self._embeddings[key] = emb

    def search(
        self,
        query: str,
        collection: str,
        k: int = 5,
        filter_source: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._embeddings:
            return []
        (qvec,) = EMBED([query])

        scores: list[tuple[float, str]] = []
        for key, emb in self._embeddings.items():
            if not key.startswith(f"{collection}:"):
                continue
            dot = sum(a * b for a, b in zip(qvec, emb))
            scores.append((dot, key))
        scores.sort(reverse=True)

        results = []
        for _, key in scores[:k]:
            e = self._entries[key]
            if filter_source and e.get("source") != filter_source:
                continue
            results.append(e)
        return results

    def delete_source(self, source: str, collection: str) -> None:
        to_remove = [
            k for k, e in self._entries.items()
            if k.startswith(f"{collection}:") and e.get("source") == source
        ]
        for k in to_remove:
            self._entries.pop(k, None)
            self._embeddings.pop(k, None)

    def persist(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_DEFAULT_PATH = os.environ.get(
    "PLANFORGE_KNOWLEDGE_PATH",
    os.path.expanduser("~/.planforge/knowledge")
)


def create_backend(
    path: str | None = None,
    dim: int = 384,
    force: str | None = None,
) -> VectorBackend:
    """Create the best available backend.

    Args:
        path: Storage path for persistent backends (default: ``~/.planforge/knowledge``).
        dim: Embedding dimension.
        force: ``"qdrant"``, ``"brute"``, or ``None`` for auto-detect.
    """
    if force == "brute":
        logger.info("Using brute-force backend (explicit)")
        return BruteForceBackend(dim=dim)

    if force in (None, "qdrant"):
        try:
            # Verify qdrant-client is available. FastEmbed may require
            # the optional ``[fastembed]`` extra to compute embeddings locally.
            import qdrant_client  # noqa: F401
            import fastembed  # noqa: F401
            p = path or _DEFAULT_PATH
            Path(p).mkdir(parents=True, exist_ok=True)
            logger.info("Using Qdrant local backend at %s", p)
            return QdrantBackend(p, dim=dim)
        except Exception as exc:
            logger.warning("Qdrant unavailable: %s", exc)

    logger.info("Using brute-force backend (final fallback)")
    return BruteForceBackend(dim=dim)
