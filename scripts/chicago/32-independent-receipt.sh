#!/usr/bin/env bash
set -euo pipefail
# prove the second consumer owns independent execution evidence.
test "$RECEIPT_LINES_INDEPENDENT" -ge 1
test -s "$CONSUMER_B/manufacturing/.ggen-v2/receipt-log.jsonl"
test "$(wc -l <"$CONSUMER_B/manufacturing/.ggen-v2/receipt-log.jsonl")" -eq "$RECEIPT_LINES_INDEPENDENT"
test "$CONSUMER_A/manufacturing/.ggen-v2/receipt-log.jsonl" != "$CONSUMER_B/manufacturing/.ggen-v2/receipt-log.jsonl"
printf 'CHICAGO_PROBE ALIVE edge=32-independent-receipt\n'
