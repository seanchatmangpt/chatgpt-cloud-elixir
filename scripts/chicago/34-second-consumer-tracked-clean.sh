#!/usr/bin/env bash
set -euo pipefail
# prove production manufacture never edits tracked source in consumer two.
git -C "$CONSUMER_B" diff --exit-code -- . ':!manufacturing/generated' >/dev/null
git -C "$CONSUMER_B" diff --cached --exit-code >/dev/null
test -z "$(git -C "$CONSUMER_B" ls-files --modified)"
test "$(git -C "$CONSUMER_B" rev-parse HEAD)" = "$SUBJECT_SHA"
printf 'CHICAGO_PROBE ALIVE edge=34-second-consumer-tracked-clean\n'
