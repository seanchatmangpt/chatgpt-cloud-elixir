#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,re,sys
v=json.load(open(sys.argv[1]))
r=[x for x in v["sources"] if x["name"]=="ggen-legacy"]; assert len(r)==1; r=r[0]
assert r["repository"]=="seanchatmangpt/ggen-legacy" and r["sha"]=="93d2ecd18147acaff659bf1d9cc2d4313628305b"
assert r["capital_class"]=="acquisition-runtime" and r["execution_mode"]=="source-snapshot"
assert r["required_standing"]=="exact-source-present" and len(r["role"].split())>=3
PY
