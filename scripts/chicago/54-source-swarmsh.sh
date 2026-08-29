#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,re,sys
v=json.load(open(sys.argv[1]))
r=[x for x in v["sources"] if x["name"]=="swarmsh"]; assert len(r)==1; r=r[0]
assert r["repository"]=="seanchatmangpt/swarmsh" and r["sha"]=="745008438b9493d31e8af3735ad6116ac01c150f"
assert r["capital_class"]=="execution-runtime" and r["execution_mode"]=="shell-source"
assert r["required_standing"]=="exact-source-shell-qualification" and len(r["role"].split())>=3
PY
