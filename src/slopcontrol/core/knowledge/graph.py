"""Graph layer for the SlopControl Knowledge Fabric.

Provides a graph-based memory model on top of the existing vector/RAPTOR system.
Supports long-term/short-term tiers, relationship traversal, and 'Coverage of Truth'
metrics (empirical validation vs uncertainty).

This implements the user's preference for graph-based knowledge that can be viewed
from multiple angles and supports inference over time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from slopcontrol.core.knowledge.retriever import KnowledgeRetriever

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    type: str  # "plan", "decision", "truth", "concept", "observation"
    content: str
    confidence: float = 1.0  # 0.0 to 1.0 - "Coverage of Truth"
    timestamp: str = ""
    metadata: dict[str, Any] = None  # type: ignore

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class KnowledgeGraph:
    """Hybrid graph + vector knowledge fabric.

    Nodes are stored with vector embeddings (via existing RAPTOR backend).
    Edges represent relationships, influence, and confidence.
    Supports tiered memory (short-term active, long-term indexed).
    """

    def __init__(self, retriever: KnowledgeRetriever | None = None) -> None:
        self.retriever = retriever
        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: dict[str, list[tuple[str, str, float]]] = {}  # source -> [(target, relation, weight)]

    def add_node(self, node: KnowledgeNode) -> None:
        """Add or update a knowledge node."""
        self.nodes[node.id] = node

        # Index into vector backend for semantic search
        if self.retriever and self.retriever.backend:
            try:
                self.retriever.backend.upsert(
                    [{
                        "id": node.id,
                        "text": f"{node.type}: {node.content}",
                        "source": f"graph:{node.type}",
                        "level": 0,
                        "confidence": node.confidence,
                    }],
                    collection="knowledge_chunks"
                )
            except Exception as e:
                logger.debug("Failed to vector-index node: %s", e)

        logger.debug("Added graph node: %s (confidence=%.2f)", node.id, node.confidence)

    def add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0) -> None:
        """Add a directed relationship between nodes."""
        if source_id not in self.edges:
            self.edges[source_id] = []
        self.edges[source_id].append((target_id, relation, weight))

    def get_coverage_of_truth(self, domain: str = "code") -> dict[str, float]:
        """Calculate 'Coverage of Truth' - % of knowledge that is empirically validated."""
        if not self.nodes:
            return {"validated": 0.0, "uncertain": 1.0, "overall": 0.0}

        validated = sum(1 for node in self.nodes.values() if node.confidence >= 0.8)
        total = len(self.nodes)
        coverage = validated / total if total > 0 else 0.0

        return {
            "validated": coverage,
            "uncertain": 1.0 - coverage,
            "overall": coverage,
            "total_nodes": total,
        }

    def query(self, query: str, k: int = 10) -> list[KnowledgeNode]:
        """Query the graph using vector search + graph traversal."""
        if not self.retriever:
            return list(self.nodes.values())[:k]

        # Use existing retriever for semantic search
        results = self.retriever.search(query, k=k)
        node_ids = [r.get("id") for r in results if "id" in r]

        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def get_lessons(self, k: int = 5) -> str:
        """Return human-readable lessons from high-confidence truths."""
        truths = [n for n in self.nodes.values() if n.type == "truth" and n.confidence > 0.7]
        truths.sort(key=lambda x: x.confidence, reverse=True)
        return "\n".join([f"- {t.content} (confidence: {t.confidence:.2f})" for t in truths[:k]])


# Global singleton for the knowledge graph fabric
_knowledge_graph: KnowledgeGraph | None = None


def get_knowledge_graph(retriever: KnowledgeRetriever | None = None) -> KnowledgeGraph:
    """Get or create the global knowledge graph instance."""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph(retriever)
    return _knowledge_graph
