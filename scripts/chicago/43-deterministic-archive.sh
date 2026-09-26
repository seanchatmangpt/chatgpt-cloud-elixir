#!/usr/bin/env bash
set -euo pipefail
# manufacture two deterministic archives from real generated products.
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$CONSUMER_A/manufacturing" -cf "$CHICAGO_ROOT/products-a.tar" generated
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -C "$CONSUMER_A/manufacturing" -cf "$CHICAGO_ROOT/products-b.tar" generated
cmp "$CHICAGO_ROOT/products-a.tar" "$CHICAGO_ROOT/products-b.tar"
sha256sum "$CHICAGO_ROOT/products-a.tar" >"$CHICAGO_ROOT/products.tar.sha256"
printf 'CHICAGO_PROBE ALIVE edge=43-deterministic-archive\n'
