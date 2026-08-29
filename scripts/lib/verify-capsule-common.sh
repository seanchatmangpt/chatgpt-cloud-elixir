#!/usr/bin/env bash
# shellcheck shell=bash
#
# Shared boilerplate sourced by both capsule verify entry points:
#   - scripts/verify-capsule.sh (beam-core / ash-* capsules: plain mix compile+test)
#   - capsules/process-intelligence/verify-capsule.sh (subject-acceptance loop +
#     process-lab harness)
#
# Both entry points must keep their exact current external behavior (same
# stdout, same receipt.json shape, same exit codes) -- this file holds only
# the parts that were byte-for-byte identical between them (see
# docs/errc-tracker.md's "share ~70% logic" REDUCE item). Anything that
# differs between the two capsules (NETWORK_MODE default, capsule_name
# source, release_version extraction, whether emit-ocel-capsule-event.sh is
# invoked, receipt field set) intentionally stays in each entry script, not
# here.
#
# Contract: the caller must set ROOT before sourcing this file (both entry
# scripts compute it as `$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)`
# *before* sourcing -- computing it in here instead would resolve against
# this file's own directory, scripts/lib, not the entry script's).

# shellcheck disable=SC1091
source "$ROOT/activate"
LOG="$ROOT/verification.log"
ARCHIVE_DIGEST="${CAPSULE_ARCHIVE_DIGEST:-external-not-supplied}"

# Runs the two elixir manifest/runtime verifier scripts against
# $ROOT/manifest.json. Identical first two acceptance steps in both entry
# scripts' fenced/logged bodies.
capsule_verify_manifest_and_runtime() {
  elixir "$ROOT/verifier/verify_manifest.exs" "$ROOT/manifest.json"
  elixir "$ROOT/verifier/verify_runtime.exs" "$ROOT/manifest.json"
}

# Runs the function named by $1 inside a `set -e` subshell, tees its
# combined stdout/stderr to $LOG, and leaves the subshell's real exit code
# in the global STATUS variable -- equivalent to both scripts' previous
# inline `set +e; ( set -e; ... ) 2>&1 | tee "$LOG"; STATUS=${PIPESTATUS[0]};
# set -e` wrapper.
capsule_run_logged() {
  local body_fn="$1"
  set +e
  ( set -e; "$body_fn" ) 2>&1 | tee "$LOG"
  STATUS=${PIPESTATUS[0]}
  set -e
}

# Echoes ALIVE/BUILD_BROKEN for a given acceptance exit code.
capsule_standing_from_status() {
  if [[ "$1" -eq 0 ]]; then
    echo "ALIVE"
  else
    echo "BUILD_BROKEN"
  fi
}

# Echoes the sha256 of $ROOT/manifest.json.
capsule_manifest_sha() {
  sha256sum "$ROOT/manifest.json" | awk '{print $1}'
}

# Echoes the source_sha field embedded in $ROOT/manifest.json.
capsule_source_sha() {
  sed -n 's/.*"source_sha": "\([^"]*\)".*/\1/p' "$ROOT/manifest.json" | head -1
}

# Echoes the current UTC timestamp in the receipt's verified_at format.
capsule_verified_at() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}
