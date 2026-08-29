#!/usr/bin/env bash
# Real PostgreSQL 17 acceptance for the ash-postgres capsule's `integration_fixture`.
#
# This is deliberately NOT part of scripts/build-capsule.sh / scripts/verify-capsule.sh /
# scripts/run-offline.sh. Those prove the ash-postgres capsule needs zero network to pass
# its acceptance command by running it inside a zero-network namespace — a real Postgres
# connection would always fail there regardless of correctness. This script instead runs
# directly against a live checkout with network + a reachable PostgreSQL 17 server, and
# proves the `external_crowns = ["postgresql"]` half of the contract declared in
# capsules/ash-postgres/capsule.toml. See that file's comment block for the full rationale
# and docs referencing capsules/process-intelligence/capsule.toml's identical
# standing_scope/external_crowns pattern.
#
# Usage: scripts/verify-ash-postgres-integration.sh
# Requires: elixir, mix, python3, network access to Hex, and PGHOST/PGPORT/PGUSER
#           reachable (defaults match capsules/postgres17's own convention:
#           127.0.0.1:55432, user postgres, trust auth / no password).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAPSULE_CONFIG="$ROOT/capsules/ash-postgres/capsule.toml"
VERSIONS="$ROOT/versions.toml"

for cmd in python3 elixir mix; do
  command -v "$cmd" >/dev/null || { echo "BLOCKED: required command '$cmd' is missing" >&2; exit 69; }
done
[[ -f "$CAPSULE_CONFIG" ]] || { echo "UNSUPPORTED: capsules/ash-postgres/capsule.toml not found" >&2; exit 64; }

export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-55432}"
export PGUSER="${PGUSER:-postgres}"

if command -v pg_isready >/dev/null 2>&1; then
  pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -t 10 \
    || { echo "BLOCKED: PostgreSQL not reachable at $PGHOST:$PGPORT — external_crowns=[\"postgresql\"] is not admitted in this environment" >&2; exit 69; }
fi

BUILD_ROOT="${CAPSULE_BUILD_ROOT:-$ROOT/.capsule-build/ash-postgres-integration}"
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT/project" "$BUILD_ROOT/host/mix" "$BUILD_ROOT/host/hex"
export MIX_HOME="$BUILD_ROOT/host/mix"
export HEX_HOME="$BUILD_ROOT/host/hex"

FIXTURE="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["integration_fixture"])' "$CAPSULE_CONFIG")"
[[ -d "$ROOT/fixtures/$FIXTURE" ]] || { echo "UNSUPPORTED: integration fixture '$FIXTURE' not found under fixtures/" >&2; exit 64; }
cp -a "$ROOT/fixtures/$FIXTURE/." "$BUILD_ROOT/project/"

EXPECTED_ELIXIR="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["runtime"]["elixir"])' "$VERSIONS")"

mix local.hex --force
mix local.rebar --force

# Same generation shape as scripts/build-capsule.sh: mix.exs deps come from the
# capsule's `packages` list, pinned to the exact versions.toml version.
python3 - "$VERSIONS" "$CAPSULE_CONFIG" "$BUILD_ROOT/project" "$EXPECTED_ELIXIR" <<'PY'
import pathlib, sys, tomllib
versions = tomllib.load(open(sys.argv[1], "rb"))
cfg = tomllib.load(open(sys.argv[2], "rb"))
project = pathlib.Path(sys.argv[3])
expected_elixir = sys.argv[4]
deps = []
for package in cfg.get("packages", []):
    version = versions["packages"][package]
    deps.append(f'{{:{package}, "== {version}"}}')
deps_text = ",\n        ".join(deps)
project.joinpath("mix.exs").write_text(f'''defmodule CloudCapsule.MixProject do
  use Mix.Project

  def project do
    [
      app: :cloud_capsule,
      version: "0.1.0",
      elixir: "~> {expected_elixir.rsplit(".", 1)[0]}",
      start_permanent: false,
      deps: deps()
    ]
  end

  def application, do: [extra_applications: [:logger]]

  defp deps do
    [
        {deps_text}
    ]
  end
end
''')
PY

pushd "$BUILD_ROOT/project" >/dev/null
mix deps.get

STATUS=0
INTEGRATION_ACCEPTANCE="$(python3 -c 'import tomllib,sys; print("\n".join(tomllib.load(open(sys.argv[1],"rb"))["integration_acceptance"]))' "$CAPSULE_CONFIG")"
LOG="$BUILD_ROOT/integration-test.log"
: > "$LOG"
set +e
while IFS= read -r cmd; do
  [[ -n "$cmd" ]] || continue
  echo "+ $cmd" | tee -a "$LOG"
  bash -c "$cmd" 2>&1 | tee -a "$LOG"
  STATUS=${PIPESTATUS[0]}
  [[ "$STATUS" -eq 0 ]] || break
done <<< "$INTEGRATION_ACCEPTANCE"
set -e
popd >/dev/null

[[ "$STATUS" -eq 0 ]] && STANDING="ALIVE" || STANDING="BUILD_BROKEN"
VERIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SOURCE_SHA="${GITHUB_SHA:-unknown}"
RECEIPT="$ROOT/ash-postgres-integration-receipt.json"
cat > "$RECEIPT" <<EOF
{
  "schema_version": 1,
  "phase": "external_crown_replay",
  "capsule_name": "ash-postgres",
  "external_crown": "postgresql",
  "source_sha": "$SOURCE_SHA",
  "acceptance_exit_code": $STATUS,
  "verified_at": "$VERIFIED_AT",
  "standing": "$STANDING",
  "note": "Additive integration tier; does not gate ash-postgres offline ALIVE standing (scripts/verify-capsule.sh).",
  "replay": "PGHOST=$PGHOST PGPORT=$PGPORT PGUSER=$PGUSER bash scripts/verify-ash-postgres-integration.sh"
}
EOF
cat "$RECEIPT"

if [[ "$STATUS" -ne 0 ]]; then
  echo "BUILD_BROKEN: ash-postgres integration acceptance failed — see $LOG" >&2
fi
exit "$STATUS"
