#!/usr/bin/env python3
"""Structural court for the orphaned ggen/paas/ + ggen/capability-lineage/ trees.

docs/errc-tracker.md (ELIMINATE) records that these 138 RDF/SPARQL files are
entirely orphaned: no script, workflow, or doc anywhere references any
filename or predicate from either tree. This validator does not wire them
into a functional runtime-admission pipeline (that is a separate, larger,
riskier undertaking) — it closes the achievable slice: proving the files are
real and well-formed, with a real rerunnable check, so "nothing references
them" becomes "CI validates them" even though nothing yet executes them.

Checks performed, each with real pass/fail counts (never estimated):

  1. Every *.ttl file under ggen/paas/ and ggen/capability-lineage/ parses
     cleanly with rdflib (format="turtle").
  2. The set of files that actually use SHACL vocabulary (sh:NodeShape /
     sh:property) is independently discovered via rdflib (not grepped/
     assumed) and cross-checked against the claim in docs/errc-tracker.md:
     exactly ggen/paas/runtime-admission/*.ttl, no more, no fewer.
  3. Each SHACL-shaped file loads as a shapes graph with pyshacl and
     validates against a trivial data graph without raising — proof the
     shapes are well-formed SHACL, not proof anything currently checks real
     data against them (there is no real data graph yet). The full 100-file
     runtime-admission set is also loaded as one combined shapes graph and
     validated the same way, as a second, coarser-grained pass.
  4. Every *.rq file under both trees is syntactically parseable SPARQL via
     rdflib.plugins.sparql.prepareQuery (a real parse, not a regex sniff).

Usage:
    python3 scripts/verify-ggen-paas-shapes.py

Exit status: 0 if every check passes, 2 for a missing dependency or an empty/
missing corpus (setup problem, not a content problem), 1 if any file
genuinely fails to parse/validate or the SHACL-scope claim has drifted.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import rdflib
    from rdflib.plugins.sparql import prepareQuery
except ImportError:  # pragma: no cover
    print(
        "REFUSED[MISSING_DEPENDENCY]: pip3 install rdflib pyshacl",
        file=sys.stderr,
    )
    raise SystemExit(2)

try:
    from pyshacl import validate as shacl_validate
except ImportError:  # pragma: no cover
    print(
        "REFUSED[MISSING_DEPENDENCY]: pip3 install rdflib pyshacl",
        file=sys.stderr,
    )
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
PAAS_DIR = ROOT / "ggen" / "paas"
RUNTIME_ADMISSION_DIR = PAAS_DIR / "runtime-admission"
LINEAGE_DIR = ROOT / "ggen" / "capability-lineage"

SH_NODE_SHAPE = rdflib.URIRef("http://www.w3.org/ns/shacl#NodeShape")
SH_PROPERTY = rdflib.URIRef("http://www.w3.org/ns/shacl#property")

# A deliberately trivial, unrelated data graph — enough for pyshacl to run a
# validation pass without erroring, not a functional check against real
# runtime-admission data (there is none yet; that is the whole point of the
# ELIMINATE finding this script closes).
TRIVIAL_DATA_GRAPH_TTL = (
    "@prefix ex: <http://example.org/trivial#> . ex:nothing a ex:Nothing ."
)


def refuse(code: str, message: str) -> None:
    print(f"REFUSED[{code}]: {message}", file=sys.stderr)


def discover(root: Path, pattern: str) -> list[Path]:
    return sorted(root.rglob(pattern)) if root.is_dir() else []


def check_turtle_parses(ttl_files: list[Path]) -> tuple[list[Path], list[tuple[Path, str]]]:
    ok: list[Path] = []
    fail: list[tuple[Path, str]] = []
    for f in ttl_files:
        g = rdflib.Graph()
        try:
            g.parse(str(f), format="turtle")
            ok.append(f)
        except Exception as e:  # noqa: BLE001 - report every parser failure mode
            fail.append((f, f"{type(e).__name__}: {e}"))
    return ok, fail


def discover_shacl_files(ttl_ok: list[Path]) -> set[Path]:
    """Independently determine, via rdflib triples (not grep/assumption),
    which of the parsed .ttl files actually use SHACL vocabulary."""
    shacl_files: set[Path] = set()
    for f in ttl_ok:
        g = rdflib.Graph()
        g.parse(str(f), format="turtle")
        uses_shacl = (None, rdflib.RDF.type, SH_NODE_SHAPE) in g or (
            None,
            SH_PROPERTY,
            None,
        ) in g
        if uses_shacl:
            shacl_files.add(f)
    return shacl_files


def check_shacl_shapes(shacl_files: list[Path]) -> tuple[list[Path], list[tuple[Path, str]]]:
    ok: list[Path] = []
    fail: list[tuple[Path, str]] = []
    data_graph = rdflib.Graph()
    data_graph.parse(data=TRIVIAL_DATA_GRAPH_TTL, format="turtle")
    for f in shacl_files:
        try:
            conforms, _results_graph, _results_text = shacl_validate(
                data_graph,
                shacl_graph=str(f),
                data_graph_format="turtle",
                shacl_graph_format="turtle",
                inference="none",
                serialize_report_graph=False,
            )
            ok.append(f)
        except Exception as e:  # noqa: BLE001 - report every pyshacl failure mode
            fail.append((f, f"{type(e).__name__}: {e}"))
    return ok, fail


def check_shacl_combined(shacl_files: list[Path]) -> tuple[bool, str]:
    """Load every SHACL-shaped file as one combined shapes graph and confirm
    pyshacl can validate it as a whole, not just file-by-file."""
    shapes_graph = rdflib.Graph()
    for f in shacl_files:
        shapes_graph.parse(str(f), format="turtle")
    data_graph = rdflib.Graph()
    data_graph.parse(data=TRIVIAL_DATA_GRAPH_TTL, format="turtle")
    try:
        conforms, _rg, _rt = shacl_validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference="none",
            serialize_report_graph=False,
        )
        return True, f"combined shapes graph: {len(shapes_graph)} triples, conforms={conforms}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def check_sparql_parses(rq_files: list[Path]) -> tuple[list[Path], list[tuple[Path, str]]]:
    ok: list[Path] = []
    fail: list[tuple[Path, str]] = []
    for f in rq_files:
        text = f.read_text()
        try:
            prepareQuery(text)
            ok.append(f)
        except Exception as e:  # noqa: BLE001 - report every SPARQL parser failure mode
            fail.append((f, f"{type(e).__name__}: {e}"))
    return ok, fail


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    if not PAAS_DIR.is_dir() or not LINEAGE_DIR.is_dir():
        refuse(
            "MISSING_CORPUS",
            f"expected both {rel(PAAS_DIR)} and {rel(LINEAGE_DIR)} to exist",
        )
        return 2

    ttl_files = discover(PAAS_DIR, "*.ttl") + discover(LINEAGE_DIR, "*.ttl")
    rq_files = discover(PAAS_DIR, "*.rq") + discover(LINEAGE_DIR, "*.rq")

    if not ttl_files and not rq_files:
        refuse(
            "EMPTY_CORPUS",
            f"found 0 .ttl/.rq files under {rel(PAAS_DIR)} and {rel(LINEAGE_DIR)} "
            "-- either the trees moved or this script's globs are stale",
        )
        return 2

    print(f"Discovered {len(ttl_files)} .ttl files and {len(rq_files)} .rq files "
          f"under {rel(PAAS_DIR)} + {rel(LINEAGE_DIR)} ({len(ttl_files) + len(rq_files)} total).")
    print()

    # 1. Turtle parse.
    print("== 1. Turtle parse (rdflib, format=turtle) ==")
    ttl_ok, ttl_fail = check_turtle_parses(ttl_files)
    print(f"ttl parse: ok={len(ttl_ok)} fail={len(ttl_fail)}")
    for f, err in ttl_fail:
        print(f"  FAIL {rel(f)}: {err}")
    print()

    # 2. Independently discover which files are SHACL-shaped, cross-check
    #    against the claim that it's exactly runtime-admission/*.ttl.
    print("== 2. SHACL-vocabulary discovery + scope cross-check ==")
    shacl_files = discover_shacl_files(ttl_ok)
    expected_shacl_files = {
        f for f in ttl_ok
        if RUNTIME_ADMISSION_DIR in f.parents
    }
    unexpected_shacl = sorted(shacl_files - expected_shacl_files)
    missing_shacl = sorted(expected_shacl_files - shacl_files)
    print(f"files using sh:NodeShape/sh:property: {len(shacl_files)}")
    print(f"runtime-admission/*.ttl files (parsed): {len(expected_shacl_files)}")
    scope_drift = bool(unexpected_shacl or missing_shacl)
    for f in unexpected_shacl:
        print(f"  DRIFT: {rel(f)} uses SHACL vocabulary but is outside runtime-admission/")
    for f in missing_shacl:
        print(f"  DRIFT: {rel(f)} is under runtime-admission/ but does NOT use SHACL vocabulary")
    if not scope_drift:
        print("scope matches docs/errc-tracker.md claim exactly: no drift")
    print()

    # 3. Well-formed SHACL: per-file, then combined.
    print("== 3. SHACL well-formedness (pyshacl, trivial data graph) ==")
    shacl_sorted = sorted(shacl_files)
    shacl_ok, shacl_fail = check_shacl_shapes(shacl_sorted)
    print(f"per-file shacl load+validate: ok={len(shacl_ok)} fail={len(shacl_fail)}")
    for f, err in shacl_fail:
        print(f"  FAIL {rel(f)}: {err}")
    combined_ok, combined_msg = check_shacl_combined(shacl_sorted)
    print(f"combined shapes graph: {'OK' if combined_ok else 'FAIL'} -- {combined_msg}")
    print()

    # 4. SPARQL parse.
    print("== 4. SPARQL parse (rdflib prepareQuery) ==")
    rq_ok, rq_fail = check_sparql_parses(rq_files)
    print(f"sparql parse: ok={len(rq_ok)} fail={len(rq_fail)}")
    for f, err in rq_fail:
        print(f"  FAIL {rel(f)}: {err}")
    print()

    failures = []
    if ttl_fail:
        failures.append(("TURTLE_PARSE_FAILURE", f"{len(ttl_fail)}/{len(ttl_files)} .ttl files failed to parse"))
    if scope_drift:
        failures.append(("SHACL_SCOPE_DRIFT", "SHACL-shaped file set no longer matches runtime-admission/*.ttl exactly"))
    if shacl_fail:
        failures.append(("SHACL_MALFORMED", f"{len(shacl_fail)}/{len(shacl_sorted)} SHACL files failed to load/validate"))
    if not combined_ok:
        failures.append(("SHACL_COMBINED_MALFORMED", combined_msg))
    if rq_fail:
        failures.append(("SPARQL_PARSE_FAILURE", f"{len(rq_fail)}/{len(rq_files)} .rq files failed to parse"))

    if failures:
        for code, message in failures:
            refuse(code, message)
        return 1

    print(
        "GGEN_PAAS_SHAPES=ALIVE "
        f"ttl={len(ttl_ok)}/{len(ttl_files)} "
        f"shacl={len(shacl_ok)}/{len(shacl_sorted)} "
        f"sparql={len(rq_ok)}/{len(rq_files)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
