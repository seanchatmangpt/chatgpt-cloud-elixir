#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/generated/capability-lock.json" <<'PY'
import json,sys
x=[r["execution_mode"] for r in json.load(open(sys.argv[1]))["sources"]]
assert len(x)==7 and all(isinstance(s,str) and s for s in x)
assert set(x)==set(["compiled-binary","source-snapshot","shell-source","typed-source"])
PY
