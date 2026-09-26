#!/usr/bin/env bash
set -euo pipefail
# prove every declared query is a real nonempty consumer input.
python3 - "$CONSUMER_A/manufacturing/ggen.toml" "$CONSUMER_A/manufacturing" <<'PY'
import pathlib,sys,tomllib
v=tomllib.load(open(sys.argv[1],"rb")); root=pathlib.Path(sys.argv[2])
for r in v["generation"]["rules"]:
 p=root/r["query"]["file"]
 assert p.is_file() and p.stat().st_size>0
 assert "SELECT" in p.read_text().upper()
PY
printf 'CHICAGO_PROBE ALIVE edge=22-query-materialization\n'
