#!/usr/bin/env bash
# Canonical fetcher for the admitted capability-source closure. CI, docs, and local
# replays all use this one script, so fetch semantics cannot drift between them.
#
#   scripts/fetch-capability-sources.sh <capability-lock.json> <dest-root> [--exclude name ...]
#
# Every source is fetched shallowly at its exact admitted SHA and checked out detached,
# and its HEAD identity is asserted. Existing checkouts already at the admitted SHA are
# reused.
#
# Git LFS law (manufacturing/ontology.ttl cc:lfsObjectPolicy "pointer-identity"):
# LFS-tracked files are admitted by their pointer blob (sha256 oid + size), which the
# commit and tree SHA already bind. They are never downloaded. The closure therefore
# never depends on an LFS endpoint, quota, or credentials. (ggen-marketplace exceeded
# its LFS budget on 2026-09-24, which is why this is enforced here and not left to
# ambient git configuration.) build-autonomic-manufacturing.sh refuses to stage an LFS
# pointer into shipped content.
set -euo pipefail

LOCK="${1:?usage: fetch-capability-sources.sh <capability-lock.json> <dest-root> [--exclude name ...]}"
DEST="${2:?usage: fetch-capability-sources.sh <capability-lock.json> <dest-root> [--exclude name ...]}"
shift 2
EXCLUDE=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --exclude) EXCLUDE+=("${2:?--exclude needs a name}"); shift 2 ;;
    *) echo "UNSUPPORTED: unknown argument $1" >&2; exit 64 ;;
  esac
done

# Private sources (cc:accessClass "private") are fetched only with CAPABILITY_SOURCES_TOKEN
# (a read credential, passed per-command and never persisted into any .git/config).
# Without it they are recorded as BLOCKED[IRREDUCIBLE_AUTHORITY] in <dest>/.blocked-sources.tsv
# and the closure continues (a blocked edge is topology, not graph failure). A public
# source that fails to fetch is always fatal.
export GIT_LFS_SKIP_SMUDGE=1 GIT_TERMINAL_PROMPT=0
BASE_URL="${CAPABILITY_SOURCES_BASE_URL:-https://github.com}"
[[ -f "$LOCK" ]] || { echo "BLOCKED: capability lock not found: $LOCK" >&2; exit 66; }
mkdir -p "$DEST"

ROWS="$(python3 - "$LOCK" "${EXCLUDE[@]+"${EXCLUDE[@]}"}" <<'PY'
import json, re, sys
lock = json.load(open(sys.argv[1]))
excluded = set(sys.argv[2:])
for s in lock["sources"]:
    if s["name"] in excluded:
        continue
    if not re.fullmatch(r"[0-9a-f]{40}", s["sha"]) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", s["repository"]):
        raise SystemExit(f"REFUSED: malformed lock row for {s['name']}")
    access = s.get("access_class", "public")
    if access not in ("public", "private"):
        raise SystemExit(f"REFUSED: unknown access_class for {s['name']}")
    print(f"{s['name']}\t{s['repository']}\t{s['sha']}\t{access}")
PY
)"

BLOCKED_TSV="$DEST/.blocked-sources.tsv"
: > "$BLOCKED_TSV"
fetched=0 reused=0 blocked=0
while IFS=$'\t' read -r name repository sha access; do
  [[ -n "$name" ]] || continue
  dir="$DEST/$name"
  if [[ -d "$dir/.git" && "$(git -C "$dir" rev-parse HEAD 2>/dev/null)" == "$sha" ]]; then
    reused=$((reused + 1))
    continue
  fi
  auth=()
  if [[ "$access" == private ]]; then
    if [[ -z "${CAPABILITY_SOURCES_TOKEN:-}" ]]; then
      printf '%s\t%s\t%s\t%s\n' "$name" "$repository" "$sha" "BLOCKED[IRREDUCIBLE_AUTHORITY]: private source, no CAPABILITY_SOURCES_TOKEN" >> "$BLOCKED_TSV"
      rm -rf "$dir"
      blocked=$((blocked + 1))
      continue
    fi
    auth=(-c "http.extraHeader=AUTHORIZATION: basic $(printf 'x-access-token:%s' "$CAPABILITY_SOURCES_TOKEN" | base64 -w0)")
  fi
  rm -rf "$dir"
  mkdir -p "$dir"
  git -C "$dir" init -q
  git -C "$dir" remote add origin "$BASE_URL/$repository.git"
  git "${auth[@]}" -C "$dir" fetch -q --depth 1 origin "$sha"
  git -C "$dir" checkout -q --detach FETCH_HEAD
  [[ "$(git -C "$dir" rev-parse HEAD)" == "$sha" ]] || { echo "BUILD_BROKEN: $name expected $sha" >&2; exit 65; }
  fetched=$((fetched + 1))
done <<< "$ROWS"

echo "CAPABILITY_SOURCES=ALIVE fetched=$fetched reused=$reused blocked_private=$blocked lfs=pointer-identity dest=$DEST"
