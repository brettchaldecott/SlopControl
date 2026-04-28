"""Auto-ingestion – watch a directory of markdown notes and re-index."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .indexer import KnowledgeIndexer

logger = logging.getLogger(__name__)


class KnowledgeIngest:
    """Watch and ingest markdown files from a given knowledge directory.

    Currently simple (one-shot scan); a future version may use
    ``watchdog`` for true filesystem watching.
    """

    def __init__(
        self,
        indexer: KnowledgeIndexer | None = None,
        vault_paths: list[str] | None = None,
    ) -> None:
        self.indexer = indexer or KnowledgeIndexer()
        self.vault_paths = vault_paths or []

    def scan(self) -> None:
        """Scan all ``.md`` files in all vault paths and reindex."""
        for root in self.vault_paths:
            for path in Path(root).rglob("*.md"):
                try:
                    self.indexer.index_file(path)
                except Exception as exc:
                    logger.error("Failed to index %s: %s", path, exc, exc_info=True)
        self.indexer.persist()

    def scan_source(self, path: str) -> None:
        """Reindex a single note file or directory tree."""
        p = Path(path)
        if p.is_dir():
            for note in p.rglob("*.md"):
                try:
                    self.indexer.reindex_source(note)
                except Exception as exc:
                    logger.error("Failed to reindex %s: %s", note, exc, exc_info=True)
        else:
            try:
                self.indexer.reindex_source(p)
            except Exception as exc:
                logger.error("Failed to reindex %s: %s", p, exc, exc_info=True)
        self.indexer.persist()
