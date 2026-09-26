#!/usr/bin/env bash
set -euo pipefail
# parse the real manufacturing manifest through the production language boundary.
python3 - "$CONSUMER_A/manufacturing/ggen.toml" <<'PY'
import sys, tomllib
v=tomllib.load(open(sys.argv[1],"rb"))
assert set(("project","ontology","generation")) <= set(v)
assert isinstance(v["generation"]["rules"], list)
PY
printf 'CHICAGO_PROBE ALIVE edge=16-manifest-parser\n'
