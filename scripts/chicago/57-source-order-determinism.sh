#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,sys
x=[r["name"] for r in json.load(open(sys.argv[1]))["sources"]]
assert x==sorted(x) and x[0]=="ggen" and x[-1]=="swarmsh-v2"
PY
