#!/usr/bin/env bash
set -euo pipefail
python3 - "$CONSUMER_A/manufacturing/ggen.toml" "$CONSUMER_A/manufacturing" <<'PY'
import pathlib,sys,tomllib
v=tomllib.load(open(sys.argv[1],"rb")); r=pathlib.Path(sys.argv[2]); x=v["generation"]["rules"]; assert len(x)==2
for q in x: p=r/q["template"]["file"]; assert p.is_file() and p.stat().st_size and p.suffix==".tera"
PY
