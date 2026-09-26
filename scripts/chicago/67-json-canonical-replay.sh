#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" "$CONSUMER_B/manufacturing/generated/capability-lock.json" <<'PY'
import json,sys,hashlib
x=[json.dumps(json.load(open(p)),sort_keys=True,separators=(",",":")).encode() for p in sys.argv[1:]]
assert x[0]==x[1] and len(x[0])>100 and hashlib.sha256(x[0]).digest()==hashlib.sha256(x[1]).digest()
PY
