#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/activate"

ARCHIVE_DIGEST="${CAPSULE_ARCHIVE_DIGEST:-external-not-supplied}"
NETWORK_MODE="${CAPSULE_NETWORK_MODE:-loopback_only}"
STATE_ROOT="${POSTGRES_STATE_DIR:-$ROOT/verification-state/postgres}"
export POSTGRES_STATE_DIR="$STATE_ROOT"
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-55432}"
export PGUSER="${PGUSER:-postgres}"
export PGDATABASE="postgres"
LOG="$ROOT/verification.log"
rm -rf "$ROOT/verification-state"
mkdir -p "$ROOT/verification-state"

set +e
(
  set -euo pipefail
  postgres --version
  initdb --version
  pg_ctl --version
  psql --version

  "$ROOT/scripts/postgres-server.sh" init
  "$ROOT/scripts/postgres-server.sh" start
  trap '"$ROOT/scripts/postgres-server.sh" stop >/dev/null 2>&1 || true' EXIT
  "$ROOT/scripts/postgres-server.sh" status

  SERVER_VERSION="$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -Atqc 'SHOW server_version')"
  EXPECTED_VERSION="$(sed -n 's/.*"version": "\([^"]*\)".*/\1/p' "$ROOT/manifest.json" | head -1)"
  [[ "$SERVER_VERSION" == "$EXPECTED_VERSION" ]] || {
    echo "BUILD_BROKEN: server version expected=$EXPECTED_VERSION observed=$SERVER_VERSION" >&2
    exit 65
  }

  dropdb --if-exists -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" capsule_acceptance
  createdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" capsule_acceptance
  psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d capsule_acceptance -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE receipt_probe (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  value text NOT NULL UNIQUE,
  revision integer NOT NULL DEFAULT 0
);
INSERT INTO receipt_probe (value) VALUES ('created');
SELECT id, value, revision FROM receipt_probe WHERE value = 'created';
UPDATE receipt_probe SET value = 'updated', revision = revision + 1 WHERE value = 'created';
SELECT id, value, revision FROM receipt_probe WHERE value = 'updated';
DELETE FROM receipt_probe WHERE value = 'updated';
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM receipt_probe) THEN
    RAISE EXCEPTION 'receipt_probe cleanup failed';
  END IF;
END
$$;
SQL
  dropdb -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" capsule_acceptance
  "$ROOT/scripts/postgres-server.sh" stop
  trap - EXIT
) 2>&1 | tee "$LOG"
STATUS=${PIPESTATUS[0]}
set -e

if [[ "$STATUS" -eq 0 ]]; then
  STANDING="ALIVE"
else
  STANDING="BUILD_BROKEN"
fi

SOURCE_SHA="$(sed -n 's/.*"source_sha": "\([^"]*\)".*/\1/p' "$ROOT/manifest.json" | head -1)"
CAPSULE_NAME="$(sed -n 's/.*"capsule_name": "\([^"]*\)".*/\1/p' "$ROOT/manifest.json" | head -1)"
POSTGRES_VERSION="$(sed -n 's/.*"version": "\([^"]*\)".*/\1/p' "$ROOT/manifest.json" | head -1)"
MANIFEST_SHA="$(sha256sum "$ROOT/manifest.json" | awk '{print $1}')"
VERIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$ROOT/receipt.json" <<EOF
{
  "schema_version": 1,
  "phase": "consumer_service_replay",
  "source_sha": "$SOURCE_SHA",
  "capsule_name": "$CAPSULE_NAME",
  "capsule_archive_sha256": "$ARCHIVE_DIGEST",
  "manifest_sha256": "$MANIFEST_SHA",
  "postgresql_version": "$POSTGRES_VERSION",
  "network_mode": "$NETWORK_MODE",
  "listen": "$PGHOST",
  "port": $PGPORT,
  "acceptance_command": "postgres --version && initdb && pg_ctl start && SQL CRUD lifecycle && pg_ctl stop",
  "acceptance_exit_code": $STATUS,
  "verified_at": "$VERIFIED_AT",
  "standing": "$STANDING",
  "replay": "CAPSULE_ARCHIVE_DIGEST=$ARCHIVE_DIGEST CAPSULE_NETWORK_MODE=$NETWORK_MODE bash scripts/verify-postgres-capsule.sh"
}
EOF
cat "$ROOT/receipt.json"
exit "$STATUS"
