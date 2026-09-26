#!/usr/bin/env bash
set -euo pipefail
# bind the executing host to the consumer platform admission.
python3 - "$CONSUMER_A/versions.toml" "$(uname -s)" "$(uname -m)" <<'PY'
import sys,tomllib
v=tomllib.load(open(sys.argv[1],"rb"))
assert sys.argv[2]=="Linux"
assert sys.argv[3]=="x86_64"
p=v["platforms"]["linux_x86_64"]
assert p=={"os":"linux","arch":"x86_64","status":"admitted"}
PY
printf 'CHICAGO_PROBE ALIVE edge=46-runtime-platform-admission\n'
