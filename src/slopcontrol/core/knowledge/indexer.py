"""Indexer – chunk markdown notes and upsert into the vector backend.

Supports both raw chunks (level 0) and RAPTOR tree summaries
(level 1+).  Each level is stored in its own Qdrant collection.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from .backends import VectorBackend, create_backend
from .raptor import RaptorTree

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 100


class KnowledgeIndexer:
    """Index markdown knowledge notes into vector collections."""

    def __init__(
        self,
        backend: VectorBackend | None = None,
        chunk_size: int = _CHUNK_SIZE,
        raptor: bool = True,
    ) -> None:
        self.backend = backend or create_backend()
        self.chunk_size = chunk_size
        self.raptor = raptor
        self._raptor_tree = RaptorTree(chunk_size=5, levels=3) if raptor else None

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def index_file(self, path: Path, source: str | None = None) -> None:
        """Read a markdown file, chunk it, and upsert."""
        source_name = source or str(path)
        text = path.read_text(encoding="utf-8")
        self.index_text(text, source=source_name)
        logger.info("Indexed %s", source_name)

    def index_text(self, text: str, source: str) -> None:
        """Index arbitrary text under a given source identifier."""
        chunks = self._split(text)

        chunk_entries = [
            {
                "id": self._chunk_id(source, i, c),
                "text": c,
                "source": source,
                "level": 0,
            }
            for i, c in enumerate(chunks)
        ]

        self.backend.upsert(chunk_entries, collection="knowledge_chunks")

        if self._raptor_tree:
            summary_nodes = self._raptor_tree.build(chunk_entries)
            summary_entries = [
                {
                    "id": node.id,
                    "text": node.text,
                    "source": source,
                    "level": node.level,
                }
                for node in summary_nodes
                if node.level > 0
            ]
            if summary_entries:
                self.backend.upsert(summary_entries, collection="knowledge_summaries")

    def reindex_source(self, path: Path, source: str | None = None) -> None:
        """Delete previous entries for a source, then re-index."""
        source_name = source or str(path)
        self.backend.delete_source(source_name, collection="knowledge_chunks")
        self.backend.delete_source(source_name, collection="knowledge_summaries")
        self.index_file(path, source=source_name)

    def persist(self) -> None:
        self.backend.persist()

    # -------------------------------------------------------------------
    # Chunking
    # -------------------------------------------------------------------

    def _split(self, text: str) -> list[str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        current = ""

        for para in paragraphs:
            if current and len(current) + len(para) > self.chunk_size:
                chunks.append(current.strip())
                current = para
            else:
                current = (current + "\n\n" + para).strip()

        if current:
            chunks.append(current.strip())

        return chunks

    @staticmethod
    def _chunk_id(source: str, idx: int, text: str) -> str:
        payload = f"{source}:{idx}:{text[:40]}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
