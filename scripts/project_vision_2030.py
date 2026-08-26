#!/usr/bin/env python3
"""Deterministic Vision 2030 portfolio projection for Project Two.

Consumes the existing read-only semantic graph and emits observational capability,
evidence, dependency-closure, and frontier metrics. It grants no standing and has
no mutation or actuation path.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

SCHEMA = "project-two-vision-2030/v1"
AUTHORITY = "READ_ONLY_VIRTUAL_PROJECTION"

PILLARS = [
    {
        "id": "deterministic-manufacture",
        "label": "Deterministic manufacture",
        "signals": [
            "ggen",
            "generator",
            "generated",
            "generation",
            "pack",
            "marketplace",
            "manufacture",
            "manufacturing",
            "ontology",
        ],
    },
    {
        "id": "governed-actuation",
        "label": "Governed actuation",
        "signals": [
            "brce",
            "authority",
            "admission",
            "receipt",
            "receipts",
            "replay",
            "standing",
            "verifier",
            "court",
            "bounded",
        ],
    },
    {
        "id": "autonomous-qualification",
        "label": "Autonomous qualification",
        "signals": [
            "ci",
            "test",
            "tests",
            "qualification",
            "qualify",
            "verification",
            "verify",
            "validator",
            "exact-head",
            "workflow",
        ],
    },
    {
        "id": "cloud-execution",
        "label": "Cloud execution",
        "signals": [
            "cloud",
            "aws",
            "azure",
            "gcp",
            "kubernetes",
            "k8s",
            "docker",
            "terraform",
            "fly",
            "deployment",
            "runtime",
        ],
    },
    {
        "id": "process-intelligence",
        "label": "Process intelligence",
        "signals": ["process", "ocel", "pm4py", "ex4pm", "provenance", "prov", "event-log", "conformance"],
    },
    {
        "id": "semantic-interoperability",
        "label": "Semantic interoperability",
        "signals": ["semantic", "ontology", "rdf", "r2rml", "jsonld", "json-ld", "ash", "schema", "prov-o", "dcat", "skos"],
    },
    {
        "id": "agent-evaluation",
        "label": "Agent evaluation",
        "signals": ["gym", "eval", "evaluation", "benchmark", "agent", "planner", "policy", "episode", "autofde"],
    },
    {
        "id": "portfolio-memory",
        "label": "Portfolio memory",
        "signals": ["memory", "project-two", "frontier", "ledger", "capability", "receipt", "replay"],
    },
]

DEPENDENCY_PREDICATES = {"REQUIRES", "DEPENDS_ON", "CONSUMES_MEMORY"}
RECEIPT_PREDICATES = {"HAS_RECEIPT", "HAS_REPLAY"}


def project(graph: dict[str, Any], query: dict[str, Any] | None = None) -> dict[str, Any]:
    query = {str(k): v for k, v in (query or {}).items()}
    minimum_evidence = max(_bounded_int(query.get("minimum_evidence", 1), 1), 1)

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    memory_nodes = [node for node in nodes if "MemoryRecord" in (node.get("types") or [])]
    repositories = [node for node in nodes if "Repository" in (node.get("types") or [])]
    commits = [node for node in nodes if "Commit" in (node.get("types") or [])]

    standings = Counter(
        str(value)
        for value in (_props(node).get("standing") for node in memory_nodes)
        if value not in (None, "")
    )

    evidence_index: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        evidence_index[edge.get("source")].append(edge.get("predicate"))

    pillar_results = []
    for pillar in PILLARS:
        evidence = _pillar_evidence(memory_nodes, pillar["signals"])
        count = len(evidence)
        pillar_results.append(
            {
                "id": pillar["id"],
                "label": pillar["label"],
                "status": "PRESENT" if count >= minimum_evidence else "GAP",
                "evidence_count": count,
                "minimum_evidence": minimum_evidence,
                "evidence": evidence[:25],
            }
        )

    present = sum(1 for pillar in pillar_results if pillar["status"] == "PRESENT")
    total = len(pillar_results)

    return {
        "schema": SCHEMA,
        "canonical_subject": graph.get("canonical_subject", "GitHub Project v2 #2"),
        "observed_at": graph.get("observed_at"),
        "authority": AUTHORITY,
        "source_truncated": bool(graph.get("source_truncated", False)),
        "objective": "AUTONOMIC_SOFTWARE_MANUFACTURING",
        "horizon": 2030,
        "interpretation": "Deterministic evidence projection only; not a forecast, certification, or actuation grant.",
        "portfolio": {
            "memory_records": len(memory_nodes),
            "repositories": len(repositories),
            "commits": len(commits),
            "standings": dict(sorted(standings.items())),
        },
        "capability_coverage": {
            "present_pillars": present,
            "total_pillars": total,
            "coverage_ratio": _ratio(present, total),
            "pillars": pillar_results,
            "gaps": [
                {k: pillar[k] for k in ("id", "label", "evidence_count", "minimum_evidence")}
                for pillar in pillar_results
                if pillar["status"] == "GAP"
            ],
        },
        "evidence_coverage": _evidence_coverage(memory_nodes, evidence_index),
        "dependency_closure": _dependency_closure(graph, memory_nodes),
        "frontier": _frontier(memory_nodes, evidence_index, query),
        "admission": {
            "mutating_operations_introduced": 0,
            "standing_granted": False,
            "consequential_do_authority": False,
            "rule": "Observation may identify gaps; only existing bounded mutation paths may act on them.",
        },
    }


def _pillar_evidence(nodes: list[dict[str, Any]], signals: list[str]) -> list[dict[str, Any]]:
    evidence = []
    for node in nodes:
        corpus = _node_corpus(node)
        matched = sorted({signal for signal in signals if signal in corpus})
        if not matched:
            continue
        props = _props(node)
        evidence.append(
            {
                "id": node.get("id"),
                "label": node.get("label"),
                "memory_key": props.get("memory_key"),
                "repository": props.get("repository"),
                "standing": props.get("standing"),
                "matched_signals": matched,
            }
        )
    return sorted(evidence, key=lambda item: (str(item.get("memory_key")), str(item.get("id"))))


def _node_corpus(node: dict[str, Any]) -> str:
    props = _props(node)
    values = [
        node.get("label"),
        node.get("types"),
        props.get("repository"),
        props.get("kind"),
        props.get("standing"),
        props.get("cell"),
        props.get("memory_key"),
        props.get("tags"),
        props.get("body"),
    ]
    return repr(values).lower()


def _evidence_coverage(
    memory_nodes: list[dict[str, Any]], evidence_index: dict[str, list[str]]
) -> dict[str, Any]:
    total = len(memory_nodes)
    with_standing = sum(1 for node in memory_nodes if _props(node).get("standing") not in (None, ""))
    with_repository = sum(1 for node in memory_nodes if _props(node).get("repository") not in (None, ""))
    with_commit = sum(
        1
        for node in memory_nodes
        if any(predicate.startswith("METADATA_") for predicate in evidence_index.get(node.get("id"), []))
    )
    with_receipt = sum(
        1
        for node in memory_nodes
        if RECEIPT_PREDICATES.intersection(evidence_index.get(node.get("id"), []))
    )
    return {
        "total_records": total,
        "standing": _coverage_metric(with_standing, total),
        "repository_identity": _coverage_metric(with_repository, total),
        "commit_identity": _coverage_metric(with_commit, total),
        "receipt_or_replay": _coverage_metric(with_receipt, total),
    }


def _dependency_closure(graph: dict[str, Any], memory_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    memory_keys = {
        value
        for value in (_props(node).get("memory_key") for node in memory_nodes)
        if value not in (None, "")
    }
    node_by_id = {node.get("id"): node for node in graph.get("nodes") or []}
    dependencies = [edge for edge in graph.get("edges") or [] if edge.get("predicate") in DEPENDENCY_PREDICATES]

    unresolved = []
    for edge in dependencies:
        target = node_by_id.get(edge.get("target"))
        label = target.get("label") if target else None
        target_types = target.get("types") or [] if target else []
        unresolved_edge = target is None or ("MemoryKey" in target_types and label not in memory_keys)
        if unresolved_edge:
            unresolved.append(
                {
                    "source": edge.get("source"),
                    "predicate": edge.get("predicate"),
                    "target": edge.get("target"),
                    "label": label,
                }
            )

    unresolved.sort(key=lambda edge: (str(edge["source"]), str(edge["predicate"]), str(edge["target"])))
    total = len(dependencies)
    closed = max(total - len(unresolved), 0)
    return {
        "dependency_edges": total,
        "resolved_edges": closed,
        "unresolved_edges": len(unresolved),
        "closure_ratio": _ratio(closed, total),
        "unresolved": unresolved[:100],
    }


def _frontier(
    memory_nodes: list[dict[str, Any]], evidence_index: dict[str, list[str]], query: dict[str, Any]
) -> list[dict[str, Any]]:
    limit = max(min(_bounded_int(query.get("frontier_limit", 20), 20), 100), 1)
    ranked = []
    for node in memory_nodes:
        predicates = evidence_index.get(node.get("id"), [])
        props = _props(node)
        standing = props.get("standing")
        evidence_weight = sum(
            1
            for predicate in predicates
            if predicate in RECEIPT_PREDICATES or predicate.startswith("METADATA_")
        )
        relation_weight = sum(1 for predicate in predicates if predicate in DEPENDENCY_PREDICATES)
        standing_weight = 4 if standing == "ALIVE" else (1 if standing not in (None, "") else 0)
        repository_weight = 1 if props.get("repository") not in (None, "") else 0
        ranked.append(
            {
                "id": node.get("id"),
                "memory_key": props.get("memory_key"),
                "label": node.get("label"),
                "repository": props.get("repository"),
                "standing": standing,
                "evidence_weight": evidence_weight,
                "relation_weight": relation_weight,
                "observational_rank": evidence_weight + relation_weight + standing_weight + repository_weight,
            }
        )
    ranked.sort(key=lambda item: (-item["observational_rank"], str(item.get("memory_key")), str(item.get("id"))))
    return ranked[:limit]


def _props(node: dict[str, Any]) -> dict[str, Any]:
    return node.get("properties") or {}


def _coverage_metric(count: int, total: int) -> dict[str, Any]:
    return {"count": count, "total": total, "ratio": _ratio(count, total)}


def _ratio(count: int, total: int) -> float:
    return 0.0 if total == 0 else round(count / total, 4)


def _bounded_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
