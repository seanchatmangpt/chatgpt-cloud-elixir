#!/usr/bin/env python3
"""Read-only orphan/health report for project-memory/ transport files.

Turns the one-off manual audit behind docs/errc-tracker.md's RAISE item ("180 of 1115
project-memory/requests/*.json (16%) have no matching receipt ... 13
project-memory/requests/*.json files fail json.loads ... 2 project-memory/requests/*.json
files use an entirely different, envelope-less schema") into a real, rerunnable tool, so
those numbers stop being a point-in-time claim nobody can reproduce.

This script:

1. Scans project-memory/requests/**/*.json (recursively -- the corpus has one dated
   subdirectory, project-memory/requests/2026-08-25/, that a purely top-level glob would
   miss; see "recursion note" below) against project-memory/receipts/*.receipt.json,
   matching by filename stem (request "X.json" <-> receipt "X.receipt.json"; receipts
   live flat regardless of which directory depth the request came from -- confirmed
   against the real corpus).
2. Reports:
   - requests with no matching receipt, broken down by operation (and by the coarser
     mutating vs. read-only split -- MUTATING_OPERATIONS below).
   - receipts with no matching request.
   - requests that fail json.loads (with the parse error).
   - requests that parse as JSON but do not look like the expected request envelope
     (missing an "operation" key -- e.g. the "project2.work_claim" schema noted in the
     tracker). Reported separately from orphans/parse-failures since these can (and in
     the real corpus, do) still have a matching receipt that correctly REFUSED them.
   - receipts with standing == "BUILD_BROKEN".
3. Is READ-ONLY. It only ever calls Path.read_text/glob/rglob/stat under the requests
   and receipts directories -- never write_text, unlink, rename, or shutil.move/copy on
   anything under project-memory/. It writes only to stdout, and optionally to a
   caller-chosen --output path that this script itself refuses to accept if it resolves
   under project-memory/ (see _reject_output_inside_project_memory).
4. Exits non-zero (see main()) when the count of orphan MUTATING-operation requests
   exceeds --mutating-orphan-threshold (default 0) -- these are the ones whose real
   effect on the live GitHub Project board is UNKNOWN, not ALIVE or REFUSED (see
   MUTATING_OPERATIONS docstring). Every other finding (orphan receipts, parse failures,
   schema anomalies, BUILD_BROKEN receipts) is reported but never affects the exit code
   -- they are historical-provenance/informational by nature, not "did a live mutation
   maybe silently fail to land" the way an orphan mutating request is. A future CI wiring
   can therefore treat this script's exit code as an informational (non-blocking) signal
   simply by using it as-is, or force it non-fatal with a workflow-level
   `continue-on-error: true` / `|| true` -- no separate "informational mode" flag needed.

Recursion note: the original manual audit's "5 receipts have no matching request in the
other direction" figure turns out to be an artifact of NOT recursing into
project-memory/requests/2026-08-25/ -- 4 of those 5 "orphan" receipts actually match a
request that lives in that subdirectory (confirmed by hand against the real corpus while
building this script); recursing (as this script does) finds the true number, which as of
this writing is 0. This script's numbers are the reproducible ones; a future re-run that
disagrees with this docstring's numbers means the corpus changed, not that the tool is
wrong.

This module exposes plain functions/dataclasses (scan, Report, load_json_safe, ...) so
tests can drive it against synthetic fixtures in a temp directory without touching the
real project-memory/ corpus.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

# Operations whose real effect is a write against the live GitHub Project board (see
# project-memory/README.md's "Operations" section). Deliberately broader than
# scripts/project_memory_prune.py's WRITE_OPERATIONS: prune.py only cares about
# operations that write a superseding "current"/"latest" *pointer key* (so it excludes
# memory.archive/memory.delete, which don't write such a key); this script cares about
# "did any live mutation happen at all", which is exactly the set docs/errc-tracker.md's
# RAISE item itself counts (its 52-orphan breakdown includes 1 memory.archive).
MUTATING_OPERATIONS = {
    "memory.create",
    "memory.update",
    "memory.upsert",
    "memory.archive",
    "memory.delete",
}

REQUEST_RECEIPT_SUFFIX = ".receipt.json"


def load_json_safe(path: Path) -> tuple[Any, str | None]:
    """Returns (parsed_value, None) on success, or (None, error_message) on failure.

    Mirrors scripts/project_memory_prune.py's helper of the same name, except it does
    not require the top-level value to be an object -- a request/receipt file whose
    top-level JSON value is not an object is itself a schema anomaly this script wants
    to report, not something to fold silently into "unparseable".
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return data, None


