#!/usr/bin/env bash
set -euo pipefail
# prove replay appends evidence instead of overwriting history.
test "$RECEIPT_LINES_FIRST" -ge 1
test "$RECEIPT_LINES_REPLAY" -gt "$RECEIPT_LINES_FIRST"
test "$(wc -l <"$CONSUMER_A/manufacturing/.ggen-v2/receipt-log.jsonl")" -eq "$RECEIPT_LINES_REPLAY"
tail -n 1 "$CONSUMER_A/manufacturing/.ggen-v2/receipt-log.jsonl" | python3 -m json.tool >/dev/null
printf 'CHICAGO_PROBE ALIVE edge=31-receipt-growth\n'
