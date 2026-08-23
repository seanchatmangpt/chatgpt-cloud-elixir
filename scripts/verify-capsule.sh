#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/activate"
LOG="$ROOT/verification.log"
NETWORK_MODE="${CAPSULE_NETWORK_MODE:-hex_offline}"
ARCHIVE_DIGEST="${CAPSULE_ARCHIVE_DIGEST:-external-not-supplied}"
VERSIONS="$ROOT/source/versions.toml"

set +e
(
  set -e
  elixir "$ROOT/verifier/verify_manifest.exs" "$ROOT/manifest.json"
  elixir "$ROOT/verifier/verify_runtime.exs" "$ROOT/manifest.json"
  cd "$ROOT/project"
  MIX_ENV=test mix compile --warnings-as-errors
  MIX_ENV=test mix test
) 2>&1 | tee "$LOG"
STATUS=${PIPESTATUS[0]}
set -e

if [[ "$STATUS" -eq 0 ]]; then
  STANDING="ALIVE"
else
  STANDING="BUILD_BROKEN"
fi
MANIFEST_SHA="$(sha256sum "$ROOT/manifest.json" | awk '{print $1}')"
SOURCE_SHA="$(sed -n 's/.*"source_sha": "\([^"]*\)".*/\1/p' "$ROOT/manifest.json" | head -1)"
CAPSULE_NAME="$(sed -n 's/.*"capsule_name": "\([^"]*\)".*/\1/p' "$ROOT/manifest.json" | head -1)"
RELEASE_VERSION="$(python3 - "$VERSIONS" <<'PY'
import sys, tomllib
print(tomllib.load(open(sys.argv[1], "rb"))["release"]["version"])
PY
)"
VERIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "$ROOT/receipt.json" <<EOF
{
  "schema_version": 1,
  "phase": "consumer_replay",
  "source_sha": "$SOURCE_SHA",
  "release_version": "$RELEASE_VERSION",
  "capsule_name": "$CAPSULE_NAME",
  "capsule_archive_sha256": "$ARCHIVE_DIGEST",
  "manifest_sha256": "$MANIFEST_SHA",
  "network_mode": "$NETWORK_MODE",
  "acceptance_command": "MIX_ENV=test mix compile --warnings-as-errors && MIX_ENV=test mix test",
  "acceptance_exit_code": $STATUS,
  "verified_at": "$VERIFIED_AT",
  "standing": "$STANDING",
  "replay": "CAPSULE_NETWORK_MODE=$NETWORK_MODE bash scripts/verify-capsule.sh"
}
EOF
cat "$ROOT/receipt.json"
exit "$STATUS"
