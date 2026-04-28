"""RAPTOR (Recursive Abstractive Processing for Tree-Organised Retrieval).

Clusters related chunks and recursively summarises them into
a hierarchical tree.  Every level is stored in its own Qdrant
collection so the retriever can choose the right abstraction.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SummaryNode:
    """A node in the RAPTOR tree."""

    text: str
    level: int = 0
    source_ids: list[str] = field(default_factory=list)
    children_text: str = ""

    @property
    def id(self) -> str:
        payload = f"{self.level}::{self.text}::{self.children_text}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


class RaptorTree:
    """Build a multi-level summary tree from raw text chunks.

    Level 0: original chunks (leaves)
    Level 1: summaries of ``chunk_size`` related chunks
    Level 2: summaries of level-1 summaries
    ... until one root remains.
    """

    COLLECTIONS = (
        "knowledge_chunks",     # level 0
        "knowledge_summaries",  # level 1+
    )

    def __init__(
        self,
        chunk_size: int = 5,
        levels: int = 3,
    ) -> None:
        self.chunk_size = chunk_size
        self.levels = levels

    def build(self, chunks: list[dict[str, Any]]) -> list[SummaryNode]:
        """Build all summary nodes from raw chunks."""
        all_nodes: list[SummaryNode] = []

        # Level 0
        leaves = [
            SummaryNode(
                text=c["text"],
                level=0,
                source_ids=[c.get("id", c["text"][:20])],
                children_text=c["text"],
            )
            for c in chunks
        ]
        all_nodes.extend(leaves)

        current_level = leaves
        for lvl in range(1, self.levels + 1):
            next_level: list[SummaryNode] = []
            for i in range(0, len(current_level), self.chunk_size):
                group = current_level[i : i + self.chunk_size]
                if not group:
                    continue
                summary_text = self._summarize([n.text for n in group])
                children_text = "\n".join(n.text for n in group)
                node = SummaryNode(
                    text=summary_text,
                    level=lvl,
                    source_ids=[n.id for n in group],
                    children_text=children_text,
                )
                next_level.append(node)
                all_nodes.append(node)
            current_level = next_level
            if len(current_level) <= 1:
                break

        return all_nodes

    # -------------------------------------------------------------------
    # Summarisation (heuristic — can be swapped for LLM call)
    # -------------------------------------------------------------------

    def _summarize(self, texts: list[str]) -> str:
        if not texts:
            return ""
        if len(texts) == 1:
            return texts[0][:300]

        sentences = []
        for t in texts:
            for s in t.replace("?", ".").replace("!", ".").split("."):
                s = s.strip()
                if s and len(s) > 20:
                    sentences.append(s)

        if not sentences:
            return " ".join(texts)[:400] + "..."

        # Score by overlap with other chunks
        scores = []
        for sent in sentences:
            words = set(sent.lower().split())
            score = sum(
                1
                for other in sentences
                if other != sent
                for w in words
                if w in other.lower()
            )
            scores.append(score)

        ranked = sorted(zip(scores, sentences), reverse=True)
        best = ranked[:3]
        best.sort(key=lambda x: sentences.index(x[1]))
        return ". ".join(s[1] for s in best) + "."
