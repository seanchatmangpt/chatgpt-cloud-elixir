#!/usr/bin/env bash
set -euo pipefail
# prove production manufacture never edits tracked source in consumer one.
git -C "$CONSUMER_A" diff --exit-code -- . ':!manufacturing/generated' >/dev/null
git -C "$CONSUMER_A" diff --cached --exit-code >/dev/null
test -z "$(git -C "$CONSUMER_A" ls-files --modified)"
test "$(git -C "$CONSUMER_A" rev-parse HEAD)" = "$SUBJECT_SHA"
printf 'CHICAGO_PROBE ALIVE edge=33-first-consumer-tracked-clean\n'
