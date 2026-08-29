#!/usr/bin/env bash
set -euo pipefail
# prove rejected identity transport cannot yield an executable checkout.
test "$STALE_EXIT" -ne 0
! git -C "$CHICAGO_ROOT/stale-ggen" rev-parse --verify HEAD >/dev/null 2>&1
test -z "$(git -C "$CHICAGO_ROOT/stale-ggen" branch --show-current)"
test ! -e "$CHICAGO_ROOT/stale-ggen/target/release/ggen"
printf 'CHICAGO_PROBE ALIVE edge=42-stale-no-checkout\n'
