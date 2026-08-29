#!/usr/bin/env bash
set -euo pipefail
for c in "$CONSUMER_A" "$CONSUMER_B"; do p="$c/manufacturing/.ggen-v2/receipt.json"; test -s "$p"; python3 -m json.tool "$p" >/dev/null; done
