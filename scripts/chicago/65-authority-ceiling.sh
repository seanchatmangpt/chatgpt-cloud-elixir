#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1])); assert v["authority_ceiling"]=="CONSTRUCT_VERIFY" and "DO" not in v["authority_ceiling"] and v["sources"]
PY
