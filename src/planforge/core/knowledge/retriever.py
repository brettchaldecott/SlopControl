"""Retrieval engine.

Queries both ``knowledge_chunks`` (raw) and ``knowledge_summaries``
(RAPTOR) collections, merges and ranks results, and optionally
filters by source / abstraction level.
"""

from __future__ import annotations

import logging
from typing import Any

from .backends import VectorBackend, create_backend

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """Retrieve relevant knowledge chunks for a given query.

    Searches raw chunks and RAPTOR summaries simultaneously, then
    deduplicates and re-ranks by score.
    """

    def __init__(
        self,
        backend: VectorBackend | None = None,
        chunk_weight: float = 1.0,
        summary_weight: float = 1.2,
    ) -> None:
        self.backend = backend or create_backend()
        self.chunk_weight = chunk_weight
        self.summary_weight = summary_weight

    def search(
        self,
        query: str,
        k: int = 5,
        filter_source: str | None = None,
        include_summaries: bool = True,
    ) -> list[dict[str, Any]]:
        """Search knowledge base and return top-k relevant chunks.

        Args:
            query: Natural language query.
            k: Number of results to return.
            filter_source: Only return chunks from this source file.
            include_summaries: Also search RAPTOR summary collection.

        Returns:
            List of chunks with ``id``, ``text``, ``source``, ``level``, ``score``.
        """
        results: dict[str, dict[str, Any]] = {}

        # 1. Search raw chunks
        chunk_hits = self.backend.search(
            query=query,
            collection="knowledge_chunks",
            k=k * 2,
            filter_source=filter_source,
        )
        for h in chunk_hits:
            h["score"] = h.get("score", 1.0) * self.chunk_weight
            results[h["id"]] = h

        # 2. Search RAPTOR summaries
        if include_summaries:
            summary_hits = self.backend.search(
                query=query,
                collection="knowledge_summaries",
                k=k,
                filter_source=filter_source,
            )
            for h in summary_hits:
                h["score"] = h.get("score", 1.0) * self.summary_weight
                results[h["id"]] = h

        # 3. Sort by score, return top-k
        ranked = sorted(results.values(), key=lambda x: x["score"], reverse=True)
        return ranked[:k]

    def get_context_string(
        self,
        query: str,
        k: int = 5,
        filter_source: str | None = None,
        include_summaries: bool = True,
    ) -> str:
        """Return a single concatenated context string for prompt injection."""
        hits = self.search(query, k, filter_source, include_summaries)
        parts = []
        for h in hits:
            header = f"Source: {h.get('source', 'unknown')} (level={h.get('level', 0)})"
            parts.append(f"{header}\n{h['text']}")
        return "\n\n---\n\n".join(parts)
