#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/ggen.toml" "$CONSUMER_A/manufacturing" <<'PY'
import pathlib,sys,tomllib
v=tomllib.load(open(sys.argv[1],"rb")); r=pathlib.Path(sys.argv[2]); x=[q["query"]["file"] for q in v["generation"]["rules"]]
assert x==["queries/sources.rq"]*2 and "ORDER BY ?name" in (r/x[0]).read_text()
PY
