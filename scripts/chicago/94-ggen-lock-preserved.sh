#!/usr/bin/env bash
set -euo pipefail
for p in Cargo.toml Cargo.lock rust-toolchain.toml; do test -s "$GGEN_DIR/$p"; test "$(git -C "$GGEN_DIR" hash-object "$p")" = "$(git -C "$GGEN_DIR" rev-parse "HEAD:$p")"; done
