#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/activate"

STATE_ROOT="${POSTGRES_STATE_DIR:-$ROOT/state/postgres}"
PGDATA="${PGDATA:-$STATE_ROOT/data}"
PGLOG="${PGLOG:-$STATE_ROOT/postgres.log}"
PGPORT="${PGPORT:-55432}"
PGHOST="${PGHOST:-127.0.0.1}"
PGUSER="${PGUSER:-postgres}"
RUN_UID="${POSTGRES_RUN_UID:-65534}"
RUN_GID="${POSTGRES_RUN_GID:-65534}"
SOCKET_KEY="$(printf '%s' "$STATE_ROOT" | sha256sum | cut -c1-12)"
PGSOCKET="${PGSOCKET:-${POSTGRES_SOCKET_ROOT:-/tmp}/cce-pg-${PGPORT}-${SOCKET_KEY}}"

export PGDATA PGPORT PGHOST PGUSER PGSOCKET

prepare_state() {
  mkdir -p "$STATE_ROOT" "$STATE_ROOT/home" "$PGSOCKET"
  chmod 700 "$PGSOCKET"
  if [[ "$(id -u)" -eq 0 ]]; then
    chown -R "$RUN_UID:$RUN_GID" "$STATE_ROOT"
    chown "$RUN_UID:$RUN_GID" "$PGSOCKET"
  fi

  local socket_filename="$PGSOCKET/.s.PGSQL.$PGPORT"
  if (( ${#socket_filename} > 107 )); then
    echo "REFUSED(POSTGRES_SOCKET_PATH_TOO_LONG): $socket_filename (${#socket_filename} bytes; max 107)" >&2
    return 65
  fi
}

run_server_user() {
  if [[ "$(id -u)" -eq 0 ]]; then
    command -v setpriv >/dev/null || {
      echo "BLOCKED: root consumer requires setpriv to demote PostgreSQL server privileges" >&2
      return 69
    }
    setpriv --reuid="$RUN_UID" --regid="$RUN_GID" --clear-groups \
      env HOME="$STATE_ROOT/home" PATH="$PATH" PGDATA="$PGDATA" PGPORT="$PGPORT" PGHOST="$PGHOST" PGUSER="$PGUSER" PGSOCKET="$PGSOCKET" "$@"
  else
    env HOME="${HOME:-$STATE_ROOT/home}" PATH="$PATH" PGDATA="$PGDATA" PGPORT="$PGPORT" PGHOST="$PGHOST" PGUSER="$PGUSER" PGSOCKET="$PGSOCKET" "$@"
  fi
}

init_cluster() {
  prepare_state
  if [[ -f "$PGDATA/PG_VERSION" ]]; then
    return 0
  fi
  mkdir -p "$PGDATA"
  if [[ "$(id -u)" -eq 0 ]]; then
    chown -R "$RUN_UID:$RUN_GID" "$PGDATA"
  fi
  run_server_user initdb -D "$PGDATA" -A trust -U "$PGUSER" --encoding=UTF8 --no-locale
}

start_server() {
  init_cluster
  prepare_state
  run_server_user pg_ctl -D "$PGDATA" -w -t 30 -l "$PGLOG" \
    -o "-h $PGHOST -p $PGPORT -k $PGSOCKET" start
  pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres
}

stop_server() {
  if [[ -f "$PGDATA/PG_VERSION" ]] && run_server_user pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
    run_server_user pg_ctl -D "$PGDATA" -w -t 30 -m fast stop
  fi
}

status_server() {
  run_server_user pg_ctl -D "$PGDATA" status
  pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres
}

print_env() {
  printf 'export POSTGRES_STATE_DIR=%q\n' "$STATE_ROOT"
  printf 'export PGDATA=%q\n' "$PGDATA"
  printf 'export PGSOCKET=%q\n' "$PGSOCKET"
  printf 'export PGHOST=%q\n' "$PGHOST"
  printf 'export PGPORT=%q\n' "$PGPORT"
  printf 'export PGUSER=%q\n' "$PGUSER"
  printf 'export PGDATABASE=%q\n' "${PGDATABASE:-postgres}"
}

case "${1:-}" in
  init)
    init_cluster
    ;;
  start)
    start_server
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server
    start_server
    ;;
  status)
    status_server
    ;;
  env)
    print_env
    ;;
  psql)
    shift
    exec psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$@"
    ;;
  *)
    echo "usage: scripts/postgres-server.sh {init|start|stop|restart|status|env|psql [args...]}" >&2
    exit 64
    ;;
esac
