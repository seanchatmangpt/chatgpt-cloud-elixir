#!/usr/bin/env bash
set -euo pipefail
# prove a malformed manifest cannot manufacture generated products.
test "$MALFORMED_EXIT" -ne 0
test ! -e "$CHICAGO_ROOT/malformed/manufacturing/generated/capability-lock.json"
test ! -e "$CHICAGO_ROOT/malformed/manufacturing/generated/autonomic-manufacturing.mmd"
test -n "$(git -C "$CHICAGO_ROOT/malformed" status --porcelain -- manufacturing/ggen.toml)"
printf 'CHICAGO_PROBE ALIVE edge=40-malformed-no-crown\n'
