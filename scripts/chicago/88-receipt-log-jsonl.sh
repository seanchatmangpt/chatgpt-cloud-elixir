#!/usr/bin/env bash
set -euo pipefail
for c in "$CONSUMER_A" "$CONSUMER_B"; do python3 - "$c/manufacturing/.ggen-v2/receipt-log.jsonl" <<'PY'
import json,sys
x=[json.loads(s) for s in open(sys.argv[1]) if s.strip()]; assert x and all(isinstance(r,dict) and r for r in x)
PY
done
