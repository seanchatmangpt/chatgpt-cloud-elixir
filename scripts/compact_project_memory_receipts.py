#!/usr/bin/env python3
"""Squash a run of consecutive `receipt: Project v2 memory proxy` commits.

`.github/workflows/project-memory-proxy.yml` commits once per proxy run (that
serialization is load-bearing: Project #2 is one shared mutable control plane
and the workflow's `concurrency` group depends on one commit per run to keep
rebase-retry correct — see docs/swarm-noise-budget.md). At high automation
cadence that still produces long runs of small commits in git history.

This is a maintainer tool for *retroactively* compacting an already-landed run
of those commits into one, on a branch you control. It never touches the live
push-triggered workflow's behavior or a shared branch's history without
`--force` (the whole point of squashing is a history rewrite — never do that on
a branch other people build on without coordinating first).

Usage:
    # Dry run: show what would be squashed on the current branch, don't touch anything.
    scripts/compact_project_memory_receipts.py

    # Actually rewrite the current branch (creates a backup ref first).
    scripts/compact_project_memory_receipts.py --apply

    # Look further back / require a longer run before acting.
    scripts/compact_project_memory_receipts.py --apply --max-lookback 500 --min-run 3
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBJECT_PREFIX = "receipt: Project v2 memory proxy"


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        print(f"BLOCKED: git {' '.join(args)} failed:\n{result.stderr}", file=sys.stderr)
        raise SystemExit(69)
    return result.stdout


def find_trailing_run(max_lookback: int) -> list[str]:
    """Return SHAs (oldest first) of the contiguous single-parent run of receipt
    commits at HEAD.

    Walks the actual parent chain one hop at a time (not `git log`'s printed
    order) and stops at the first commit that isn't a receipt commit OR has more
    than one parent. `git log`'s default order is commit-date order across the
    *whole* reachable graph, not ancestry order — on a history with merged
    branches (this repo's included: HEAD is a chain of merge commits), two
    same-subject commits can print adjacently without one being the other's
    parent. Squashing on that false assumption would silently fold unrelated
    commits — from a different branch, on the other side of a merge — into the
    result and drop them from reachable history.
    """
    run: list[str] = []
    sha = git("rev-parse", "HEAD").strip()
    for _ in range(max_lookback):
        line = git("log", "-1", "--format=%H\t%P\t%s", sha).strip()
        commit_sha, _, rest = line.partition("\t")
        parents, _, subject = rest.partition("\t")
        parent_list = parents.split()
        if len(parent_list) != 1 or not subject.startswith(SUBJECT_PREFIX):
            break
        run.append(commit_sha)
        sha = parent_list[0]
    run.reverse()
    return run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-lookback",
        type=int,
        default=200,
        help="how many commits back from HEAD to scan for a trailing receipt run (default 200)",
    )
    parser.add_argument(
        "--min-run",
        type=int,
        default=2,
        help="minimum run length worth squashing (default 2 — squashing 1 commit is a no-op)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually rewrite HEAD (default: dry run / report only)",
    )
    args = parser.parse_args()

    status = git("status", "--porcelain")
    if status.strip():
        print("BLOCKED: working tree is not clean; commit or stash before compacting", file=sys.stderr)
        return 69

    run = find_trailing_run(args.max_lookback)
    if len(run) < args.min_run:
        print(
            f"no trailing run of >= {args.min_run} '{SUBJECT_PREFIX}' commits found "
            f"in the last {args.max_lookback} commits (found {len(run)})"
        )
        return 0

    base = run[0] + "~1"
    print(f"found {len(run)} consecutive receipt commits: {run[0][:12]}..{run[-1][:12]}")

    if not args.apply:
        print("dry run only — pass --apply to squash them into one commit")
        return 0

    backup_ref = f"refs/backup/pre-compact-{run[-1][:12]}"
    git("update-ref", backup_ref, "HEAD")
    print(f"backup ref created: {backup_ref} (delete with: git update-ref -d {backup_ref})")

    receipt_files = sorted(
        set(
            line
            for sha in run
            for line in git("diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines()
        )
    )
    subject = f"{SUBJECT_PREFIX} (compacted {len(run)} commits, {len(receipt_files)} receipts)"

    git("reset", "--soft", base)
    git("commit", "-m", subject)
    new_head = git("rev-parse", "HEAD").strip()
    print(f"squashed {len(run)} commits into {new_head[:12]}: {subject}")
    print("this rewrote local history — push with care (force-with-lease) and only to a branch you own")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
