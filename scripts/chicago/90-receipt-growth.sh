#!/usr/bin/env bash
set -euo pipefail
test "$RECEIPT_LINES_FIRST" -ge 1; test "$RECEIPT_LINES_REPLAY" -gt "$RECEIPT_LINES_FIRST"; test "$RECEIPT_LINES_INDEPENDENT" -ge 1; test "$(wc -l <"$CONSUMER_A/manufacturing/.ggen-v2/receipt-log.jsonl")" -eq "$RECEIPT_LINES_REPLAY"
