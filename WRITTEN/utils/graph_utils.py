"""
Utilities for inspecting LangGraph topology.
"""
from __future__ import annotations
from typing import Any


def extract_graph_topology(graph_obj: Any) -> dict:
    """
    Given a compiled LangGraph object, extract:
    - node names
    - edges (source -> target)
    - entry point
    Returns a plain dict for serialization.
    """
    try:
        nodes = list(graph_obj.nodes.keys()) if hasattr(graph_obj, "nodes") else []
        # LangGraph stores edges in the graph's underlying structure
        edges = []
        if hasattr(graph_obj, "_graph"):
            for src, targets in graph_obj._graph.adj.items():
                for tgt in targets:
                    edges.append((src, tgt))
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}


def find_node_position(node_name: str, topology: dict) -> int:
    """Return the index of a node in topological order (rough BFS)."""
    nodes = topology.get("nodes", [])
    return nodes.index(node_name) if node_name in nodes else -1