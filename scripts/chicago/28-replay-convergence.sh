#!/usr/bin/env bash
set -euo pipefail
# prove the second full execution converges on the first consequence.
test "$DIGEST_REPLAY" = "$DIGEST_FIRST"
[[ "$DIGEST_REPLAY" =~ ^[0-9a-f]{64}$ ]]
test -s "$CONSUMER_A/manufacturing/.ggen-v2/receipt-log.jsonl"
test "$RECEIPT_LINES_REPLAY" -ge "$RECEIPT_LINES_FIRST"
printf 'CHICAGO_PROBE ALIVE edge=28-replay-convergence\n'
