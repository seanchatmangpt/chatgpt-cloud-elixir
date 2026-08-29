#!/usr/bin/env bash
set -euo pipefail
# execute Cargo locked metadata over the exact constructor.
test -s "$GGEN_DIR/Cargo.lock"
cargo +"$RUST_TOOLCHAIN" metadata --locked --no-deps --format-version 1 --manifest-path "$GGEN_DIR/Cargo.toml" >"$CHICAGO_ROOT/ggen-metadata.json"
python3 -m json.tool "$CHICAGO_ROOT/ggen-metadata.json" >/dev/null
grep -q '"packages"' "$CHICAGO_ROOT/ggen-metadata.json"
printf 'CHICAGO_PROBE ALIVE edge=11-ggen-locked-metadata\n'
