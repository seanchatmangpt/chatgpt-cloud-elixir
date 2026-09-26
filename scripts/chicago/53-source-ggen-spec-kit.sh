#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,re,sys
v=json.load(open(sys.argv[1]))
r=[x for x in v["sources"] if x["name"]=="ggen-spec-kit"]; assert len(r)==1; r=r[0]
assert r["repository"]=="seanchatmangpt/ggen-spec-kit" and r["sha"]=="10d75676a4a12034bd9c650633a86962907d5eeb"
assert r["capital_class"]=="semantic-intake" and r["execution_mode"]=="source-snapshot"
assert r["required_standing"]=="exact-source-present" and len(r["role"].split())>=3
PY
