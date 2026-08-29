#!/usr/bin/env bash
set -euo pipefail
# prove clean stranger clones honor the shallow transport boundary.
test "$(git -C "$CONSUMER_A" rev-parse --is-shallow-repository)" = true
test "$(git -C "$CONSUMER_B" rev-parse --is-shallow-repository)" = true
test "$(git -C "$CONSUMER_A" rev-list --count HEAD)" -eq 1
test "$(git -C "$CONSUMER_B" rev-list --count HEAD)" -eq 1
printf 'CHICAGO_PROBE ALIVE edge=03-subject-shallow-boundary\n'
