#!/usr/bin/env python3
"""Semantic extension layer for the bounded Project v2 memory proxy.

This wrapper preserves every operation from ``project_memory_proxy.py`` and adds
read-only virtual projections over the exact same Project #2 subject.  The base
proxy still owns authority, transport, validation, receipts, and mutations.
"""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import project_memory_proxy as base
import project_semantic_projection as semantic
import project_vision_2030 as vision_2030

SEMANTIC_OPERATIONS = {
    "project.semantic",
    "project.graph",
    "project.graph.query",
    "project.tables",
    "project.triples",
    "project.jsonld",
    "project.services",
    "project.ocel",
    "project.context",
    "project.vision2030",
}

_ORIGINAL_EXECUTE_REQUEST = base.execute_request
base.ALLOWED_OPERATIONS.update(SEMANTIC_OPERATIONS)


def _bounded_int(payload: dict[str, Any], key: str, default: int, maximum: int) -> int:
    value = int(payload.get(key, default))
    if value < 1:
        raise base.ProxyError(f"{key} must be positive", standing="REFUSED", reason="INVALID_REQUEST")
    return min(value, maximum)


def _virtual_project(store: base.ProjectMemoryStore, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    max_items = _bounded_int(payload, "max_items", 5000, 5000)
    max_facts = _bounded_int(payload, "max_facts", 100_000, 250_000)
    include_archived = bool(payload.get("include_archived", False))
    include_bodies = bool(payload.get("include_bodies", True))
    items, truncated = store.project_items(
        types=payload.get("types"),
        include_archived=include_archived,
        max_items=max_items,
    )
    for item in items:
        content = item.get("content") or {}
        metadata, cleaned = base.decode_memory_body(content.get("body") or "")
        if metadata:
            item["memory"] = {"metadata": metadata, "body": cleaned}
    project = {
        "owner": store.project.owner,
        "number": store.project.number,
        "id": store.project.node_id,
        "title": store.project.title,
        "url": store.project.url,
    }
    graph = semantic.build_virtual_project(
        project,
        items,
        include_bodies=include_bodies,
        max_facts=max_facts,
    )
    graph["source_truncated"] = truncated
    return graph, truncated


def execute_request(store: base.ProjectMemoryStore, request: dict[str, Any], operation: str) -> Any:
    if operation not in SEMANTIC_OPERATIONS:
        return _ORIGINAL_EXECUTE_REQUEST(store, request, operation)

    payload = request.get("payload") or {}
    graph, source_truncated = _virtual_project(store, payload)
    query = payload.get("query") or {}

    if operation == "project.semantic":
        result = semantic.select_views(graph, payload.get("views"), query=query)
    elif operation == "project.graph":
        result = {
            "schema": graph["schema"],
            "project": graph["project"],
            "observed_at": graph["observed_at"],
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "facts": graph["facts"],
            "stats": graph["stats"],
        }
    elif operation == "project.graph.query":
        result = semantic.query_graph(graph, query)
        result.update({"schema": graph["schema"], "project": graph["project"], "observed_at": graph["observed_at"]})
    elif operation == "project.tables":
        result = {"schema": graph["schema"], "project": graph["project"], "observed_at": graph["observed_at"], **graph["tables"]}
    elif operation == "project.triples":
        result = {"schema": graph["schema"], "project": graph["project"], "observed_at": graph["observed_at"], "triples": graph["triples"]}
    elif operation == "project.jsonld":
        result = graph["jsonld"]
    elif operation == "project.services":
        result = {"schema": graph["schema"], "project": graph["project"], "observed_at": graph["observed_at"], **graph["services"]}
    elif operation == "project.ocel":
        result = {"schema": graph["schema"], "project": graph["project"], "observed_at": graph["observed_at"], "ocel": graph["ocel"]}
    elif operation == "project.context":
        result = semantic.context_projection(graph, query)
    elif operation == "project.vision2030":
        result = vision_2030.project(graph, query)
    else:  # pragma: no cover - guarded by SEMANTIC_OPERATIONS
        raise AssertionError(operation)

    if isinstance(result, dict):
        result["source_truncated"] = source_truncated
        result["authority"] = "READ_ONLY_VIRTUAL_PROJECTION"
        result["canonical_subject"] = "GitHub Project v2 #2"
    return result


base.execute_request = execute_request


if __name__ == "__main__":
    raise SystemExit(base.main())