def receipt_stem(path: Path) -> str | None:
    """Strips the '.receipt.json' suffix from a receipt filename, or None if absent."""
    name = path.name
    if not name.endswith(REQUEST_RECEIPT_SUFFIX):
        return None
    return name[: -len(REQUEST_RECEIPT_SUFFIX)]


def describe_schema_anomaly(data: Any) -> str:
    if not isinstance(data, dict):
        return f"top-level JSON value is {type(data).__name__}, not an object"
    if "operation" not in data:
        alt_type = data.get("type")
        if alt_type is not None:
            return f"missing 'operation' key (has 'type': {alt_type!r} instead)"
        return "missing 'operation' key"
    return "unrecognized shape"


@dataclass
class ParseFailure:
    path: Path
    error: str


@dataclass
class SchemaAnomaly:
    path: Path
    stem: str
    reason: str


@dataclass
class OrphanRequest:
    path: Path
    stem: str
    operation: str | None
    mutating: bool


@dataclass
class OrphanReceipt:
    path: Path
    stem: str
    operation: str | None
    standing: str | None


@dataclass
class BuildBrokenReceipt:
    path: Path
    stem: str
    reason: str | None


@dataclass
class Report:
    requests_dir: Path
    receipts_dir: Path
    total_requests: int = 0
    total_receipts: int = 0
    parse_failures: list[ParseFailure] = field(default_factory=list)
    schema_anomalies: list[SchemaAnomaly] = field(default_factory=list)
    orphan_requests: list[OrphanRequest] = field(default_factory=list)
    orphan_receipts: list[OrphanReceipt] = field(default_factory=list)
    receipt_parse_failures: list[ParseFailure] = field(default_factory=list)
    build_broken_receipts: list[BuildBrokenReceipt] = field(default_factory=list)

    @property
    def orphan_request_count(self) -> int:
        return len(self.orphan_requests)

    @property
    def orphan_receipt_count(self) -> int:
        return len(self.orphan_receipts)

    @property
    def mutating_orphan_requests(self) -> list[OrphanRequest]:
        return [r for r in self.orphan_requests if r.mutating]

    @property
    def mutating_orphan_count(self) -> int:
        return len(self.mutating_orphan_requests)

    @property
    def orphan_requests_by_operation(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.orphan_requests:
            key = r.operation if r.operation is not None else "(missing operation)"
            counts[key] = counts.get(key, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        def rel(p: Path) -> str:
            try:
                return str(p.relative_to(REPO_ROOT))
            except ValueError:
                return str(p)

        return {
            "requests_dir": rel(self.requests_dir),
            "receipts_dir": rel(self.receipts_dir),
            "total_requests": self.total_requests,
            "total_receipts": self.total_receipts,
            "orphan_requests": {
                "count": self.orphan_request_count,
                "mutating_count": self.mutating_orphan_count,
                "read_only_count": self.orphan_request_count - self.mutating_orphan_count,
                "by_operation": dict(sorted(self.orphan_requests_by_operation.items())),
                "items": [
                    {
                        "path": rel(r.path),
                        "operation": r.operation,
                        "mutating": r.mutating,
                    }
                    for r in self.orphan_requests
                ],
            },
            "orphan_receipts": {
                "count": self.orphan_receipt_count,
                "items": [
                    {"path": rel(r.path), "operation": r.operation, "standing": r.standing}
                    for r in self.orphan_receipts
                ],
            },
            "parse_failures": {
                "count": len(self.parse_failures),
                "items": [{"path": rel(f.path), "error": f.error} for f in self.parse_failures],
            },
            "schema_anomalies": {
                "count": len(self.schema_anomalies),
                "items": [{"path": rel(a.path), "reason": a.reason} for a in self.schema_anomalies],
            },
            "receipt_parse_failures": {
                "count": len(self.receipt_parse_failures),
                "items": [{"path": rel(f.path), "error": f.error} for f in self.receipt_parse_failures],
            },
            "build_broken_receipts": {
                "count": len(self.build_broken_receipts),
                "items": [
                    {"path": rel(b.path), "reason": b.reason} for b in self.build_broken_receipts
                ],
            },
        }


def scan(requests_dir: Path, receipts_dir: Path) -> Report:
    """Builds a Report by reading (never writing) requests_dir and receipts_dir.

    Requests are discovered recursively (rglob) -- see module docstring's "recursion
    note". Receipts are also discovered recursively for robustness, though the real
    corpus keeps them flat directly under receipts_dir; matching is by filename stem
    regardless of either side's directory depth, so this choice is not load-bearing
    for the real corpus today.
    """
    report = Report(requests_dir=requests_dir, receipts_dir=receipts_dir)

    request_files = sorted(p for p in requests_dir.rglob("*.json") if p.is_file())
    receipt_files = sorted(
        p for p in receipts_dir.rglob("*" + REQUEST_RECEIPT_SUFFIX) if p.is_file()
    )

    report.total_requests = len(request_files)
    report.total_receipts = len(receipt_files)

    request_stems: dict[str, Path] = {}
    for path in request_files:
        # Real corpus has no stem collisions across directories (verified); the last
        # write wins on the rare chance of one, which only affects report completeness,
        # never correctness of what IS reported (never a write to the source tree).
        request_stems[path.stem] = path

    receipt_stems: dict[str, Path] = {}
    for path in receipt_files:
        stem = receipt_stem(path)
        if stem is None:
            continue
        receipt_stems[stem] = path

    for stem, path in request_stems.items():
        data, error = load_json_safe(path)
        if error is not None:
            report.parse_failures.append(ParseFailure(path=path, error=error))
            operation = None
        else:
            operation = data.get("operation") if isinstance(data, dict) else None
            if not isinstance(data, dict) or "operation" not in data:
                report.schema_anomalies.append(
                    SchemaAnomaly(path=path, stem=stem, reason=describe_schema_anomaly(data))
                )
        if stem not in receipt_stems:
            report.orphan_requests.append(
                OrphanRequest(
                    path=path,
                    stem=stem,
                    operation=operation,
                    mutating=operation in MUTATING_OPERATIONS,
                )
            )

    for stem, path in receipt_stems.items():
        data, error = load_json_safe(path)
        if error is not None:
            report.receipt_parse_failures.append(ParseFailure(path=path, error=error))
            continue
        standing = data.get("standing") if isinstance(data, dict) else None
        reason = data.get("reason") if isinstance(data, dict) else None
        operation = data.get("operation") if isinstance(data, dict) else None
        if stem not in request_stems:
            report.orphan_receipts.append(
                OrphanReceipt(path=path, stem=stem, operation=operation, standing=standing)
            )
        if standing == "BUILD_BROKEN":
            report.build_broken_receipts.append(
                BuildBrokenReceipt(path=path, stem=stem, reason=reason)
            )

    report.orphan_requests.sort(key=lambda r: r.path.as_posix())
    report.orphan_receipts.sort(key=lambda r: r.path.as_posix())
    report.parse_failures.sort(key=lambda f: f.path.as_posix())
    report.schema_anomalies.sort(key=lambda a: a.path.as_posix())
    report.receipt_parse_failures.sort(key=lambda f: f.path.as_posix())
    report.build_broken_receipts.sort(key=lambda b: b.path.as_posix())

    return report


def format_human_report(report: Report, mutating_orphan_threshold: int) -> str:
    lines: list[str] = []
    lines.append("project-memory/ orphan/health report")
    lines.append(f"  requests dir: {report.requests_dir}")
    lines.append(f"  receipts dir: {report.receipts_dir}")
    lines.append("")
    lines.append(f"total requests scanned: {report.total_requests}")
    lines.append(f"total receipts scanned: {report.total_receipts}")
    lines.append("")

    lines.append(
        f"requests with no matching receipt: {report.orphan_request_count} "
        f"({report.mutating_orphan_count} mutating, "
        f"{report.orphan_request_count - report.mutating_orphan_count} read-only)"
    )
    if report.orphan_requests:
        for op, count in sorted(report.orphan_requests_by_operation.items()):
            tag = "MUTATING" if op in MUTATING_OPERATIONS else "read-only"
            lines.append(f"    {op}: {count}  [{tag}]")
    lines.append("")

    lines.append(f"receipts with no matching request: {report.orphan_receipt_count}")
    for r in report.orphan_receipts:
        lines.append(f"    {r.path}  (operation={r.operation}, standing={r.standing})")
    lines.append("")

    lines.append(f"requests failing json.loads: {len(report.parse_failures)}")
    for f in report.parse_failures:
        lines.append(f"    {f.path}: {f.error}")
    lines.append("")

    lines.append(
        f"requests parsing but not matching the expected envelope schema: "
        f"{len(report.schema_anomalies)}"
    )
    for a in report.schema_anomalies:
        lines.append(f"    {a.path}: {a.reason}")
    lines.append("")

    lines.append(f"receipts with standing=BUILD_BROKEN: {len(report.build_broken_receipts)}")
    for b in report.build_broken_receipts:
        lines.append(f"    {b.path}  (reason={b.reason})")

    if report.receipt_parse_failures:
        lines.append("")
        lines.append(f"receipts failing json.loads: {len(report.receipt_parse_failures)}")
        for f in report.receipt_parse_failures:
            lines.append(f"    {f.path}: {f.error}")

    lines.append("")
    if report.mutating_orphan_count > mutating_orphan_threshold:
        lines.append(
            f"FAIL: {report.mutating_orphan_count} orphan mutating-operation request(s) "
            f"exceed threshold ({mutating_orphan_threshold}) -- their real effect on the "
            f"live GitHub Project board is UNKNOWN, not ALIVE or REFUSED."
        )
    else:
        lines.append(
            f"OK: orphan mutating-operation requests ({report.mutating_orphan_count}) "
            f"within threshold ({mutating_orphan_threshold})."
        )
    return "\n".join(lines)


def _reject_output_inside_project_memory(output_path: Path, root: Path) -> str | None:
    """Returns an error message if output_path resolves under root/project-memory, else None.

    This script must never write under project-memory/ (see module docstring point 3).
    Resolution happens against the parent directory (which must exist) rather than the
    possibly-not-yet-created file itself, so a not-yet-existing report file is still
    checked correctly.
    """
    project_memory_root = (root / "project-memory").resolve()
    candidate_dir = output_path.parent
    try:
        candidate_dir = candidate_dir.resolve()
    except OSError:
        pass
    try:
        candidate_dir.relative_to(project_memory_root)
    except ValueError:
        return None
    return (
        f"refusing to write --output under {project_memory_root} "
        f"(this script is read-only there); choose a path outside project-memory/"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repo root containing project-memory/ (default: this script's repo root).",
    )
    parser.add_argument("--requests-dir", type=Path, default=None, help="Override requests directory.")
    parser.add_argument("--receipts-dir", type=Path, default=None, help="Override receipts directory.")
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON instead of a human summary."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Also write the report to this path (same format as stdout: JSON if --json, "
            "else human text). Must NOT resolve under project-memory/ -- refused otherwise."
        ),
    )
    parser.add_argument(
        "--mutating-orphan-threshold",
        type=int,
        default=0,
        help=(
            "Exit non-zero only when the count of orphan MUTATING-operation requests "
            "exceeds this threshold (default: 0 -- any orphan mutating request fails)."
        ),
    )
    args = parser.parse_args(argv)

    requests_dir = args.requests_dir or (args.root / "project-memory" / "requests")
    receipts_dir = args.receipts_dir or (args.root / "project-memory" / "receipts")

    if not requests_dir.is_dir():
        print(f"requests directory not found: {requests_dir}", file=sys.stderr)
        return 2
    if not receipts_dir.is_dir():
        print(f"receipts directory not found: {receipts_dir}", file=sys.stderr)
        return 2

    output_text: str | None = None
    if args.output is not None:
        rejection = _reject_output_inside_project_memory(args.output, args.root)
        if rejection is not None:
            print(rejection, file=sys.stderr)
            return 2

    report = scan(requests_dir, receipts_dir)

    if args.json:
        payload = report.to_dict()
        payload["mutating_orphan_threshold"] = args.mutating_orphan_threshold
        payload["exit_ok"] = report.mutating_orphan_count <= args.mutating_orphan_threshold
        output_text = json.dumps(payload, indent=2, sort_keys=True)
    else:
        output_text = format_human_report(report, args.mutating_orphan_threshold)

    print(output_text)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text + "\n", encoding="utf-8")

    if report.mutating_orphan_count > args.mutating_orphan_threshold:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
