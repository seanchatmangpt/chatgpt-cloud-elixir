#!/usr/bin/env python3
"""Deterministic Vision 2030 portfolio projection for Project Two.

Consumes the existing read-only semantic graph and emits observational capability,
evidence, dependency-closure, manufacturing-capital, combinatorial-option, and
frontier metrics. It grants no standing and has no mutation or actuation path.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
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

CAPITAL_CLASSES = [
    {
        "id": "generative-capital",
        "signals": ["ggen", "generator", "generation", "pack", "marketplace", "manufacture", "manufacturing"],
    },
    {
        "id": "governance-capital",
        "signals": ["brce", "authority", "admission", "receipt", "replay", "verifier", "court", "standing"],
    },
    {
        "id": "qualification-capital",
        "signals": ["ci", "test", "qualification", "verification", "validator", "exact-head", "workflow"],
    },
    {
        "id": "semantic-capital",
        "signals": ["ontology", "semantic", "rdf", "r2rml", "jsonld", "prov-o", "dcat", "skos", "ocel"],
    },
    {
        "id": "execution-capital",
        "signals": ["cloud", "aws", "azure", "gcp", "kubernetes", "docker", "terraform", "runtime", "deployment"],
    },
    {
        "id": "evaluation-capital",
        "signals": ["gym", "eval", "evaluation", "benchmark", "planner", "policy", "episode", "autofde"],
    },
    {
        "id": "memory-capital",
        "signals": ["memory", "project-two", "frontier", "ledger", "capability"],
    },
]

DEPENDENCY_PREDICATES = {"REQUIRES", "DEPENDS_ON", "CONSUMES_MEMORY"}
RECEIPT_PREDICATES = {"HAS_RECEIPT", "HAS_REPLAY"}


def project(graph: dict[str, Any], query: dict[str, Any] | None = None) -> dict[str, Any]:
    query = {str(k): v for k, v in (query or {}).items()}
    minimum_evidence = max(_bounded_int(query.get("minimum_evidence", 1), 1), 1)
    minimum_domains = max(min(_bounded_int(query.get("minimum_domains", 1), 1), 10), 1)
    minimum_receipt_ratio = _bounded_ratio(query.get("minimum_receipt_ratio", 0.0), 0.0)

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
        domains = sorted({_evidence_domain(item) for item in evidence})
        count = len(evidence)
        falsifiers = []
        if count < minimum_evidence:
            falsifiers.append("EVIDENCE_SHORTFALL")
        if len(domains) < minimum_domains:
            falsifiers.append("DOMAIN_DIVERSITY_SHORTFALL")

        pillar_results.append(
            {
                "id": pillar["id"],
                "label": pillar["label"],
                "status": "PRESENT" if not falsifiers else "GAP",
                "evidence_count": count,
                "minimum_evidence": minimum_evidence,
                "evidence_domains": domains,
                "domain_count": len(domains),
                "minimum_domains": minimum_domains,
                "falsifiers": falsifiers,
                "evidence": evidence[:25],
            }
        )

    present = sum(1 for pillar in pillar_results if pillar["status"] == "PRESENT")
    total = len(pillar_results)
    dependency = _dependency_closure(graph, memory_nodes)
    evidence = _evidence_coverage(memory_nodes, evidence_index)
    combinatorial = _combinatorial_option_space(memory_nodes)
    capital = _manufacturing_capital(memory_nodes, evidence_index)
    maximalist_frontier = _maximalist_frontier(pillar_results, combinatorial)
    autonomy = _autonomy_envelope(
        graph,
        pillar_results,
        dependency,
        evidence,
        capital,
        minimum_receipt_ratio,
    )

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
                {
                    k: pillar[k]
                    for k in (
                        "id",
                        "label",
                        "evidence_count",
                        "minimum_evidence",
                        "domain_count",
                        "minimum_domains",
                        "falsifiers",
                    )
                }
                for pillar in pillar_results
                if pillar["status"] == "GAP"
            ],
        },
        "evidence_coverage": evidence,
        "dependency_closure": dependency,
        "manufacturing_capital": capital,
        "combinatorial_option_space": combinatorial,
        "maximalist_frontier": maximalist_frontier,
        "autonomy_envelope": autonomy,
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


def _evidence_domain(item: dict[str, Any]) -> str:
    repository = item.get("repository")
    return str(repository) if repository not in (None, "") else "project-memory"


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


def _combinatorial_option_space(memory_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    observed_pairs: set[tuple[str, str]] = set()
    cross_pillar_records = 0

    for node in memory_nodes:
        corpus = _node_corpus(node)
        matched = sorted(
            pillar["id"]
            for pillar in PILLARS
            if any(signal in corpus for signal in pillar["signals"])
        )
        if len(matched) >= 2:
            cross_pillar_records += 1
        observed_pairs.update(combinations(matched, 2))

    possible_pairings = len(PILLARS) * (len(PILLARS) - 1) // 2
    pairings = [list(pair) for pair in sorted(observed_pairs)]
    return {
        "possible_pairings": possible_pairings,
        "observed_pairings": len(pairings),
        "pairing_coverage_ratio": _ratio(len(pairings), possible_pairings),
        "cross_pillar_records": cross_pillar_records,
        "pairings": pairings,
        "interpretation": "Observed co-occurrence topology only; pairings are not causal claims or effort estimates.",
    }


def _manufacturing_capital(
    memory_nodes: list[dict[str, Any]], evidence_index: dict[str, list[str]]
) -> dict[str, Any]:
    capital_records = []
    class_counts = Counter()

    for node in memory_nodes:
        corpus = _node_corpus(node)
        matched_classes = sorted(
            capital_class["id"]
            for capital_class in CAPITAL_CLASSES
            if any(signal in corpus for signal in capital_class["signals"])
        )
        if not matched_classes:
            continue

        props = _props(node)
        predicates = evidence_index.get(node.get("id"), [])
        has_receipt = bool(RECEIPT_PREDICATES.intersection(predicates))
        standing = props.get("standing")
        qualified = standing == "ALIVE" and has_receipt
        for class_id in matched_classes:
            class_counts[class_id] += 1

        capital_records.append(
            {
                "id": node.get("id"),
                "memory_key": props.get("memory_key"),
                "repository": props.get("repository"),
                "standing": standing,
                "classes": matched_classes,
                "class_count": len(matched_classes),
                "has_receipt_or_replay": has_receipt,
                "qualified_reusable_capital": qualified,
            }
        )

    qualified = [record for record in capital_records if record["qualified_reusable_capital"]]
    unqualified = [record for record in capital_records if not record["qualified_reusable_capital"]]
    unqualified.sort(
        key=lambda record: (
            -record["class_count"],
            record["has_receipt_or_replay"],
            str(record.get("memory_key")),
            str(record.get("id")),
        )
    )

    return {
        "capital_records": len(capital_records),
        "portfolio_records": len(memory_nodes),
        "capital_ratio": _ratio(len(capital_records), len(memory_nodes)),
        "qualified_reusable_capital": len(qualified),
        "qualified_capital_ratio": _ratio(len(qualified), len(capital_records)),
        "by_class": dict(sorted(class_counts.items())),
        "unqualified_capital_frontier": unqualified[:50],
        "interpretation": "Capital means reusable productive machinery evidenced in Project memory; it is not financial-accounting capitalization.",
    }


def _maximalist_frontier(
    pillar_results: list[dict[str, Any]], combinatorial: dict[str, Any]
) -> list[dict[str, Any]]:
    observed_pairs = {tuple(pair) for pair in combinatorial["pairings"]}
    pillar_ids = [pillar["id"] for pillar in pillar_results]
    frontier = []

    for pillar in pillar_results:
        if pillar["status"] != "GAP":
            continue
        unrealized = []
        for other in pillar_ids:
            if other == pillar["id"]:
                continue
            pair = tuple(sorted((pillar["id"], other)))
            if pair not in observed_pairs:
                unrealized.append(other)

        evidence_shortfall = max(pillar["minimum_evidence"] - pillar["evidence_count"], 0)
        domain_shortfall = max(pillar["minimum_domains"] - pillar["domain_count"], 0)
        frontier.append(
            {
                "id": pillar["id"],
                "label": pillar["label"],
                "unrealized_pairing_count": len(unrealized),
                "unrealized_pairings_with": sorted(unrealized),
                "evidence_shortfall": evidence_shortfall,
                "domain_shortfall": domain_shortfall,
                "option_surface_score": len(unrealized) + evidence_shortfall + domain_shortfall,
                "falsifiers": pillar["falsifiers"],
            }
        )

    frontier.sort(
        key=lambda item: (
            -item["option_surface_score"],
            -item["unrealized_pairing_count"],
            item["id"],
        )
    )
    return frontier


def _autonomy_envelope(
    graph: dict[str, Any],
    pillar_results: list[dict[str, Any]],
    dependency: dict[str, Any],
    evidence: dict[str, Any],
    capital: dict[str, Any],
    minimum_receipt_ratio: float,
) -> dict[str, Any]:
    falsifiers = []
    capability_gaps = [pillar["id"] for pillar in pillar_results if pillar["status"] == "GAP"]

    if bool(graph.get("source_truncated", False)):
        falsifiers.append("SOURCE_TRUNCATED")
    if capability_gaps:
        falsifiers.append("CAPABILITY_GAPS")
    if dependency["unresolved_edges"] > 0:
        falsifiers.append("UNRESOLVED_DEPENDENCIES")
    if evidence["receipt_or_replay"]["ratio"] < minimum_receipt_ratio:
        falsifiers.append("RECEIPT_COVERAGE_SHORTFALL")

    closed = not falsifiers
    return {
        "status": "CLOSED" if closed else "OPEN",
        "structural_phase": "INTEGRATED_AUTONOMIC_STACK" if closed else "ASSEMBLY_IN_PROGRESS",
        "falsifiers": falsifiers,
        "capability_gaps": capability_gaps,
        "minimum_receipt_ratio": minimum_receipt_ratio,
        "observed_receipt_ratio": evidence["receipt_or_replay"]["ratio"],
        "qualified_reusable_capital": capital["qualified_reusable_capital"],
        "standing": "OBSERVATIONAL_ONLY",
        "interpretation": "Envelope closure is a deterministic structural condition, not production certification or authority to act.",
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


def _bounded_ratio(value: Any, default: float) -> float:
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        ratio = default
    return round(max(0.0, min(ratio, 1.0)), 4)
