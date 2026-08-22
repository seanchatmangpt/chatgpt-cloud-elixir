#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/activate"
LOG="$ROOT/verification.log"
NETWORK_MODE="${CAPSULE_NETWORK_MODE:-hex_offline}"
ARCHIVE_DIGEST="${CAPSULE_ARCHIVE_DIGEST:-external-not-supplied}"

set +e
(
  set -e
  elixir "$ROOT/verifier/verify_manifest.exs" "$ROOT/manifest.json"
  elixir "$ROOT/verifier/verify_runtime.exs" "$ROOT/manifest.json"

  cd "$ROOT/subjects/ash_r2rml"
  echo ">>> [ash_r2rml] MIX_ENV=test mix compile --warnings-as-errors"
  MIX_ENV=test mix compile --warnings-as-errors
  echo ">>> [ash_r2rml] MIX_ENV=test mix test test/fortune5/"
  MIX_ENV=test mix test test/fortune5/

  cd "$ROOT/subjects/ex4pm"
  echo ">>> [ex4pm] mix verify"
  mix verify

  cd "$ROOT"
  bash "$ROOT/harness/verify.sh"
) 2>&1 | tee "$LOG"
STATUS=${PIPESTATUS[0]}
set -e

if [[ "$STATUS" -eq 0 ]]; then
  STANDING="ALIVE"
else
  STANDING="BUILD_BROKEN"
fi
MANIFEST_SHA="$(sha256sum "$ROOT/manifest.json" | awk '{print $1}')"
PROCESS_RECEIPT_SHA="missing"
[[ -f "$ROOT/harness/process-lab-receipt.json" ]] && PROCESS_RECEIPT_SHA="$(sha256sum "$ROOT/harness/process-lab-receipt.json" | awk '{print $1}')"
SOURCE_SHA="$(sed -n 's/.*"source_sha": "\([^"]*\)".*/\1/p' "$ROOT/manifest.json" | head -1)"
VERIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$ROOT/receipt.json" <<EOF2
{
  "schema_version": 1,
  "phase": "consumer_replay",
  "source_sha": "$SOURCE_SHA",
  "capsule_name": "process-intelligence",
  "capsule_archive_sha256": "$ARCHIVE_DIGEST",
  "manifest_sha256": "$MANIFEST_SHA",
  "process_lab_receipt_sha256": "$PROCESS_RECEIPT_SHA",
  "network_mode": "$NETWORK_MODE",
  "acceptance_command": "ash_r2rml compile + Fortune5 ETS; ex4pm mix verify; process-lab bridge",
  "acceptance_exit_code": $STATUS,
  "verified_at": "$VERIFIED_AT",
  "standing": "$STANDING",
  "replay": "CAPSULE_NETWORK_MODE=$NETWORK_MODE bash scripts/verify-capsule.sh"
}
EOF2
cat "$ROOT/receipt.json"
exit "$STATUS"
