#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/.ggen-v2/receipt.json" "$CONSUMER_B/manufacturing/.ggen-v2/receipt.json" <<'PY'
import json,sys
a,b=[json.load(open(p)) for p in sys.argv[1:]]; assert isinstance(a,dict) and isinstance(b,dict) and a and b and set(a)==set(b); assert all(isinstance(k,str) and k for k in a)
PY
