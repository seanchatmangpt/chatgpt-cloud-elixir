#!/usr/bin/env bash
set -euo pipefail
for c in "$CONSUMER_A" "$CONSUMER_B"; do test "$(find "$c/manufacturing/.ggen-v2" -maxdepth 1 -type f | wc -l)" -eq 2; test -s "$c/manufacturing/.ggen-v2/receipt.json"; test -s "$c/manufacturing/.ggen-v2/receipt-log.jsonl"; done
