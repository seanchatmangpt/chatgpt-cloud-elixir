#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/ontology.ttl" <<'PY'
import re,sys
x=re.findall(r'cc:commitSha "([0-9a-f]+)"',open(sys.argv[1]).read()); assert len(x)==len(set(x))==7 and all(len(s)==40 for s in x)
PY
