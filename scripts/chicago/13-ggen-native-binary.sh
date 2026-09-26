#!/usr/bin/env bash
set -euo pipefail
# prove the real constructor binary is native and executable.
test -x "$GGEN_BIN"
test -s "$GGEN_BIN"
file "$GGEN_BIN" | grep -Eq 'ELF|executable'
"$GGEN_BIN" --help >"$CHICAGO_ROOT/ggen-help.txt"
test -s "$CHICAGO_ROOT/ggen-help.txt"
printf 'CHICAGO_PROBE ALIVE edge=13-ggen-native-binary\n'
