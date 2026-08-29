#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/versions.toml" "$CONSUMER_A/manufacturing/ggen.toml" <<'PY'
import os,sys,tomllib
v=tomllib.load(open(sys.argv[1],"rb")); g=tomllib.load(open(sys.argv[2],"rb")); assert v["release"]["version"]==g["project"]["version"]=="26.8.25"; assert v["bootstrap"]["ggen_sha"]==os.environ["GGEN_SHA"]
PY
