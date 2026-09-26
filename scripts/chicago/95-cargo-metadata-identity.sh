#!/usr/bin/env bash
set -euo pipefail
python3 - "$CHICAGO_ROOT/ggen-metadata.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))["packages"]; p=next(r for r in x if r["name"]=="ggen-cli-lib"); assert p["version"]=="26.8.21" and p["manifest_path"].endswith("/crates/ggen-cli/Cargo.toml")
PY
