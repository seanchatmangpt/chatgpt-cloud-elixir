#!/usr/bin/env python3
"""Validate manufacturing/ontology.ttl's cc:CapabilitySource instances against
the cc:CapabilitySourceShape SHACL shape defined in the same file.

The shapes graph and the data graph are the same file (the shapes live
alongside the data they constrain), so this loads manufacturing/ontology.ttl
once and validates it against itself with pyshacl.

Usage:
    python3 scripts/verify-manufacturing-shacl.py

Exit status: 0 if conforms=True, 1 otherwise. Prints the real pyshacl
validation report text either way — this is a rerunnable check, not a
one-off hand-trace.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from pyshacl import validate
except ImportError:  # pragma: no cover
    print(
        "REFUSED[MISSING_DEPENDENCY]: pip3 install rdflib pyshacl",
        file=sys.stderr,
    )
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "manufacturing" / "ontology.ttl"

EXPECTED_CAPABILITY_SOURCES = {
    "https://chatman.ai/chatgpt-cloud/capability#Ggen",
    "https://chatman.ai/chatgpt-cloud/capability#GgenMarketplace",
    "https://chatman.ai/chatgpt-cloud/capability#GgenCreate",
    "https://chatman.ai/chatgpt-cloud/capability#GgenLegacy",
    "https://chatman.ai/chatgpt-cloud/capability#GgenSpecKit",
    "https://chatman.ai/chatgpt-cloud/capability#SwarmSH",
    "https://chatman.ai/chatgpt-cloud/capability#SwarmSHV2",
}

CC = "https://chatman.ai/chatgpt-cloud/capability#"


def main() -> int:
    if not ONTOLOGY.exists():
        print(f"REFUSED[MISSING_ONTOLOGY]: {ONTOLOGY} not found", file=sys.stderr)
        return 2

    data_text = ONTOLOGY.read_text()

    # Sanity check: confirm the shape this script exists to enforce is
    # actually present, so a silent shape-removal doesn't make this script
    # report a hollow conforms=True.
    if "cc:CapabilitySourceShape" not in data_text or "sh:NodeShape" not in data_text:
        print(
            "REFUSED[MISSING_SHAPE]: cc:CapabilitySourceShape / sh:NodeShape "
            "not found in manufacturing/ontology.ttl",
            file=sys.stderr,
        )
        return 2

    # Independently confirm, via rdflib, that the exact 7 real
    # cc:CapabilitySource instances are the ones being validated (regression
    # guard against the instance set silently drifting).
    import rdflib

    g = rdflib.Graph()
    g.parse(data=data_text, format="turtle")
    cap_source = rdflib.URIRef(CC + "CapabilitySource")
    found_instances = {
        str(s) for s in g.subjects(rdflib.RDF.type, cap_source)
    }
    if found_instances != EXPECTED_CAPABILITY_SOURCES:
        print(
            "REFUSED[INSTANCE_SET_DRIFT]: expected exactly "
            f"{sorted(EXPECTED_CAPABILITY_SOURCES)}, found {sorted(found_instances)}",
            file=sys.stderr,
        )
        return 2

    # Shapes graph and data graph are the same file — the shapes live
    # alongside the data they constrain.
    conforms, results_graph, results_text = validate(
        data_text,
        shacl_graph=data_text,
        data_graph_format="turtle",
        shacl_graph_format="turtle",
        inference="none",
        serialize_report_graph=False,
    )

    print(results_text)
    print(f"cc:CapabilitySource instances checked: {len(found_instances)}")
    print(f"conforms={conforms}")

    if not conforms:
        print("REFUSED[SHACL_VIOLATION]: see report above", file=sys.stderr)
        return 1

    print("SHACL_VALIDATION=ALIVE conforms=True instances=7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
