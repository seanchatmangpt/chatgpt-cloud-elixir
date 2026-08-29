#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/lib/verify-capsule-common.sh"
# This script enforces no network fencing of its own -- unshare -n / the dead
# loopback proxy live in scripts/run-offline.sh, which sets CAPSULE_NETWORK_MODE
# before invoking this file. Defaulting to "hex_offline" here (rather than an
# honest "unfenced" sentinel) made a direct, unfenced call to this script produce
# a receipt that looked identically offline-fenced to a real run-offline.sh replay
# -- see docs/errc-tracker.md's offline-law RAISE item.
NETWORK_MODE="${CAPSULE_NETWORK_MODE:-unfenced_direct_call}"
VERSIONS="$ROOT/source/versions.toml"

verification_body() {
  capsule_verify_manifest_and_runtime
  cd "$ROOT/project"
  MIX_ENV=test mix compile --warnings-as-errors
  MIX_ENV=test mix test
}
capsule_run_logged verification_body

STANDING="$(capsule_standing_from_status "$STATUS")"
MANIFEST_SHA="$(capsule_manifest_sha)"
SOURCE_SHA="$(capsule_source_sha)"
CAPSULE_NAME="$(sed -n 's/.*"capsule_name": "\([^"]*\)".*/\1/p' "$ROOT/manifest.json" | head -1)"
RELEASE_VERSION="$(awk '
  /^\[release\]$/ { in_release=1; next }
  /^\[/ { in_release=0 }
  in_release && /^version[[:space:]]*=/ {
    value=$0
    sub(/^[^=]*=[[:space:]]*/, "", value)
    gsub(/"/, "", value)
    print value
    exit
  }
' "$VERSIONS")"
[[ -n "$RELEASE_VERSION" ]] || { echo "BUILD_BROKEN: embedded release.version missing" >&2; exit 65; }
VERIFIED_AT="$(capsule_verified_at)"
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
  "replay": "bash scripts/run-offline.sh"
}
EOF
cat "$ROOT/receipt.json"

"$(dirname "${BASH_SOURCE[0]}")/emit-ocel-capsule-event.sh" \
  --agent-id "capsule-verify:${CAPSULE_NAME:-unknown}" \
  --run-id "${CAPSULE_NAME:-unknown}:${MANIFEST_SHA}" \
  --activity "capsule.verify" \
  --standing "$STANDING" \
  --occurred-at "$VERIFIED_AT" \
  --subject-sha "$SOURCE_SHA" \
  --payload-file "$ROOT/receipt.json" || true

exit "$STATUS"
