#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,re,sys
v=json.load(open(sys.argv[1]))
r=[x for x in v["sources"] if x["name"]=="ggen-marketplace"]; assert len(r)==1; r=r[0]
assert r["repository"]=="seanchatmangpt/ggen-marketplace" and r["sha"]=="5710efa0fec47242f5709790803f0129f3b29999"
assert r["capital_class"]=="manufacturing-capital" and r["execution_mode"]=="source-snapshot"
assert r["required_standing"]=="exact-source-present" and len(r["role"].split())>=3
PY
