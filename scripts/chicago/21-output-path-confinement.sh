#!/usr/bin/env bash
set -euo pipefail
# prove parsed generation outputs remain repository-relative.
python3 - "$CONSUMER_A/manufacturing/ggen.toml" <<'PY'
import pathlib,sys,tomllib
g=tomllib.load(open(sys.argv[1],"rb"))["generation"]
out=pathlib.PurePosixPath(g["output_dir"])
assert not out.is_absolute() and ".." not in out.parts
for r in g["rules"]:
 p=pathlib.PurePosixPath(r["output_file"])
 assert not p.is_absolute() and ".." not in p.parts and len(p.parts)==1
PY
printf 'CHICAGO_PROBE ALIVE edge=21-output-path-confinement\n'
