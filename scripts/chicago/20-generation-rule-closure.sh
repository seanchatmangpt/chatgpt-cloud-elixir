#!/usr/bin/env bash
set -euo pipefail
# prove both admitted production rules are present and uniquely named.
python3 - "$CONSUMER_A/manufacturing/ggen.toml" <<'PY'
import sys,tomllib
rules=tomllib.load(open(sys.argv[1],"rb"))["generation"]["rules"]
names=[r["name"] for r in rules]
assert names==["capability-lock","manufacturing-topology"]
assert len(names)==len(set(names))
assert all(r["mode"]=="Overwrite" for r in rules)
PY
printf 'CHICAGO_PROBE ALIVE edge=20-generation-rule-closure\n'
