#!/usr/bin/env python3
"""Deterministic semantic projections over normalized GitHub Project v2 items.

Project #2 remains the operational store. This module manufactures read-only
virtual views over the same admitted subject: property graph, triples, rows,
service/capability catalog, process events, and bounded LLM context.

The projector never infers domain semantics from free prose. Edges beyond the
structural Project/Issue/PR shape are created only from explicit memory metadata.
"""
from __future__ import annotations

import json
import re
from collections import deque
from typing import Any

SCHEMA = "chatgpt-project-semantic/v1"
VIEW_NAMES = {
    "model",
    "graph",
    "triples",
    "table",
    "catalog",
    "process",
    "context",
    "capabilities",
}
RELATION_KEYS = {
    "depends_on": "dependsOn",
    "requires": "requires",
    "produces": "produces",
    "consumes": "consumes",
    "supersedes": "supersedes",
    "unlocks": "unlocks",
    "derived_from": "wasDerivedFrom",
    "related_to": "relatedTo",
}
CAPABILITY_KEYS = ("capability", "capabilities", "provides")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

VIRTUAL_SURFACES = [
    {"id": "project-items", "kind": "object-store", "description": "Full-fidelity Project item/object inspection without requiring GraphQL knowledge."},
    {"id": "memory-kv", "kind": "key-value-memory", "description": "Stable-key shared memory over Project draft issues with bounded upsert/query operations."},
    {"id": "property-graph", "kind": "virtual-graph", "description": "Deterministic nodes and edges projected from Project structure and explicit memory relations."},
    {"id": "triples", "kind": "virtual-rdf-like", "description": "Subject/predicate/object projection over the property graph; no RDF database or synchronization required."},
    {"id": "table", "kind": "virtual-relational", "description": "Flat rows for SQL/dataframe-style consumers that do not understand graphs."},
    {"id": "capability-catalog", "kind": "service-catalog", "description": "Repositories, explicit capabilities, memory kinds, cells, standings, and tags as inspectable catalog objects."},
    {"id": "dependency-provenance", "kind": "knowledge-graph", "description": "Explicit requires/depends/produces/consumes/supersedes/unlocks/derived-from edges."},
    {"id": "process-events", "kind": "process-view", "description": "Memory updates projected as ordered event records for process-intelligence consumers."},
    {"id": "llm-context", "kind": "retrieval-view", "description": "Bounded text/type query with neighborhood expansion for context-efficient LLM inspection."},
]


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return _stable_json(value)
    return str(value)


def _node_id(prefix: str, value: Any) -> str:
    return f"{prefix}:{_text(value)}"


def _ref_id(value: Any, memory_keys: set[str]) -> str:
    text = _text(value).strip()
    if text in memory_keys:
        return _node_id("memory", text)
    if REPO_RE.match(text):
        return _node_id("repo", text)
    return _node_id("ref", text)


def _add_node(nodes: dict[str, dict[str, Any]], node_id: str, node_type: str, **props: Any) -> None:
    node = nodes.setdefault(node_id, {"id": node_id, "types": [], "properties": {}})
    if node_type not in node["types"]:
        node["types"].append(node_type)
        node["types"].sort()
    for key, value in props.items():
        if value is not None and value != "" and value != [] and value != {}:
            node["properties"][key] = value


def _add_edge(edges: dict[tuple[str, str, str], dict[str, Any]], source: str, predicate: str, target: str, **props: Any) -> None:
    if not source or not predicate or not target:
        return
    key = (source, predicate, target)
    edge = edges.setdefault(key, {"source": source, "predicate": predicate, "target": target, "properties": {}})
    for prop_key, value in props.items():
        if value is not None and value != "":
            edge["properties"][prop_key] = value


