#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,sys
x=[r["name"] for r in json.load(open(sys.argv[1]))["sources"]]
assert len(x)==len(set(x))==7
assert set(x)=={"ggen","ggen-marketplace","ggen-create","ggen-legacy","ggen-spec-kit","swarmsh","swarmsh-v2"}
PY
