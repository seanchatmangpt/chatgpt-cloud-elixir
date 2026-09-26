#!/usr/bin/env bash
set -euo pipefail
# prove repository release and manufacturing identities agree.
python3 - "$CONSUMER_A/versions.toml" "$CONSUMER_A/manufacturing/ggen.toml" <<'PY'
import sys,tomllib
v=tomllib.load(open(sys.argv[1],"rb"))
g=tomllib.load(open(sys.argv[2],"rb"))
assert v["release"]["version"]==g["project"]["version"]
assert v["bootstrap"]["ggen_sha"]==__import__("os").environ["GGEN_SHA"]
assert v["bootstrap"]["ggen_repository"]==__import__("os").environ["GGEN_REPOSITORY"]
PY
printf 'CHICAGO_PROBE ALIVE edge=47-release-manifest-coherence\n'
