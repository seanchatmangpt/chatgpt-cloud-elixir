#!/usr/bin/env python3
"""Admit a manufactured binary archive into the committed runtime/ tree.

Producer side of the committed-binary transport. The archive is copied byte-for-byte
(never rebuilt or recompressed) into runtime/<platform>/<name>/, split into parts no
larger than PART_SIZE so every committed file stays under GitHub's per-file limits and
is readable through the GitHub connector. runtime/lock.json records the whole-archive
digest, every part digest, the exact source identity, and who built it.

    python3 scripts/runtime-admit.py ggen dist/ggen-x86_64-unknown-linux-gnu.tar.gz \\
      --version 26.9.21 --source-repo seanchatmangpt/ggen --source-sha <40-hex> \\
      --builder upstream-release --origin-url <release asset url> \\
      --layout bin --bin ggen --smoke "ggen --version"

Consumers never run this; they run scripts/ecosystem-up.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
LOCK = RUNTIME / "lock.json"
PART_SIZE = 45 * 1024 * 1024
PLATFORM = "linux-x86_64"
BUILDERS = {"upstream-release", "local-container", "github-actions"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("name")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--builder", required=True, choices=sorted(BUILDERS))
    parser.add_argument("--origin-url", help="upstream URL the archive was obtained from, if any")
    parser.add_argument("--build-note", default="", help="toolchain / runner facts for provenance")
    parser.add_argument("--layout", required=True, choices=["capsule", "bin"],
                        help="capsule: extracted tree carries its own activate script; bin: executables at --bin paths")
    parser.add_argument("--bin", action="append", default=[], help="relative path of an executable (layout=bin)")
    parser.add_argument("--smoke", action="append", default=[], help="command that must exit 0 after activation")
    parser.add_argument("--verify", help="deeper consumer verification command, relative to the install dir")
    parser.add_argument("--not-default", action="store_true", help="install only when explicitly selected")
    parser.add_argument("--evidence", type=Path, help="JSON receipt of the admission-time consumer replay")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", args.name):
        raise SystemExit("REFUSED: artifact name must be lowercase [a-z0-9_.-]")
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
        raise SystemExit("REFUSED: --source-sha must be an exact 40-hex commit SHA")
    if args.layout == "bin" and not args.bin:
        raise SystemExit("REFUSED: layout=bin requires at least one --bin")
    if not args.smoke:
        raise SystemExit("REFUSED: at least one --smoke command is required")
    if not args.archive.is_file():
        raise SystemExit(f"BLOCKED: archive not found: {args.archive}")

    whole = sha256(args.archive)
    size = args.archive.stat().st_size
    dest = RUNTIME / PLATFORM / args.name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    parts = []
    with args.archive.open("rb") as source:
        index = 0
        while True:
            chunk = source.read(PART_SIZE)
            if not chunk:
                break
            suffix = "" if size <= PART_SIZE else f".part{index:02d}"
            part = dest / f"{args.archive.name}{suffix}"
            part.write_bytes(chunk)
            parts.append({
                "path": part.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(chunk).hexdigest(),
                "size": len(chunk),
            })
            index += 1

    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {
        "schema_version": 1,
        "platform": {"os": "linux", "arch": "x86_64", "built_on": "ubuntu-24.04 (glibc 2.39)"},
        "part_size_bytes": PART_SIZE,
        "artifacts": {},
    }
    evidence = json.loads(args.evidence.read_text()) if args.evidence else None
    lock["artifacts"][args.name] = {
        "version": args.version,
        "default": not args.not_default,
        "source": {"repository": args.source_repo, "sha": args.source_sha},
        "provenance": {
            "builder": args.builder,
            "origin_url": args.origin_url,
            "note": args.build_note,
            "admitted_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "archive": {"name": args.archive.name, "sha256": whole, "size": size, "format": "tar.gz"},
        "parts": parts,
        "install": {"layout": args.layout, "bin": args.bin, "verify": args.verify},
        "smoke": args.smoke,
        "admission_evidence": evidence,
    }
    lock["artifacts"] = dict(sorted(lock["artifacts"].items()))
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print(f"ADMITTED {args.name} {args.version} sha256={whole} parts={len(parts)} size={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
