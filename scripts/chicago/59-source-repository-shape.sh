#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,re,sys
x=[r["repository"] for r in json.load(open(sys.argv[1]))["sources"]]
assert len(x)==len(set(x))==7 and all(re.fullmatch("seanchatmangpt/[a-z0-9-]+",s) for s in x)
assert all("://" not in s and not s.endswith(".git") for s in x)
PY
