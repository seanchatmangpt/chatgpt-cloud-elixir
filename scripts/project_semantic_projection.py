#!/usr/bin/env python3
"""Deterministic virtual semantic projections over GitHub Project v2 items.

Project #2 remains the sole operational subject. This module creates read-only,
in-memory projections over an observed item set: property graph, facts/triples,
relational tables, JSON-LD, service catalog, OCEL-shaped process evidence, and a
compact LLM context view. No projection is a second database and none carries
actuation authority.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
import datetime as dt
import hashlib
import json
import re
from typing import Any, Iterable

SCHEMA = "project-two-semantic/v1"
PROJECT_TWO_BASE = "urn:project-two:"
HEX_SHA_RE = re.compile(r"^[0-9a-f]{7,64}$", re.I)
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MEMORY_KEY_RE = re.compile(r"^[A-Za-z0-9_.:-]+(?:/[A-Za-z0-9_.:@-]+)+$")

JSONLD_CONTEXT = {
    "@version": 1.1,
    "pt": "https://project-two.chatman.dev/vocab/",
    "prov": "http://www.w3.org/ns/prov#",
    "dcterms": "http://purl.org/dc/terms/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "schema": "https://schema.org/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "doap": "http://usefulinc.com/ns/doap#",
}

PLATFORM_CAPABILITIES = [
    ("memory-kv", ["memory.create", "memory.read", "memory.update", "memory.upsert", "memory.query", "memory.archive", "memory.delete"]),
    ("project-object-store", ["project.snapshot", "project.items"]),
    ("property-graph", ["project.graph", "project.graph.query"]),
    ("semantic-facts", ["project.triples"]),
    ("json-ld", ["project.jsonld"]),
    ("relational-projection", ["project.tables"]),
    ("service-catalog", ["project.services"]),
    ("process-evidence", ["project.ocel"]),
    ("llm-context", ["project.context"]),
]

REFERENCE_RELATIONS = {
    "memory_keys_consumed": "CONSUMES_MEMORY",
    "memory_keys_updated": "UPDATES_MEMORY",
    "memory_created": "CREATES_MEMORY",
    "memory_keys_created": "CREATES_MEMORY",
    "requires": "REQUIRES",
    "dependencies": "DEPENDS_ON",
    "dependency_keys": "DEPENDS_ON",
    "unlocks": "UNLOCKS",
    "supersedes": "SUPERSEDES",
    "derived_from": "DERIVED_FROM",
    "receipts": "HAS_RECEIPT",
    "receipt": "HAS_RECEIPT",
    "replay": "HAS_REPLAY",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def _urn(kind: str, value: str) -> str:
    safe = value.strip()
    if kind in {"repository", "memory", "commit", "actor", "tag", "label"} and len(safe) <= 180:
        return f"{PROJECT_TWO_BASE}{kind}:{safe}"
    return f"{PROJECT_TWO_BASE}{kind}:{_digest(safe)}"


def _stable_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def _flatten(prefix: str, value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key in sorted(value, key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten(path, value[key])
    elif isinstance(value, list):
        for index, entry in enumerate(value):
            path = f"{prefix}[{index}]"
            yield from _flatten(path, entry)
    else:
        yield prefix, value


def _listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _reference_target(value: Any, relation_key: str | None = None) -> tuple[str, str] | None:
    if not isinstance(value, (str, int)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if relation_key and relation_key.startswith("memory") and MEMORY_KEY_RE.match(text):
        return _urn("memory", text), "MemoryKey"
    if REPO_RE.match(text):
        return _urn("repository", text), "Repository"
    if HEX_SHA_RE.match(text):
        return _urn("commit", text.lower()), "Commit"
    if MEMORY_KEY_RE.match(text) and (text.startswith("dfcm/") or text.startswith("project/")):
        return _urn("memory", text), "MemoryKey"
    if relation_key in REFERENCE_RELATIONS:
        return _urn("reference", text), "Reference"
    return None


def _relation_predicate(metadata_key: str) -> str:
    return REFERENCE_RELATIONS.get(metadata_key, f"METADATA_{re.sub(r'[^A-Za-z0-9]+', '_', metadata_key).strip('_').upper()}")


def build_virtual_project(
    project: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    observed_at: str | None = None,
    include_bodies: bool = True,
    max_facts: int = 100_000,
) -> dict[str, Any]:
    """Build one canonical semantic IR from full-fidelity Project item rows.

    Items may carry an optional ``memory`` object with decoded ``metadata`` and
    cleaned ``body``. The function performs no inference from free prose: typed
    graph edges arise only from explicit Project fields or whitelisted metadata
    relation keys. All remaining scalar metadata is preserved as facts.
    """
    observed_at = observed_at or utc_now()
    node_by_id: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str, str]] = set()

    def add_node(node_id: str, types: list[str], label: str, properties: dict[str, Any] | None = None, source: dict[str, Any] | None = None) -> None:
        node = node_by_id.get(node_id)
        if node is None:
            node_by_id[node_id] = {
                "id": node_id,
                "types": sorted(set(types)),
                "label": label,
                "properties": properties or {},
                "source": source or {},
            }
            return
        node["types"] = sorted(set(node.get("types", [])) | set(types))
        if properties:
            node["properties"].update({k: v for k, v in properties.items() if v is not None})
        if source:
            node["source"].update({k: v for k, v in source.items() if v is not None})

    def add_edge(source: str, predicate: str, target: str, *, evidence: str, qualifiers: dict[str, Any] | None = None) -> None:
        qualifiers = qualifiers or {}
        key = (source, predicate, target, _stable_value(qualifiers))
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append({
            "id": f"{PROJECT_TWO_BASE}edge:{_digest('|'.join(key))}",
            "source": source,
            "predicate": predicate,
            "target": target,
            "qualifiers": qualifiers,
            "evidence": evidence,
        })

    def add_fact(subject: str, predicate: str, value: Any, *, evidence: str) -> None:
        if len(facts) >= max_facts or value is None:
            return
        facts.append({"subject": subject, "predicate": predicate, "value": value, "evidence": evidence})

    project_key = f"{project.get('owner', '')}/{project.get('number', '')}"
    project_id = _urn("project", project_key)
    add_node(
        project_id,
        ["Project", "prov:Entity", "dcat:Dataset"],
        project.get("title") or project_key,
        {
            "owner": project.get("owner"),
            "number": project.get("number"),
            "node_id": project.get("id") or project.get("node_id"),
            "url": project.get("url"),
        },
        {"project": project_key},
    )

    for item in items:
        item_id_raw = str(item.get("item_id") or "")
        if not item_id_raw:
            continue
        node_id = _urn("item", item_id_raw)
        content = item.get("content") or {}
        memory = item.get("memory") or {}
        metadata = memory.get("metadata") or {}
        memory_body = memory.get("body") if memory else None
        kind = metadata.get("kind")
        standing = metadata.get("standing")
        cell = metadata.get("cell")
        key = metadata.get("key")
        tags = sorted(set(str(tag) for tag in _listify(metadata.get("tags")) if tag is not None))
        types = ["ProjectItem", "prov:Entity", str(item.get("type") or "UNKNOWN")]
        if metadata:
            types += ["MemoryRecord"]
            if kind:
                types.append(f"kind:{kind}")
        props = {
            "item_id": item_id_raw,
            "content_id": content.get("id"),
            "title": content.get("title") or "",
            "url": content.get("url"),
            "number": content.get("number"),
            "repository": content.get("repository"),
            "state": content.get("state"),
            "is_archived": bool(item.get("is_archived")),
            "field_values": item.get("field_values") or {},
            "memory_key": key,
            "kind": kind,
            "standing": standing,
            "cell": cell,
            "tags": tags,
        }
        if include_bodies:
            props["body"] = memory_body if memory else content.get("body") or ""
        add_node(node_id, types, content.get("title") or key or item_id_raw, props, {"item_id": item_id_raw})
        add_edge(project_id, "CONTAINS", node_id, evidence=f"project-item:{item_id_raw}")

        for prop_name in ("title", "url", "number", "repository", "state", "is_archived"):
            add_fact(node_id, f"project.{prop_name}", props.get(prop_name), evidence=f"project-item:{item_id_raw}")
        for field_name, value in sorted((item.get("field_values") or {}).items()):
            add_fact(node_id, f"field.{field_name}", value, evidence=f"project-field:{field_name}")

        repository = content.get("repository") or metadata.get("repo")
        if repository:
            repo_id = _urn("repository", str(repository))
            add_node(repo_id, ["Repository", "doap:Repository", "schema:SoftwareSourceCode"], str(repository), {"name": str(repository)})
            add_edge(node_id, "BELONGS_TO_REPOSITORY", repo_id, evidence="explicit repository field")

        for label in content.get("labels") or []:
            name = str((label or {}).get("name") or "").strip()
            if not name:
                continue
            label_id = _urn("label", name)
            add_node(label_id, ["Label", "skos:Concept"], name, {"name": name, "color": (label or {}).get("color")})
            add_edge(node_id, "HAS_LABEL", label_id, evidence="GitHub label")

        for login in content.get("assignees") or []:
            login = str(login).strip()
            if not login:
                continue
            actor_id = _urn("actor", login)
            add_node(actor_id, ["Actor", "foaf:Agent"], login, {"login": login})
            add_edge(node_id, "ASSIGNED_TO", actor_id, evidence="GitHub assignee")

        if metadata:
            if key:
                memory_id = _urn("memory", str(key))
                add_node(memory_id, ["MemoryKey", "prov:Entity"], str(key), {"key": key})
                add_edge(node_id, "HAS_MEMORY_KEY", memory_id, evidence="memory marker metadata")
            for tag in tags:
                tag_id = _urn("tag", tag)
                add_node(tag_id, ["Tag", "skos:Concept"], tag, {"name": tag})
                add_edge(node_id, "TAGGED_WITH", tag_id, evidence="memory metadata tags")

            for path, value in _flatten("metadata", metadata):
                add_fact(node_id, path, value, evidence="memory marker metadata")

            for rel_key, predicate in REFERENCE_RELATIONS.items():
                for value in _listify(metadata.get(rel_key)):
                    target = _reference_target(value, rel_key)
                    if not target:
                        continue
                    target_id, target_type = target
                    add_node(target_id, [target_type, "prov:Entity"], str(value), {"value": value})
                    add_edge(node_id, predicate, target_id, evidence=f"metadata.{rel_key}", qualifiers={"metadata_key": rel_key})

            for meta_key, meta_value in sorted(metadata.items()):
                if not isinstance(meta_value, str) or not HEX_SHA_RE.match(meta_value):
                    continue
                if not any(token in meta_key.casefold() for token in ("sha", "head", "base", "commit", "merge", "candidate")):
                    continue
                commit_id = _urn("commit", meta_value.lower())
                add_node(commit_id, ["Commit", "prov:Entity"], meta_value[:12], {"sha": meta_value.lower()})
                add_edge(node_id, _relation_predicate(meta_key), commit_id, evidence=f"metadata.{meta_key}")

    nodes = sorted(node_by_id.values(), key=lambda n: n["id"])
    edges.sort(key=lambda e: (e["source"], e["predicate"], e["target"], e["id"]))
    facts.sort(key=lambda f: (f["subject"], f["predicate"], _stable_value(f["value"])))

    graph = {
        "schema": SCHEMA,
        "project": project,
        "observed_at": observed_at,
        "nodes": nodes,
        "edges": edges,
        "facts": facts,
        "truncated": {"facts": len(facts) >= max_facts},
    }
    graph["tables"] = tabular_projection(graph)
    graph["triples"] = triple_projection(graph)
    graph["jsonld"] = jsonld_projection(graph)
    graph["services"] = service_catalog(graph)
    graph["ocel"] = ocel_projection(graph)
    graph["stats"] = semantic_stats(graph)
    return graph


def semantic_stats(graph: dict[str, Any]) -> dict[str, Any]:
    types = Counter()
    predicates = Counter(edge["predicate"] for edge in graph.get("edges", []))
    for node in graph.get("nodes", []):
        types.update(node.get("types") or [])
    return {
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", [])),
        "fact_count": len(graph.get("facts", [])),
        "node_types": dict(sorted(types.items())),
        "edge_predicates": dict(sorted(predicates.items())),
    }


def tabular_projection(graph: dict[str, Any]) -> dict[str, Any]:
    node_rows = []
    for node in graph.get("nodes", []):
        props = node.get("properties") or {}
        node_rows.append({
            "id": node["id"],
            "label": node.get("label"),
            "types": node.get("types") or [],
            "repository": props.get("repository"),
            "kind": props.get("kind"),
            "standing": props.get("standing"),
            "cell": props.get("cell"),
            "memory_key": props.get("memory_key"),
            "state": props.get("state"),
            "is_archived": props.get("is_archived"),
        })
    edge_rows = [
        {
            "id": edge["id"],
            "source": edge["source"],
            "predicate": edge["predicate"],
            "target": edge["target"],
            "evidence": edge.get("evidence"),
            "qualifiers": edge.get("qualifiers") or {},
        }
        for edge in graph.get("edges", [])
    ]
    fact_rows = [dict(fact) for fact in graph.get("facts", [])]
    return {"nodes": node_rows, "edges": edge_rows, "facts": fact_rows}


def triple_projection(graph: dict[str, Any]) -> list[dict[str, Any]]:
    triples: list[dict[str, Any]] = []
    for edge in graph.get("edges", []):
        triples.append({
            "subject": edge["source"],
            "predicate": f"pt:{edge['predicate'].lower()}",
            "object": {"id": edge["target"]},
            "evidence": edge.get("evidence"),
        })
    for fact in graph.get("facts", []):
        triples.append({
            "subject": fact["subject"],
            "predicate": f"pt:{re.sub(r'[^A-Za-z0-9_.-]+', '_', fact['predicate'])}",
            "object": {"value": fact["value"]},
            "evidence": fact.get("evidence"),
        })
    triples.sort(key=lambda t: (t["subject"], t["predicate"], _stable_value(t["object"])))
    return triples


def jsonld_projection(graph: dict[str, Any]) -> dict[str, Any]:
    relation_map: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for edge in graph.get("edges", []):
        predicate = f"pt:{edge['predicate'].casefold()}"
        relation_map[edge["source"]][predicate].append({"@id": edge["target"]})

    docs = []
    for node in graph.get("nodes", []):
        doc: dict[str, Any] = {
            "@id": node["id"],
            "@type": ["prov:Entity"] + [f"pt:{re.sub(r'[^A-Za-z0-9_.-]+', '_', t)}" for t in node.get("types", []) if ":" not in t],
            "skos:prefLabel": node.get("label"),
        }
        for predicate, objects in sorted(relation_map.get(node["id"], {}).items()):
            doc[predicate] = objects
        docs.append(doc)
    return {
        "@context": JSONLD_CONTEXT,
        "@graph": docs,
        "profile": "Project Two explicit-semantics projection",
        "conformance": "GENERATED_NOT_EXTERNALLY_VALIDATED",
    }


def service_catalog(graph: dict[str, Any]) -> dict[str, Any]:
    kinds = Counter()
    repos = Counter()
    standings = Counter()
    cells = Counter()
    tags = Counter()
    for node in graph.get("nodes", []):
        props = node.get("properties") or {}
        if props.get("kind"):
            kinds[str(props["kind"])] += 1
        if props.get("repository"):
            repos[str(props["repository"])] += 1
        if props.get("standing"):
            standings[str(props["standing"])] += 1
        if props.get("cell"):
            cells[str(props["cell"])] += 1
        tags.update(str(tag) for tag in props.get("tags") or [])

    capabilities = [
        {
            "id": f"{PROJECT_TWO_BASE}capability:{name}",
            "name": name,
            "type": "dcat:DataService",
            "operations": operations,
            "authority": "READ_ONLY_PROJECTION" if not any(op.startswith("memory.") and op not in {"memory.read", "memory.query"} for op in operations) else "BOUNDED_PROJECT_MEMORY_MUTATION",
        }
        for name, operations in PLATFORM_CAPABILITIES
    ]
    return {
        "model": "virtual-semantic-paas",
        "canonical_subject": "GitHub Project v2 #2",
        "interfaces": [
            {"name": "ChatGPT request bus", "protocol": "bounded JSON request + receipt"},
            {"name": "LLM MCP junction", "protocol": "AshAi/MCP"},
            {"name": "GitHub Project UI", "protocol": "human inspection"},
        ],
        "capabilities": capabilities,
        "resource_facets": {
            "kinds": dict(sorted(kinds.items())),
            "repositories": dict(sorted(repos.items())),
            "standings": dict(sorted(standings.items())),
            "cells": dict(sorted(cells.items())),
            "tags": dict(sorted(tags.items())),
        },
    }


def ocel_projection(graph: dict[str, Any]) -> dict[str, Any]:
    """Produce an OCEL-2-shaped read model without claiming conformance."""
    project_items = [node for node in graph.get("nodes", []) if "ProjectItem" in (node.get("types") or [])]
    objects = []
    events = []
    for node in project_items:
        props = node.get("properties") or {}
        obj_type = "MemoryRecord" if "MemoryRecord" in (node.get("types") or []) else "ProjectItem"
        attributes = []
        for name in ("title", "repository", "state", "kind", "standing", "cell", "memory_key"):
            if props.get(name) is not None:
                attributes.append({"name": name, "time": graph.get("observed_at"), "value": props[name]})
        objects.append({"id": node["id"], "type": obj_type, "attributes": attributes, "relationships": []})

    if project_items:
        events.append({
            "id": f"{PROJECT_TWO_BASE}event:snapshot:{_digest(str(graph.get('observed_at')))}",
            "type": "ProjectSemanticSnapshot",
            "time": graph.get("observed_at"),
            "attributes": [],
            "relationships": [{"objectId": node["id"], "qualifier": "observed"} for node in project_items],
        })

    facts_by_subject: dict[str, dict[str, Any]] = defaultdict(dict)
    for fact in graph.get("facts", []):
        facts_by_subject[fact["subject"]][fact["predicate"]] = fact["value"]
    for node in project_items:
        facts = facts_by_subject.get(node["id"], {})
        for field, event_type in (("metadata.created_at", "MemoryCreated"), ("metadata.updated_at", "MemoryUpdated")):
            timestamp = facts.get(field)
            if not timestamp:
                continue
            events.append({
                "id": f"{PROJECT_TWO_BASE}event:{event_type.casefold()}:{_digest(node['id'] + str(timestamp))}",
                "type": event_type,
                "time": timestamp,
                "attributes": [],
                "relationships": [{"objectId": node["id"], "qualifier": "subject"}],
            })

    return {
        "profile": "OCEL-2-shaped Project Two projection",
        "conformance": "NOT_CLAIMED_UNTIL_INDEPENDENT_OCEL_VALIDATOR_EXECUTES",
        "objectTypes": [
            {"name": "ProjectItem", "attributes": []},
            {"name": "MemoryRecord", "attributes": []},
        ],
        "eventTypes": [
            {"name": "ProjectSemanticSnapshot", "attributes": []},
            {"name": "MemoryCreated", "attributes": []},
            {"name": "MemoryUpdated", "attributes": []},
        ],
        "objects": objects,
        "events": sorted(events, key=lambda e: (str(e.get("time")), e["id"])),
    }


def query_graph(graph: dict[str, Any], query: dict[str, Any] | None = None) -> dict[str, Any]:
    query = query or {}
    node_index = {node["id"]: node for node in graph.get("nodes", [])}
    text = str(query.get("text") or "").casefold().strip()
    types = set(str(v) for v in _listify(query.get("types")))
    predicates = set(str(v) for v in _listify(query.get("predicates")))
    repository = query.get("repository")
    kind = query.get("kind")
    standing = query.get("standing")
    tags = set(str(v) for v in _listify(query.get("tags")))
    explicit_ids = set(str(v) for v in _listify(query.get("node_ids")))

    def matches(node: dict[str, Any]) -> bool:
        props = node.get("properties") or {}
        if explicit_ids and node["id"] not in explicit_ids:
            return False
        if types and not (types & set(node.get("types") or [])):
            return False
        if repository is not None and props.get("repository") != repository and props.get("name") != repository:
            return False
        if kind is not None and props.get("kind") != kind:
            return False
        if standing is not None and props.get("standing") != standing:
            return False
        if tags and not tags.issubset(set(str(v) for v in props.get("tags") or [])):
            return False
        if text:
            haystack = json.dumps({"label": node.get("label"), "types": node.get("types"), "properties": props}, sort_keys=True, default=str).casefold()
            if text not in haystack:
                return False
        return True

    selected = {node["id"] for node in graph.get("nodes", []) if matches(node)}
    neighbor_ids = set(str(v) for v in _listify(query.get("neighbors_of")))
    depth = max(0, min(int(query.get("depth", 1)), 5))
    direction = str(query.get("direction") or "both").lower()
    if neighbor_ids:
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in graph.get("edges", []):
            if predicates and edge["predicate"] not in predicates:
                continue
            if direction in {"both", "out"}:
                adjacency[edge["source"]].add(edge["target"])
            if direction in {"both", "in"}:
                adjacency[edge["target"]].add(edge["source"])
        seen = set(neighbor_ids)
        queue = deque((node_id, 0) for node_id in sorted(neighbor_ids))
        while queue:
            node_id, d = queue.popleft()
            if d >= depth:
                continue
            for target in sorted(adjacency.get(node_id, ())):
                if target not in seen:
                    seen.add(target)
                    queue.append((target, d + 1))
        selected = selected & seen if any((text, types, repository, kind, standing, tags, explicit_ids)) else seen

    candidate_edges = [
        edge for edge in graph.get("edges", [])
        if edge["source"] in selected and edge["target"] in selected and (not predicates or edge["predicate"] in predicates)
    ]
    limit = max(1, min(int(query.get("limit", 500)), 5000))
    selected_nodes = [node_index[node_id] for node_id in sorted(selected) if node_id in node_index][:limit]
    selected_ids = {node["id"] for node in selected_nodes}
    candidate_edges = [e for e in candidate_edges if e["source"] in selected_ids and e["target"] in selected_ids][: limit * 10]
    facts = [fact for fact in graph.get("facts", []) if fact["subject"] in selected_ids][: limit * 20]
    return {
        "query": query,
        "nodes": selected_nodes,
        "edges": candidate_edges,
        "facts": facts,
        "matched_nodes": len(selected),
        "returned_nodes": len(selected_nodes),
        "truncated": len(selected) > len(selected_nodes),
    }


def context_projection(graph: dict[str, Any], query: dict[str, Any] | None = None) -> dict[str, Any]:
    query = dict(query or {})
    query.setdefault("limit", 100)
    result = query_graph(graph, query)
    adjacency: dict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in result["edges"]:
        adjacency[edge["source"]].append({"predicate": edge["predicate"], "target": edge["target"]})
        adjacency[edge["target"]].append({"predicate": f"INVERSE_{edge['predicate']}", "target": edge["source"]})
    max_body_chars = max(0, min(int(query.get("max_body_chars", 1200)), 20_000))
    records = []
    for node in result["nodes"]:
        props = node.get("properties") or {}
        body = props.get("body") or ""
        records.append({
            "id": node["id"],
            "label": node.get("label"),
            "types": node.get("types") or [],
            "repository": props.get("repository"),
            "kind": props.get("kind"),
            "standing": props.get("standing"),
            "cell": props.get("cell"),
            "memory_key": props.get("memory_key"),
            "tags": props.get("tags") or [],
            "body": body[:max_body_chars] if max_body_chars else None,
            "relations": sorted(adjacency.get(node["id"], []), key=lambda r: (r["predicate"], r["target"]))[:100],
        })
    return {
        "schema": "project-two-llm-context/v1",
        "project": graph.get("project"),
        "observed_at": graph.get("observed_at"),
        "stats": graph.get("stats"),
        "query": query,
        "records": records,
        "returned_records": len(records),
        "truncated": result.get("truncated", False),
    }


def select_views(graph: dict[str, Any], views: list[str] | None = None, *, query: dict[str, Any] | None = None) -> dict[str, Any]:
    requested = views or ["graph", "tables", "triples", "jsonld", "services", "ocel", "context"]
    allowed = {"graph", "tables", "triples", "jsonld", "services", "ocel", "context", "stats"}
    invalid = sorted(set(requested) - allowed)
    if invalid:
        raise ValueError(f"unsupported semantic views: {', '.join(invalid)}")
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "project": graph.get("project"),
        "observed_at": graph.get("observed_at"),
        "views": requested,
    }
    if "graph" in requested:
        result["graph"] = {k: graph[k] for k in ("nodes", "edges", "facts", "truncated")}
    for view in ("tables", "triples", "jsonld", "services", "ocel", "stats"):
        if view in requested:
            result[view] = graph.get(view)
    if "context" in requested:
        result["context"] = context_projection(graph, query)
    return result
