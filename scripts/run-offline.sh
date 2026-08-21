#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v unshare >/dev/null 2>&1 && unshare -n true >/dev/null 2>&1; then
  exec unshare -n env \
    CAPSULE_NETWORK_MODE=namespace_offline \
    HEX_OFFLINE=1 \
    bash "$ROOT/scripts/verify-capsule.sh"
fi

export CAPSULE_NETWORK_MODE=proxy_fenced_hex_offline
export HEX_OFFLINE=1
export HTTP_PROXY=http://127.0.0.1:9
export HTTPS_PROXY=http://127.0.0.1:9
export ALL_PROXY=http://127.0.0.1:9
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export all_proxy="$ALL_PROXY"
exec bash "$ROOT/scripts/verify-capsule.sh"
