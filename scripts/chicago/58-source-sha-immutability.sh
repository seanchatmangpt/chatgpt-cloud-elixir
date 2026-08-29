#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,re,sys
x=[r["sha"] for r in json.load(open(sys.argv[1]))["sources"]]
assert len(x)==len(set(x))==7 and all(re.fullmatch("[0-9a-f]{40}",s) for s in x) and "0"*40 not in x
PY
