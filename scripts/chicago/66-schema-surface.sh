#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1])); assert set(v)=={"schema_version","release","authority_ceiling","sources"}
assert isinstance(v["schema_version"],int) and isinstance(v["sources"],list)
PY
