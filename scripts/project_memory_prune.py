#!/usr/bin/env python3
"""Archival/pruning policy for project-memory/ transport files.

project-memory/requests/*.json and project-memory/receipts/*.receipt.json grow without
bound (see docs/errc-tracker.md CREATE: "No pruning/archival/rotation policy anywhere
for project-memory/"). Many requests upsert a "current"/"latest"-style pointer memory
key (dfcm/ledger/current, dfcm/select/latest, ...) -- see project-memory/README.md's
"DfCM shared-memory convention" table. A later write to the same pointer key supersedes
an earlier one: the Project board (canonical memory) only ever reflects the newest
write, so once a newer request/receipt pair for a given key exists, the older pair is
pure historical provenance -- safe to move out of the live directories without losing
any information, as long as it is moved, never deleted.

This script:

1. Scans project-memory/requests/*.json and project-memory/receipts/*.receipt.json.
2. For each request that performs a memory write (memory.create / memory.update /
   memory.upsert) targeting a key that looks like a "current"/"latest" pointer
   (heuristic: the key ends in "/current" or "/latest", case-insensitively --
   confirmed against the real corpus: dfcm/ledger/current, dfcm/select/latest,
   ggen/fanout/current, dfcm/run-control/select/current, etc. -- see
   docs/errc-tracker.md and project-memory/README.md's key table), groups requests by
   key and orders them by the request's own filename timestamp.
3. Every request for a key except the single newest one is an archival candidate --
   paired with its receipt file when one exists (project-memory/README.md documents
   16% of requests have no matching receipt; a candidate request with no receipt is
   still archived, receipt-less).
4. Defaults to dry-run: reports counts/timestamps/size, changes nothing.
5. --apply moves (never deletes) each candidate's request and, if present, receipt
   into project-memory/archive/<YYYY-MM>/{requests,receipts}/<original filename>,
   bucketed by the request's own month. Filenames are preserved exactly.

Deliberately NOT touched by this policy, even under --apply:

- The single most-recent request/receipt for every key (stays live).
- Read-only operations (memory.read, memory.query, memory.archive, memory.delete,
  project.snapshot, project.items, project.services) -- they don't write a key, so
  there is nothing for a later write to "supersede".
- Non-pointer keys, e.g. the immutable append-only `dfcm/run/<cell>/<UTC>/<head>`
  history convention, `plant/claims/...`/`plant/credits/...`/`plant/ws*/run_lease`
  leasing records, and one-off keys -- these are not "current"-style pointers and are
  never grouped for supersession even if (by coincidence) the same key is written
  more than once.
- Files that fail json.loads (docs/errc-tracker.md notes 13 such requests, a known
  systematic trailing-brace corruption) -- unparseable, so no key can be determined;
  reported as skipped, never moved.
- Requests whose filename does not carry a recognizable leading timestamp -- ordering
  candidates by an unreliable signal (e.g. filesystem mtime, which is not preserved by
  git) is worse than not ordering them at all; reported as skipped, never moved.

This module exposes plain functions (parse_filename_timestamp, extract_write_key,
build_plan, apply_plan) so tests can drive it against synthetic fixtures in a temp
directory without touching the real project-memory/ corpus.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

# Operations that write a memory record. memory.read/query/archive/delete and the
# project.* read-only operations never write a key and are never pruning candidates.
WRITE_OPERATIONS = {"memory.create", "memory.update", "memory.upsert"}

# "current"/"latest" pointer-style key heuristic, confirmed against the real corpus
# (see module docstring). Case-insensitive so "Current"/"LATEST" style keys still match.
POINTER_KEY_RE = re.compile(r"/(current|latest)$", re.IGNORECASE)

# Request filenames observed in the corpus: YYYYMMDDTHHMMSSZ-, YYYYMMDDTHHMMZ- (no
# seconds), or bare YYYYMMDD- (no time-of-day at all). All three are accepted; the
# missing components default to zero so ordering stays a total order within a day.
TIMESTAMP_RE = re.compile(
    r"^(?P<y>\d{4})(?P<mo>\d{2})(?P<d>\d{2})"
    r"(?:T(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})?Z)?"
    r"-"
)


def parse_filename_timestamp(filename: str) -> tuple[str, str] | None:
    """Extract a sortable timestamp and YYYY-MM archive bucket from a request filename.

    Returns (sortable 'YYYYMMDDHHMMSS' string, 'YYYY-MM' bucket), or None when the
    filename does not start with a recognizable timestamp -- callers must treat those
    files as unorderable, not fall back to some other signal (see module docstring).
    """
    match = TIMESTAMP_RE.match(filename)
    if not match:
        return None
    y, mo, d = match.group("y"), match.group("mo"), match.group("d")
    h = match.group("h") or "00"
    mi = match.group("mi") or "00"
    s = match.group("s") or "00"
    return f"{y}{mo}{d}{h}{mi}{s}", f"{y}-{mo}"


def load_json_safe(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Returns (parsed_dict, None) on success, or (None, error_message) on failure."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, "top-level JSON value is not an object"
    return data, None


def extract_write_key(request: dict[str, Any]) -> str | None:
    """Mirrors scripts/project_memory_proxy.py's execute_request() key resolution.

    memory.create / memory.upsert resolve the record via `payload.get("record") or
    payload`, then read `.key` from it. memory.update instead takes `key` as a
    separate top-level payload parameter (the record itself may omit it) -- so it is
    checked first, falling back to record.key for the (implicitly-allowed) case where
    a caller also repeated the key inside `record`.
    """
    operation = request.get("operation")
    if operation not in WRITE_OPERATIONS:
        return None
    payload = request.get("payload")
    if not isinstance(payload, dict):
        return None
    record = payload.get("record")
    if not isinstance(record, dict):
        record = payload
    if operation == "memory.update":
        key = payload.get("key") or record.get("key")
    else:
        key = record.get("key")
    if key is None:
        return None
    key = str(key).strip()
    return key or None


def is_pointer_key(key: str) -> bool:
    return bool(POINTER_KEY_RE.search(key))


@dataclass
class Candidate:
    key: str
    request_path: Path
    receipt_path: Path | None
    sortable_ts: str
    month_bucket: str
    size_bytes: int


@dataclass
class SkipReason:
    path: Path
    reason: str


@dataclass
class Plan:
    candidates: list[Candidate] = field(default_factory=list)
    kept_live: dict[str, Path] = field(default_factory=dict)
    skipped_unparseable: list[SkipReason] = field(default_factory=list)
    skipped_no_timestamp: list[Path] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.candidates)

    @property
    def total_size_bytes(self) -> int:
        return sum(c.size_bytes for c in self.candidates)

    @property
    def oldest_ts(self) -> str | None:
        return min((c.sortable_ts for c in self.candidates), default=None)

    @property
    def newest_ts(self) -> str | None:
        return max((c.sortable_ts for c in self.candidates), default=None)

    def to_report(self) -> dict[str, Any]:
        per_key: dict[str, int] = {}
        for c in self.candidates:
            per_key[c.key] = per_key.get(c.key, 0) + 1
        return {
            "candidate_count": self.count,
            "total_size_bytes": self.total_size_bytes,
            "oldest_timestamp": self.oldest_ts,
            "newest_timestamp": self.newest_ts,
            "candidates_per_key": dict(sorted(per_key.items())),
            "keys_with_live_pointer_kept": len(self.kept_live),
            "skipped_unparseable_count": len(self.skipped_unparseable),
            "skipped_no_timestamp_count": len(self.skipped_no_timestamp),
            "candidates": [
                {
                    "key": c.key,
                    "request": str(c.request_path),
                    "receipt": str(c.receipt_path) if c.receipt_path else None,
                    "timestamp": c.sortable_ts,
                    "month_bucket": c.month_bucket,
                    "size_bytes": c.size_bytes,
                }
                for c in self.candidates
            ],
        }


def build_plan(requests_dir: Path, receipts_dir: Path) -> Plan:
    plan = Plan()
    by_key: dict[str, list[tuple[str, str, Path]]] = {}  # key -> [(sortable_ts, filename, path)]

    for request_path in sorted(requests_dir.glob("*.json")):
        ts_bucket = parse_filename_timestamp(request_path.name)
        data, error = load_json_safe(request_path)
        if error is not None:
            plan.skipped_unparseable.append(SkipReason(request_path, error))
            continue
        assert data is not None
        key = extract_write_key(data)
        if key is None or not is_pointer_key(key):
            continue
        if ts_bucket is None:
            plan.skipped_no_timestamp.append(request_path)
            continue
        sortable_ts, _month = ts_bucket
        by_key.setdefault(key, []).append((sortable_ts, request_path.name, request_path))

    for key, entries in by_key.items():
        entries.sort(key=lambda e: (e[0], e[1]))  # (timestamp, filename) total order
        live_ts, live_name, live_path = entries[-1]
        plan.kept_live[key] = live_path
        for sortable_ts, name, request_path in entries[:-1]:
            month_bucket = f"{sortable_ts[0:4]}-{sortable_ts[4:6]}"
            receipt_name = request_path.stem + ".receipt.json"
            receipt_path = receipts_dir / receipt_name
            size = request_path.stat().st_size
            if receipt_path.is_file():
                size += receipt_path.stat().st_size
            else:
                receipt_path = None
            plan.candidates.append(
                Candidate(
                    key=key,
                    request_path=request_path,
                    receipt_path=receipt_path,
                    sortable_ts=sortable_ts,
                    month_bucket=month_bucket,
                    size_bytes=size,
                )
            )

    plan.candidates.sort(key=lambda c: (c.sortable_ts, c.request_path.name))
    return plan


def apply_plan(plan: Plan, archive_dir: Path) -> list[tuple[Path, Path]]:
    """Moves (never deletes) every candidate's request/receipt into archive_dir.

    Returns the list of (source, destination) pairs actually moved. Idempotent: if a
    destination already exists (a previous --apply run already moved it), that file is
    left alone rather than raising or overwriting.
    """
    moved: list[tuple[Path, Path]] = []
    for candidate in plan.candidates:
        month_dir = archive_dir / candidate.month_bucket
        dest_requests = month_dir / "requests"
        dest_receipts = month_dir / "receipts"
        dest_requests.mkdir(parents=True, exist_ok=True)

        request_dest = dest_requests / candidate.request_path.name
        if candidate.request_path.is_file() and not request_dest.exists():
            shutil.move(str(candidate.request_path), str(request_dest))
            moved.append((candidate.request_path, request_dest))

        if candidate.receipt_path is not None and candidate.receipt_path.is_file():
            dest_receipts.mkdir(parents=True, exist_ok=True)
            receipt_dest = dest_receipts / candidate.receipt_path.name
            if not receipt_dest.exists():
                shutil.move(str(candidate.receipt_path), str(receipt_dest))
                moved.append((candidate.receipt_path, receipt_dest))

    return moved


def format_human_report(plan: Plan, applied: list[tuple[Path, Path]] | None) -> str:
    lines = []
    lines.append(f"candidates: {plan.count}")
    lines.append(f"total size: {plan.total_size_bytes} bytes")
    lines.append(f"oldest timestamp: {plan.oldest_ts}")
    lines.append(f"newest timestamp: {plan.newest_ts}")
    lines.append(f"live pointer keys kept (never touched): {len(plan.kept_live)}")
    lines.append(f"skipped (unparseable JSON): {len(plan.skipped_unparseable)}")
    lines.append(f"skipped (no recognizable filename timestamp): {len(plan.skipped_no_timestamp)}")
    if plan.candidates:
        lines.append("")
        lines.append("candidates by key:")
        per_key: dict[str, int] = {}
        for c in plan.candidates:
            per_key[c.key] = per_key.get(c.key, 0) + 1
        for key, count in sorted(per_key.items()):
            lines.append(f"  {key}: {count}")
    if applied is not None:
        lines.append("")
        lines.append(f"APPLIED: moved {len(applied)} files into archive/")
    else:
        lines.append("")
        lines.append("DRY RUN -- no filesystem changes made. Pass --apply to move these files.")
    return "\n".join(lines)


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
    parser.add_argument("--archive-dir", type=Path, default=None, help="Override archive directory.")
    parser.add_argument("--apply", action="store_true", help="Move candidates into archive/ (default: dry-run).")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a human summary.")
    args = parser.parse_args(argv)

    requests_dir = args.requests_dir or (args.root / "project-memory" / "requests")
    receipts_dir = args.receipts_dir or (args.root / "project-memory" / "receipts")
    archive_dir = args.archive_dir or (args.root / "project-memory" / "archive")

    if not requests_dir.is_dir():
        print(f"requests directory not found: {requests_dir}", file=sys.stderr)
        return 2

    plan = build_plan(requests_dir, receipts_dir)

    applied: list[tuple[Path, Path]] | None = None
    if args.apply:
        applied = apply_plan(plan, archive_dir)

    if args.json:
        report = plan.to_report()
        if applied is not None:
            report["applied"] = True
            report["moved"] = [{"from": str(src), "to": str(dst)} for src, dst in applied]
        else:
            report["applied"] = False
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_human_report(plan, applied))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
