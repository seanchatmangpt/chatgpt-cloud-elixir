#!/usr/bin/env bash
# Network-fenced entry point for scripts/verify-postgres-capsule.sh, mirroring
# scripts/run-offline.sh's contract for the beam-core/ash capsule family. Closes a
# RAISE item in docs/errc-tracker.md's Resolved section: calling
# verify-postgres-capsule.sh directly enforced no network fencing of its own --
# this wrapper does, the same way run-offline.sh does for verify-capsule.sh, so
# "offline law" is uniformly enforced across every capsule family rather than only
# the Elixir ones. (Calling verify-capsule.sh/verify-postgres-capsule.sh directly
# still bypasses fencing -- that half stays open, see docs/errc-tracker.md.)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v unshare >/dev/null 2>&1 && unshare -n true >/dev/null 2>&1; then
  exec unshare -n env \
    CAPSULE_NETWORK_MODE=namespace_offline \
    bash "$ROOT/scripts/verify-postgres-capsule.sh"
fi

export CAPSULE_NETWORK_MODE=proxy_fenced_offline
export HTTP_PROXY=http://127.0.0.1:9
export HTTPS_PROXY=http://127.0.0.1:9
export ALL_PROXY=http://127.0.0.1:9
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export all_proxy="$ALL_PROXY"
exec bash "$ROOT/scripts/verify-postgres-capsule.sh"
