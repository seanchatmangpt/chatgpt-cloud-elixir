#!/usr/bin/env bash
set -euo pipefail
# execute structural inspection against the real generated capability lock.
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))
assert isinstance(v,(dict,list))
assert len(v)>0
text=json.dumps(v,sort_keys=True,separators=(",",":"))
assert len(text)>2
PY
printf 'CHICAGO_PROBE ALIVE edge=24-generated-json-product\n'
