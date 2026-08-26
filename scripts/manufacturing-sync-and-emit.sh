#!/usr/bin/env bash
# Runs the real `ggen sync run` projection over manufacturing/ and, on success,
# emits one OCEL event to control-plane's ingest API carrying the projected
# capability-lock identity (release, source set, graph_hash_hex).
#
# This closes the gap named by the innovation-explorer cross-repo-integration
# sweep: ggen sync run already produces structured, admitted-capability-fact
# output, but manufacturing/ had no code path making a capability-closure
# change visible on the live LiveView feed / project-memory without grepping
# generated/ by hand.
#
# Like scripts/emit-ocel-capsule-event.sh, this is observability only: a
# failed/skipped emission never changes this script's exit status relative to
# what `ggen sync run` itself reported. manufacturing/'s own CONSTRUCT_VERIFY
# authority boundary (see manufacturing/README.md) is unaffected -- this adds
# no DO authority, only an observed OCEL fact about a completed sync.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANUFACTURING_DIR="$ROOT/manufacturing"
EMITTER="$ROOT/scripts/emit-ocel-capsule-event.sh"

cd "$MANUFACTURING_DIR"
SYNC_LOG="$(mktemp)"
trap 'rm -f "$SYNC_LOG"' EXIT

set +e
ggen sync run > "$SYNC_LOG" 2>&1
STATUS=$?
set -e

cat "$SYNC_LOG"

if [[ "$STATUS" -ne 0 ]]; then
  echo "manufacturing-sync-and-emit: ggen sync run failed (exit $STATUS); not emitting" >&2
  exit "$STATUS"
fi

# ggen sync run's own stdout is one multi-line JSON summary object framed by
# tracing INFO lines (not valid JSON) before and after it. Extract the block
# between the first "{" line and its matching top-level "}" by brace counting.
SYNC_JSON="$(python3 - "$SYNC_LOG" <<'PY'
import json, sys
lines = open(sys.argv[1]).read().splitlines()
start = None
for i, line in enumerate(lines):
    if line.strip().startswith("{"):
        start = i
        break
if start is not None:
    depth = 0
    end = None
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth == 0:
            end = i
            break
    if end is not None:
        block = "\n".join(lines[start:end + 1])
        try:
            json.loads(block)
            print(block)
        except json.JSONDecodeError:
            pass
PY
)"

if [[ -z "$SYNC_JSON" ]]; then
  echo "manufacturing-sync-and-emit: could not locate sync summary JSON; not emitting" >&2
  exit 0
fi

GRAPH_HASH="$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('graph_hash_hex',''))" "$SYNC_JSON")"
LOCK_FILE="$MANUFACTURING_DIR/generated/capability-lock.json"
RELEASE=""
SOURCES_JSON="[]"
if [[ -f "$LOCK_FILE" ]]; then
  RELEASE="$(python3 -c "import json; print(json.load(open('$LOCK_FILE')).get('release',''))" 2>/dev/null || echo "")"
  SOURCES_JSON="$(python3 -c "
import json
lock = json.load(open('$LOCK_FILE'))
sources = lock.get('sources', [])
if isinstance(sources, dict):
    print(json.dumps(sorted(sources.keys())))
else:
    print(json.dumps(sorted(s.get('name') for s in sources)))
" 2>/dev/null || echo "[]")"
fi

OCCURRED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
PAYLOAD_FILE="$(mktemp)"
SYNC_JSON_FILE="$(mktemp)"
SOURCES_JSON_FILE="$(mktemp)"
trap 'rm -f "$SYNC_LOG" "$PAYLOAD_FILE" "$SYNC_JSON_FILE" "$SOURCES_JSON_FILE"' EXIT
printf '%s' "$SYNC_JSON" > "$SYNC_JSON_FILE"
printf '%s' "$SOURCES_JSON" > "$SOURCES_JSON_FILE"

# Build the payload by reading each fragment from a file, never by
# interpolating raw JSON text into Python source -- interpolating untrusted
# multi-line JSON (quotes, braces) directly into a shell-quoted `python -c`
# string is unsafe/fragile the same way an inline `git commit -m` with
# backticks/quotes is; always go through json.load on a real file instead.
python3 - "$SYNC_JSON_FILE" "$SOURCES_JSON_FILE" "$GRAPH_HASH" "$RELEASE" <<'PY' > "$PAYLOAD_FILE"
import json, sys
sync_json_file, sources_json_file, graph_hash, release = sys.argv[1:5]
sync_summary = json.load(open(sync_json_file))
sources = json.load(open(sources_json_file))
print(json.dumps({
    "graph_hash_hex": graph_hash,
    "release": release,
    "sources": sources,
    "sync_summary": sync_summary,
}))
PY

"$EMITTER" \
  --agent-id "manufacturing-sync:autonomic-manufacturing" \
  --run-id "manufacturing-sync:${GRAPH_HASH:-unknown}" \
  --activity "manufacturing.ggen_sync" \
  --standing "ALIVE" \
  --occurred-at "$OCCURRED_AT" \
  --subject-repo "seanchatmangpt/ggen-marketplace" \
  --payload-file "$PAYLOAD_FILE" || true

exit 0
