#!/usr/bin/env bash
set -euo pipefail
# preserve real parser refusal output for malformed production input.
test "$MALFORMED_EXIT" -ne 0
test -s "$CHICAGO_ROOT/malformed.out"
grep -qiE 'error|invalid|parse|toml|failed' "$CHICAGO_ROOT/malformed.out"
test "$(git -C "$CHICAGO_ROOT/malformed" rev-parse HEAD)" = "$SUBJECT_SHA"
printf 'CHICAGO_PROBE ALIVE edge=39-malformed-parser-refusal\n'
