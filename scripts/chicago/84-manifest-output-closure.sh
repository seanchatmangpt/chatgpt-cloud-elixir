#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/ggen.toml" "$CONSUMER_A/manufacturing/generated" <<'PY'
import pathlib,sys,tomllib
v=tomllib.load(open(sys.argv[1],"rb")); r=pathlib.Path(sys.argv[2]); x=[q["output_file"] for q in v["generation"]["rules"]]
assert x==["capability-lock.json","autonomic-manufacturing.mmd"] and all((r/p).is_file() and (r/p).stat().st_size for p in x)
PY
