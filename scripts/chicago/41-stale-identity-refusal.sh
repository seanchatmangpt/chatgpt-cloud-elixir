#!/usr/bin/env bash
set -euo pipefail
# preserve real Git transport refusal for a nonexistent immutable constructor.
test "$STALE_EXIT" -ne 0
test -s "$CHICAGO_ROOT/stale.out"
grep -qiE 'not our ref|unadvertised|could not|fatal|remote error' "$CHICAGO_ROOT/stale.out"
test -d "$CHICAGO_ROOT/stale-ggen/.git"
printf 'CHICAGO_PROBE ALIVE edge=41-stale-identity-refusal\n'
