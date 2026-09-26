#!/usr/bin/env bash
set -euo pipefail
# parse every real GGen receipt through the standard JSON parser.
python3 - "$CONSUMER_A/manufacturing/.ggen-v2/receipt-log.jsonl" <<'PY'
import json,sys
lines=[x for x in open(sys.argv[1]) if x.strip()]
assert len(lines)>=2
values=[json.loads(x) for x in lines]
assert all(isinstance(x,dict) and x for x in values)
assert len(values)==len(lines)
PY
printf 'CHICAGO_PROBE ALIVE edge=30-receipt-jsonl-parser\n'
