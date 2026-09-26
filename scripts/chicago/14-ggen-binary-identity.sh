#!/usr/bin/env bash
set -euo pipefail
# bind repeated binary observations to one cryptographic identity.
h1="$(sha256sum "$GGEN_BIN" | awk '{print $1}')"
h2="$(sha256sum "$GGEN_BIN" | awk '{print $1}')"
test "$h1" = "$h2"
[[ "$h1" =~ ^[0-9a-f]{64}$ ]]
printf '%s\n' "$h1" >"$CHICAGO_ROOT/ggen-binary.sha256"
printf 'CHICAGO_PROBE ALIVE edge=14-ggen-binary-identity\n'
