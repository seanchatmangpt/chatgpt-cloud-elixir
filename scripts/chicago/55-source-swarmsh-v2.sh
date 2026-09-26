#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,re,sys
v=json.load(open(sys.argv[1]))
r=[x for x in v["sources"] if x["name"]=="swarmsh-v2"]; assert len(r)==1; r=r[0]
assert r["repository"]=="seanchatmangpt/swarmsh-v2" and r["sha"]=="02e5eaae14bd03a832c0f031acc56c6d4db3845e"
assert r["capital_class"]=="execution-kernel-source" and r["execution_mode"]=="typed-source"
assert r["required_standing"]=="source-bound-not-runtime-promoted" and len(r["role"].split())>=3
PY
