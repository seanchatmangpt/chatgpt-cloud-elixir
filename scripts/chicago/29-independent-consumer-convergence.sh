#!/usr/bin/env bash
set -euo pipefail
# prove a second anonymous consumer manufactures the same consequence.
test "$DIGEST_INDEPENDENT" = "$DIGEST_FIRST"
[[ "$DIGEST_INDEPENDENT" =~ ^[0-9a-f]{64}$ ]]
test "$CONSUMER_A" != "$CONSUMER_B"
test "$(git -C "$CONSUMER_B" rev-parse HEAD)" = "$SUBJECT_SHA"
printf 'CHICAGO_PROBE ALIVE edge=29-independent-consumer-convergence\n'
