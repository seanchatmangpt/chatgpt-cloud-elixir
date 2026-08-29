#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1])); assert v["release"]=="26.8.25" and v["schema_version"]==1 and len(v["sources"])==7
PY
