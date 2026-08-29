#!/usr/bin/env bash
set -euo pipefail
# prove constructor lock and manifest identities are stable during manufacture.
before_lock="$(git -C "$GGEN_DIR" hash-object Cargo.lock)"
before_manifest="$(git -C "$GGEN_DIR" hash-object Cargo.toml)"
test "$before_lock" = "$(git -C "$GGEN_DIR" rev-parse HEAD:Cargo.lock)"
test "$before_manifest" = "$(git -C "$GGEN_DIR" rev-parse HEAD:Cargo.toml)"
git -C "$GGEN_DIR" diff --quiet -- Cargo.lock Cargo.toml
printf 'CHICAGO_PROBE ALIVE edge=12-ggen-lock-integrity\n'
