#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,re,sys
v=json.load(open(sys.argv[1]))
r=[x for x in v["sources"] if x["name"]=="ggen-create"]; assert len(r)==1; r=r[0]
assert r["repository"]=="seanchatmangpt/ggen-create" and r["sha"]=="eaa463af138d7aff88db813f0f65307bf5c9b5ba"
assert r["capital_class"]=="capitalization-runtime" and r["execution_mode"]=="source-snapshot"
assert r["required_standing"]=="exact-source-present" and len(r["role"].split())>=3
PY
