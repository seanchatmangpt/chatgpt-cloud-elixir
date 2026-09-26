#!/usr/bin/env bash
set -euo pipefail
# execute the real recursive submodule state probe.
git -C "$CONSUMER_A" submodule status --recursive >"$CHICAGO_ROOT/submodules-a.txt"
git -C "$CONSUMER_B" submodule status --recursive >"$CHICAGO_ROOT/submodules-b.txt"
! grep -Eq '^[+-]' "$CHICAGO_ROOT/submodules-a.txt"
cmp "$CHICAGO_ROOT/submodules-a.txt" "$CHICAGO_ROOT/submodules-b.txt"
printf 'CHICAGO_PROBE ALIVE edge=06-submodule-state\n'
