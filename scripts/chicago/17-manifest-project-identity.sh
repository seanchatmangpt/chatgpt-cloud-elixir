#!/usr/bin/env bash
set -euo pipefail
# prove the consumer manifest retains its release identity.
python3 - "$CONSUMER_A/manufacturing/ggen.toml" <<'PY'
import sys,tomllib
v=tomllib.load(open(sys.argv[1],"rb"))
p=v["project"]
assert p["name"]=="chatgpt-cloud-autonomic-manufacturing"
assert p["version"]=="26.8.25"
assert p["description"].strip()
PY
printf 'CHICAGO_PROBE ALIVE edge=17-manifest-project-identity\n'
