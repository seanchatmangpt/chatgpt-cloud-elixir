#!/usr/bin/env python3
"""Bring the committed ecosystem runtime up in this container: offline, digest-verified.

Consumer side of the committed-binary transport. Reads runtime/lock.json, verifies every
committed part and the reassembled archive against their SHA-256, extracts each selected
artifact into a prefix, writes one env file that puts everything on PATH, smoke-executes
each artifact, and writes a receipt. There is no network access, no build, and no package fetch.

    python3 scripts/ecosystem-up.py                      # default artifacts
    python3 scripts/ecosystem-up.py --only ggen          # a subset
    python3 scripts/ecosystem-up.py --verify             # also run each capsule's own offline verifier
    source ~/.chatgpt-cloud/runtime/env.sh               # activate in the current shell

Idempotent: an artifact already installed at the same archive digest is not re-extracted.
Standing per artifact: ALIVE (digest verified + smoke exit 0) | BUILD_BROKEN (digest or
smoke failure) | BLOCKED (committed parts absent, e.g. a sparse checkout).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "runtime" / "lock.json"
DEFAULT_PREFIX = Path(os.environ.get("CHATGPT_CLOUD_RUNTIME_HOME", Path.home() / ".chatgpt-cloud" / "runtime"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install(name: str, spec: dict, prefix: Path) -> tuple[str, str]:
    """Return (standing, detail). Installs into prefix/name unless already current."""
    target = prefix / name
    marker = target / ".chatgpt-cloud-installed"
    if marker.is_file() and marker.read_text().strip() == spec["archive"]["sha256"]:
        return "INSTALLED", "already current"
    missing = [p["path"] for p in spec["parts"] if not (ROOT / p["path"]).is_file()]
    if missing:
        return "BLOCKED", f"committed parts absent (sparse or partial checkout?): {missing[0]}"
    for part in spec["parts"]:
        if sha256_file(ROOT / part["path"]) != part["sha256"]:
            return "BUILD_BROKEN", f"part digest mismatch: {part['path']}"
    with tempfile.TemporaryDirectory(dir=prefix) as tmp:
        archive = Path(tmp) / spec["archive"]["name"]
        whole = hashlib.sha256()
        with archive.open("wb") as out:
            for part in spec["parts"]:
                data = (ROOT / part["path"]).read_bytes()
                whole.update(data)
                out.write(data)
        if whole.hexdigest() != spec["archive"]["sha256"]:
            return "BUILD_BROKEN", "reassembled archive digest mismatch"
        staging = Path(tmp) / "tree"
        staging.mkdir()
        proc = subprocess.run(["tar", "-xzf", str(archive), "-C", str(staging)], capture_output=True, text=True)
        if proc.returncode != 0:
            return "BUILD_BROKEN", f"extract failed: {proc.stderr.strip()[:200]}"
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    marker.write_text(spec["archive"]["sha256"] + "\n")
    return "INSTALLED", "extracted"


def root_var(name: str) -> str:
    return "CHATGPT_CLOUD_" + re.sub(r"[^A-Z0-9]", "_", name.upper()) + "_ROOT"


def env_lines(name: str, spec: dict, prefix: Path) -> list[str]:
    # Capsule activate scripts all export CAPSULE_ROOT (last one wins), so every
    # artifact also gets a stable, unambiguous root variable.
    target = prefix / name
    lines = [f"export {root_var(name)}={shlex.quote(str(target))}"]
    if spec["install"]["layout"] == "capsule":
        return lines + [f"source {shlex.quote(str(target / 'activate'))}"]
    dirs = sorted({str((target / b).parent) for b in spec["install"]["bin"]})
    return lines + [f'export PATH={shlex.quote(d)}:"$PATH"' for d in dirs]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--prefix", type=Path, default=DEFAULT_PREFIX)
    parser.add_argument("--only", help="comma-separated artifact names (default: every default artifact)")
    parser.add_argument("--verify", action="store_true", help="also run each artifact's own offline verifier")
    parser.add_argument("--env-file", type=Path, help="append `source <prefix>/env.sh` here (e.g. $CLAUDE_ENV_FILE)")
    parser.add_argument("--allow-hex-network", action="store_true",
                        help="unset HEX_OFFLINE after activation (network-capable dev sessions); --verify stays offline")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not LOCK.is_file():
        print("BLOCKED: runtime/lock.json not present", file=sys.stderr)
        return 69
    lock = json.loads(LOCK.read_text())
    artifacts = lock["artifacts"]
    if args.only:
        names = [n.strip() for n in args.only.split(",") if n.strip()]
        unknown = [n for n in names if n not in artifacts]
        if unknown:
            print(f"UNSUPPORTED: unknown artifact(s): {unknown}", file=sys.stderr)
            return 64
    else:
        names = [n for n, spec in artifacts.items() if spec.get("default", True)]

    prefix = args.prefix.expanduser().resolve()
    prefix.mkdir(parents=True, exist_ok=True)
    rows: dict[str, dict] = {}
    env = ["# generated by scripts/ecosystem-up.py; source this file to activate", 'export ELIXIR_ERL_OPTIONS="${ELIXIR_ERL_OPTIONS:-+fnu}"']
    for name in names:
        spec = artifacts[name]
        standing, detail = install(name, spec, prefix)
        rows[name] = {"version": spec["version"], "archive_sha256": spec["archive"]["sha256"], "install": detail}
        if standing in ("BLOCKED", "BUILD_BROKEN"):
            rows[name]["standing"] = standing
            continue
        env += env_lines(name, spec, prefix)
    if args.allow_hex_network:
        env.append("unset HEX_OFFLINE")
    env_path = prefix / "env.sh"
    env_path.write_text("\n".join(env) + "\n")

    for name in names:
        row = rows[name]
        if "standing" in row:
            continue
        spec = artifacts[name]
        checks = list(spec["smoke"])
        if args.verify and spec["install"].get("verify"):
            checks.append(
                f"cd {shlex.quote(str(prefix / name))} && "
                f"CAPSULE_ARCHIVE_DIGEST={spec['archive']['sha256']} {spec['install']['verify']}"
            )
        results = []
        for command in checks:
            proc = subprocess.run(["bash", "-c", f"source {shlex.quote(str(env_path))} >/dev/null 2>&1; {command}"],
                                  capture_output=True, text=True)
            results.append({"command": command, "exit": proc.returncode,
                            "output": (proc.stdout.strip() or proc.stderr.strip()).splitlines()[-1:] })
        row["checks"] = results
        row["standing"] = "ALIVE" if all(r["exit"] == 0 for r in results) else "BUILD_BROKEN"

    receipt = {
        "schema_version": 1,
        "check": "ecosystem_up",
        "repository": "seanchatmangpt/chatgpt-cloud-elixir",
        "lock_sha256": sha256_file(LOCK),
        "prefix": str(prefix),
        "env_file": str(env_path),
        "observed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "network_used": False,
        "artifacts": rows,
        "standing": "ALIVE" if rows and all(r["standing"] == "ALIVE" for r in rows.values()) else "PARTIAL_ALIVE",
    }
    (prefix / "ecosystem-up-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    if args.env_file:
        with args.env_file.open("a") as handle:
            handle.write(f"source {shlex.quote(str(env_path))}\n")

    if not args.quiet:
        for name, row in rows.items():
            print(f"{row['standing']:<12} {name:<24} {row['version']:<12} {row['install']}")
        print(f"ECOSYSTEM_UP={receipt['standing']} artifacts={len(rows)} env={env_path}")
    return 0 if receipt["standing"] == "ALIVE" else 65


if __name__ == "__main__":
    raise SystemExit(main())
