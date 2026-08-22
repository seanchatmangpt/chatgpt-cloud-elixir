#!/usr/bin/env bash
set -euo pipefail

for command in flyctl openssl; do
  command -v "$command" >/dev/null || {
    echo "BLOCKED: required command '$command' is unavailable" >&2
    exit 69
  }
done

APP="${FLY_APP_NAME:-chatgpt-cloud-process-intelligence}"
REGION="${FLY_REGION:-lax}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-$(openssl rand -hex 24)}"
OCEL_INGEST_TOKEN="${OCEL_INGEST_TOKEN:-$(openssl rand -hex 32)}"
SECRET_KEY_BASE="${SECRET_KEY_BASE:-$(openssl rand -hex 64)}"
PHX_HOST="${PHX_HOST:-${APP}.fly.dev}"

ORG_ARGS=()
if [[ -n "${FLY_ORG:-}" ]]; then
  ORG_ARGS=(--org "$FLY_ORG")
fi

if ! flyctl apps show "$APP" >/dev/null 2>&1; then
  flyctl apps create "$APP" "${ORG_ARGS[@]}"
fi

if [[ -n "${FLY_MPG_CLUSTER_ID:-}" ]]; then
  flyctl mpg attach "$FLY_MPG_CLUSTER_ID" --app "$APP"
elif [[ -n "${FLY_POSTGRES_APP:-}" ]]; then
  flyctl postgres attach "$FLY_POSTGRES_APP" --app "$APP" --yes
elif [[ -n "${DATABASE_URL:-}" ]]; then
  flyctl secrets set --app "$APP" --stage "DATABASE_URL=$DATABASE_URL"
else
  cat >&2 <<'EOF'
BLOCKED: no PostgreSQL subject was admitted.
Set exactly one of:
  FLY_MPG_CLUSTER_ID   existing Fly Managed Postgres cluster id (recommended)
  FLY_POSTGRES_APP     existing unmanaged Fly Postgres app
  DATABASE_URL         existing PostgreSQL connection URL
EOF
  exit 69
fi

flyctl secrets set --app "$APP" --stage \
  "ADMIN_USERNAME=$ADMIN_USERNAME" \
  "ADMIN_PASSWORD=$ADMIN_PASSWORD" \
  "OCEL_INGEST_TOKEN=$OCEL_INGEST_TOKEN" \
  "SECRET_KEY_BASE=$SECRET_KEY_BASE" \
  "PHX_HOST=$PHX_HOST"

flyctl deploy --app "$APP"

cat <<EOF
ALIVE: Fly control-plane deployment completed.
Dashboard: https://${PHX_HOST}/process-intelligence/live
AshAdmin:  https://${PHX_HOST}/admin
Ingest:    https://${PHX_HOST}/api/v1/ocel/batches

Generated/selected credentials (store them now; Fly will not reveal secret values later):
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
OCEL_INGEST_TOKEN=${OCEL_INGEST_TOKEN}
EOF