def build_model(project: dict[str, Any], items: list[dict[str, Any]], memory_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one canonical graph model from Project items plus decoded memory records."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    owner = project.get("owner") or "unknown"
    number = project.get("number") or "unknown"
    project_id = _node_id("project", f"{owner}/{number}")
    _add_node(nodes, project_id, "Project", title=project.get("title"), url=project.get("url"), owner=owner, number=number)

    memory_by_item = {record.get("item_id"): record for record in memory_records if record.get("item_id")}
    memory_keys = {_text((record.get("metadata") or {}).get("key")) for record in memory_records if (record.get("metadata") or {}).get("key")}

    for item in items:
        content = item.get("content") or {}
        item_id = item.get("item_id")
        memory = memory_by_item.get(item_id)
        metadata = (memory or {}).get("metadata") or {}
        key = metadata.get("key")
        semantic_id = _node_id("memory", key) if key else _node_id("item", item_id)
        item_type = item.get("type") or "ITEM"
        node_types = ["ProjectItem", item_type.title().replace("_", "")]
        if key:
            node_types.append("MemoryRecord")

        for node_type in node_types:
            _add_node(
                nodes,
                semantic_id,
                node_type,
                title=(memory or {}).get("title") or content.get("title"),
                body=(memory or {}).get("body") if memory else content.get("body"),
                url=content.get("url"),
                number=content.get("number"),
                state=content.get("state"),
                archived=bool(item.get("is_archived")),
                item_id=item_id,
                content_id=content.get("id") or (memory or {}).get("content_id"),
                memory_key=key,
                kind=metadata.get("kind"),
                cell=metadata.get("cell"),
                standing=metadata.get("standing"),
                generation=metadata.get("generation"),
                updated_at=metadata.get("updated_at"),
                head_sha=metadata.get("head_sha"),
            )
        _add_edge(edges, project_id, "contains", semantic_id)

        repo = content.get("repository") or metadata.get("repo")
        if repo:
            repo_id = _node_id("repo", repo)
            _add_node(nodes, repo_id, "Repository", name=repo)
            _add_edge(edges, semantic_id, "inRepository", repo_id)

        for label in content.get("labels") or []:
            label_name = label.get("name") if isinstance(label, dict) else label
            if not label_name:
                continue
            label_id = _node_id("label", label_name)
            _add_node(nodes, label_id, "Label", name=label_name, color=label.get("color") if isinstance(label, dict) else None)
            _add_edge(edges, semantic_id, "hasLabel", label_id)

        for assignee in content.get("assignees") or []:
            login = assignee.get("login") if isinstance(assignee, dict) else assignee
            if not login:
                continue
            actor_id = _node_id("actor", login)
            _add_node(nodes, actor_id, "Actor", login=login)
            _add_edge(edges, semantic_id, "assignedTo", actor_id)

        for field_name, field_value in sorted((item.get("field_values") or {}).items()):
            field_id = _node_id("field", field_name)
            _add_node(nodes, field_id, "ProjectField", name=field_name)
            _add_edge(edges, semantic_id, "hasFieldValue", field_id, value=field_value)

        for tag in metadata.get("tags") or []:
            tag_id = _node_id("tag", tag)
            _add_node(nodes, tag_id, "Tag", name=tag)
            _add_edge(edges, semantic_id, "hasTag", tag_id)

        for dimension, node_type, predicate in (
            ("kind", "MemoryKind", "hasKind"),
            ("cell", "Cell", "inCell"),
            ("standing", "Standing", "hasStanding"),
            ("generation", "Generation", "inGeneration"),
        ):
            value = metadata.get(dimension)
            if value:
                dim_id = _node_id(dimension, value)
                _add_node(nodes, dim_id, node_type, name=value)
                _add_edge(edges, semantic_id, predicate, dim_id)

        for capability_key in CAPABILITY_KEYS:
            for capability in _list(metadata.get(capability_key)):
                if capability is None or capability == "":
                    continue
                cap_id = _node_id("capability", capability)
                _add_node(nodes, cap_id, "Capability", name=capability)
                _add_edge(edges, semantic_id, "providesCapability", cap_id, source_key=capability_key)

        for relation_key, predicate in RELATION_KEYS.items():
            for target_value in _list(metadata.get(relation_key)):
                if target_value is None or target_value == "":
                    continue
                target_id = _ref_id(target_value, memory_keys)
                if target_id.startswith("ref:"):
                    _add_node(nodes, target_id, "Reference", value=_text(target_value))
                elif target_id.startswith("repo:"):
                    _add_node(nodes, target_id, "Repository", name=_text(target_value))
                _add_edge(edges, semantic_id, predicate, target_id, source_key=relation_key)

    return {"schema": SCHEMA, "project": project, "nodes": sorted(nodes.values(), key=lambda n: n["id"]), "edges": sorted(edges.values(), key=lambda e: (e["source"], e["predicate"], e["target"]))}


def graph_view(model: dict[str, Any]) -> dict[str, Any]:
    return {"schema": SCHEMA, "view": "graph", "project": model["project"], "nodes": model["nodes"], "edges": model["edges"], "node_count": len(model["nodes"]), "edge_count": len(model["edges"])}


def triples_view(model: dict[str, Any], *, include_properties: bool = True) -> dict[str, Any]:
    triples: list[dict[str, Any]] = []
    for edge in model["edges"]:
        triples.append({"subject": edge["source"], "predicate": edge["predicate"], "object": edge["target"], "object_type": "iri"})
    if include_properties:
        for node in model["nodes"]:
            for node_type in node["types"]:
                triples.append({"subject": node["id"], "predicate": "type", "object": node_type, "object_type": "literal"})
            for key, value in sorted(node["properties"].items()):
                triples.append({"subject": node["id"], "predicate": key, "object": value, "object_type": "literal"})
    triples.sort(key=lambda t: (t["subject"], t["predicate"], _stable_json(t["object"])))
    return {"schema": SCHEMA, "view": "triples", "project": model["project"], "triples": triples, "triple_count": len(triples)}


def _first_edge_target(model: dict[str, Any], source: str, predicate: str, strip_prefix: str | None = None) -> str | None:
    for edge in model["edges"]:
        if edge["source"] == source and edge["predicate"] == predicate:
            target = edge["target"]
            if strip_prefix and target.startswith(strip_prefix):
                return target[len(strip_prefix) :]
            return target
    return None


def table_view(model: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for node in model["nodes"]:
        if "ProjectItem" not in node["types"]:
            continue
        props = node["properties"]
        rows.append({"id": node["id"], "types": node["types"], "title": props.get("title"), "url": props.get("url"), "repository": _first_edge_target(model, node["id"], "inRepository", strip_prefix="repo:"), "state": props.get("state"), "memory_key": props.get("memory_key"), "kind": props.get("kind"), "cell": props.get("cell"), "standing": props.get("standing"), "generation": props.get("generation"), "updated_at": props.get("updated_at"), "archived": props.get("archived", False)})
    rows.sort(key=lambda row: row["id"])
    return {"schema": SCHEMA, "view": "table", "project": model["project"], "rows": rows, "row_count": len(rows)}


def catalog_view(model: dict[str, Any]) -> dict[str, Any]:
    by_type: dict[str, list[dict[str, Any]]] = {}
    for node in model["nodes"]:
        for node_type in node["types"]:
            if node_type in {"Repository", "Capability", "MemoryKind", "Cell", "Standing", "Generation", "Tag"}:
                by_type.setdefault(node_type, []).append(node)
    for values in by_type.values():
        values.sort(key=lambda node: node["id"])
    return {"schema": SCHEMA, "view": "catalog", "project": model["project"], "virtual_surfaces": VIRTUAL_SURFACES, "catalog": by_type, "counts": {key: len(value) for key, value in sorted(by_type.items())}}


def process_view(model: dict[str, Any]) -> dict[str, Any]:
    events = []
    for node in model["nodes"]:
        if "MemoryRecord" not in node["types"]:
            continue
        props = node["properties"]
        if not props.get("updated_at"):
            continue
        events.append({"event_id": f"event:{node['id']}@{props['updated_at']}", "time": props["updated_at"], "activity": props.get("kind") or "memory.updated", "object": node["id"], "cell": props.get("cell"), "standing": props.get("standing"), "generation": props.get("generation"), "head_sha": props.get("head_sha")})
    events.sort(key=lambda event: (event["time"], event["event_id"]))
    return {"schema": SCHEMA, "view": "process", "project": model["project"], "events": events, "event_count": len(events), "conformance": "UNSUPPORTED_UNTIL_INDEPENDENT_VALIDATOR"}


def capabilities_view(model: dict[str, Any]) -> dict[str, Any]:
    return {"schema": SCHEMA, "view": "capabilities", "project": model["project"], "virtual_surfaces": VIRTUAL_SURFACES, "operations": ["project.snapshot", "project.items", "project.semantic", "memory.create", "memory.read", "memory.update", "memory.upsert", "memory.query", "memory.archive", "memory.delete"], "projection_law": "one operational Project subject; zero synchronized graph/relational copies"}


def context_view(model: dict[str, Any], *, query: str = "", node_types: list[str] | None = None, edge_predicates: list[str] | None = None, hops: int = 1, limit: int = 50) -> dict[str, Any]:
    """Return text/type matches plus a bounded graph neighborhood (0..2 hops)."""
    hops = max(0, min(int(hops), 2))
    limit = max(1, min(int(limit), 200))
    query_cf = query.casefold().strip()
    wanted_types = set(node_types or [])
    wanted_predicates = set(edge_predicates or [])
    nodes_by_id = {node["id"]: node for node in model["nodes"]}

    def matches(node: dict[str, Any]) -> bool:
        if wanted_types and not wanted_types.intersection(node["types"]):
            return False
        if not query_cf:
            return True
        return query_cf in _stable_json(node).casefold()

    seeds = [node["id"] for node in model["nodes"] if matches(node)][:limit]
    selected = set(seeds)
    frontier = deque((seed, 0) for seed in seeds)
    adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for edge in model["edges"]:
        if wanted_predicates and edge["predicate"] not in wanted_predicates:
            continue
        adjacency.setdefault(edge["source"], []).append((edge["target"], edge))
        adjacency.setdefault(edge["target"], []).append((edge["source"], edge))

    while frontier and len(selected) < limit:
        current, depth = frontier.popleft()
        if depth >= hops:
            continue
        for neighbor, _edge in adjacency.get(current, []):
            if neighbor not in selected and neighbor in nodes_by_id:
                selected.add(neighbor)
                frontier.append((neighbor, depth + 1))
                if len(selected) >= limit:
                    break

    selected_edges = [edge for edge in model["edges"] if edge["source"] in selected and edge["target"] in selected and (not wanted_predicates or edge["predicate"] in wanted_predicates)]
    return {"schema": SCHEMA, "view": "context", "project": model["project"], "query": query, "hops": hops, "seed_count": len(seeds), "nodes": [nodes_by_id[node_id] for node_id in sorted(selected)], "edges": sorted(selected_edges, key=lambda e: (e["source"], e["predicate"], e["target"])), "truncated": len(selected) >= limit}


def render_view(model: dict[str, Any], view: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}
    if view not in VIEW_NAMES:
        raise ValueError(f"unsupported semantic view: {view}")
    if view == "model":
        return {**model, "view": "model"}
    if view == "graph":
        return graph_view(model)
    if view == "triples":
        return triples_view(model, include_properties=bool(options.get("include_properties", True)))
    if view == "table":
        return table_view(model)
    if view == "catalog":
        return catalog_view(model)
    if view == "process":
        return process_view(model)
    if view == "context":
        return context_view(model, query=str(options.get("query", "")), node_types=[str(v) for v in (options.get("node_types") or [])], edge_predicates=[str(v) for v in (options.get("edge_predicates") or [])], hops=int(options.get("hops", 1)), limit=int(options.get("limit", 50)))
    if view == "capabilities":
        return capabilities_view(model)
    raise AssertionError(view)
