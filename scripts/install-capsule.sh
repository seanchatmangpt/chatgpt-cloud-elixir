#!/usr/bin/env bash
set -euo pipefail

ARCHIVE="${1:?usage: scripts/install-capsule.sh <archive.tar.gz> [destination]}"
DEST="${2:-./chatgpt-cloud-elixir-capsule}"
[[ -f "$ARCHIVE" ]] || { echo "BLOCKED: archive not found: $ARCHIVE" >&2; exit 66; }

SIDECAR="$ARCHIVE.sha256"
if [[ -f "$SIDECAR" ]]; then
  expected="$(awk '{print $1}' "$SIDECAR")"
  actual="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
  [[ "$expected" == "$actual" ]] || { echo "BUILD_BROKEN: archive checksum mismatch" >&2; exit 65; }
fi

mkdir -p "$DEST"
tar -xzf "$ARCHIVE" -C "$DEST"
printf 'installed=%s\n' "$(cd "$DEST" && pwd)"
printf 'activate=source %s/activate\n' "$(cd "$DEST" && pwd)"
