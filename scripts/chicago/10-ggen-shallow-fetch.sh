#!/usr/bin/env bash
set -euo pipefail
# prove constructor acquisition is bounded to the immutable subject.
test "$(git -C "$GGEN_DIR" rev-parse --is-shallow-repository)" = true
test "$(git -C "$GGEN_DIR" rev-list --count HEAD)" -eq 1
test -f "$GGEN_DIR/.git/shallow"
grep -q "$GGEN_SHA" "$GGEN_DIR/.git/shallow"
printf 'CHICAGO_PROBE ALIVE edge=10-ggen-shallow-fetch\n'
