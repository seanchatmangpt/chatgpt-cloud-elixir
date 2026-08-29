#!/usr/bin/env bash
set -euo pipefail
# prove both anonymous consumers are the exact admitted subject.
test "$(git -C "$CONSUMER_A" rev-parse HEAD)" = "$SUBJECT_SHA"
test "$(git -C "$CONSUMER_B" rev-parse HEAD)" = "$SUBJECT_SHA"
test "$(git -C "$CONSUMER_A" rev-parse --show-toplevel)" = "$CONSUMER_A"
test "$(git -C "$CONSUMER_B" rev-parse --show-toplevel)" = "$CONSUMER_B"
printf 'CHICAGO_PROBE ALIVE edge=01-subject-exact-checkout\n'
