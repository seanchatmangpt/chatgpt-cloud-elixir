#!/usr/bin/env bash
# Best-effort OCEL event emission for capsule build/verify scripts.
#
# Posts one `chatgpt-cloud-ocel/1` envelope (one event) to control-plane's
# `/api/v1/ocel/batches` ingest API so capsule build/verify history becomes
# visible on the live LiveView feed (/process-intelligence/live) instead of
# only existing as a scattered local receipt.json.
#
# This is observability only, never the crown: a failed/unreachable/unauthenticated
# emission must never change the calling script's exit status. CI/local capsule
# verification remains authoritative on its own acceptance command's exit code,
# per this repo's "CI is construction and transport, never the proof" contract.
#
# Usage:
#   OCEL_INGEST_TOKEN=... scripts/emit-ocel-capsule-event.sh \
#     --agent-id capsule-verify:<capsule_name> \
#     --run-id <run_key> \
#     --activity capsule.verify \
#     --standing ALIVE|BUILD_BROKEN|... \
#     --occurred-at <ISO8601> \
#     --subject-repo <repo-or-empty> \
#     --subject-sha <sha-or-empty> \
#     --payload-file <path-to-json-object>
#
# Env:
#   OCEL_INGEST_URL   base URL of control-plane (default: production Fly host)
#   OCEL_INGEST_TOKEN bearer token; emission is skipped entirely if unset
set -euo pipefail

OCEL_INGEST_URL="${OCEL_INGEST_URL:-https://chatgpt-cloud-process-intelligence.fly.dev}"

AGENT_ID=""
RUN_ID=""
ACTIVITY=""
STANDING="UNKNOWN"
OCCURRED_AT=""
SUBJECT_REPO=""
SUBJECT_SHA=""
PAYLOAD_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent-id) AGENT_ID="$2"; shift 2 ;;
    --run-id) RUN_ID="$2"; shift 2 ;;
    --activity) ACTIVITY="$2"; shift 2 ;;
    --standing) STANDING="$2"; shift 2 ;;
    --occurred-at) OCCURRED_AT="$2"; shift 2 ;;
    --subject-repo) SUBJECT_REPO="$2"; shift 2 ;;
    --subject-sha) SUBJECT_SHA="$2"; shift 2 ;;
    --payload-file) PAYLOAD_FILE="$2"; shift 2 ;;
    *) echo "emit-ocel-capsule-event: unknown argument '$1'" >&2; exit 64 ;;
  esac
done

if [[ -z "$AGENT_ID" || -z "$RUN_ID" || -z "$ACTIVITY" || -z "$OCCURRED_AT" ]]; then
  echo "emit-ocel-capsule-event: SKIPPED (missing required --agent-id/--run-id/--activity/--occurred-at)" >&2
  exit 0
fi

if [[ -z "${OCEL_INGEST_TOKEN:-}" ]]; then
  echo "emit-ocel-capsule-event: SKIPPED (OCEL_INGEST_TOKEN not set; not emitting to $OCEL_INGEST_URL)" >&2
  exit 0
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  echo "emit-ocel-capsule-event: SKIPPED (curl/python3 not available)" >&2
  exit 0
fi

PAYLOAD_JSON="{}"
if [[ -n "$PAYLOAD_FILE" && -f "$PAYLOAD_FILE" ]]; then
  PAYLOAD_JSON="$(cat "$PAYLOAD_FILE")"
fi

ENVELOPE="$(python3 - "$AGENT_ID" "$RUN_ID" "$ACTIVITY" "$STANDING" "$OCCURRED_AT" \
  "$SUBJECT_REPO" "$SUBJECT_SHA" <<'PY'
import json, sys
agent_id, run_id, activity, standing, occurred_at, subject_repo, subject_sha = sys.argv[1:8]
payload = json.loads(sys.stdin.read() or "{}") if not sys.stdin.isatty() else {}
envelope = {
    "schema": "chatgpt-cloud-ocel/1",
    "producer": {
        "agent_id": agent_id,
        "run_id": run_id,
        "status": "completed",
        "subject_repo": subject_repo or None,
        "subject_sha": subject_sha or None,
        "started_at": occurred_at,
        "ended_at": occurred_at,
        "metadata": {},
    },
    "events": [
        {
            "id": run_id,
            "activity": activity,
            "sequence": 1,
            "timestamp": occurred_at,
            "standing": standing,
            "lifecycle": "complete",
            "authority_domain": "CONSTRUCT_VERIFY",
            "payload": payload,
        }
    ],
}
print(json.dumps(envelope))
PY
<<<"$PAYLOAD_JSON")"

set +e
HTTP_STATUS="$(
  curl -sS --max-time 10 -o /tmp/ocel-emit-response.json -w '%{http_code}' \
    -X POST "$OCEL_INGEST_URL/api/v1/ocel/batches" \
    -H "Authorization: Bearer $OCEL_INGEST_TOKEN" \
    -H "Content-Type: application/json" \
    --data-binary "$ENVELOPE" 2>/tmp/ocel-emit-error.log
)"
set -e
[[ -n "$HTTP_STATUS" ]] || HTTP_STATUS="000"

if [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]]; then
  echo "emit-ocel-capsule-event: OCEL_EMIT=ALIVE status=$HTTP_STATUS run_id=$RUN_ID" >&2
else
  echo "emit-ocel-capsule-event: OCEL_EMIT=UNKNOWN status=$HTTP_STATUS (best-effort, non-fatal) run_id=$RUN_ID" >&2
fi

exit 0
