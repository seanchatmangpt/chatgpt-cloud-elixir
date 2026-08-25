#!/usr/bin/env bash
set -euo pipefail

VARIANT="${1:?usage: scripts/build-postgres-capsule.sh <variant>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAPSULE_CONFIG="$ROOT/capsules/$VARIANT/capsule.toml"
VERSIONS="$ROOT/versions.toml"

[[ -f "$CAPSULE_CONFIG" ]] || { echo "UNSUPPORTED: capsule $VARIANT not found" >&2; exit 64; }
for cmd in python3 curl tar bzip2 sha256sum make cc gzip ldd; do
  command -v "$cmd" >/dev/null || { echo "BLOCKED: required build command '$cmd' is missing" >&2; exit 69; }
done

BUILD_ROOT="${CAPSULE_BUILD_ROOT:-$ROOT/.capsule-build/$VARIANT}"
OUTPUT_DIR="${CAPSULE_OUTPUT_DIR:-$ROOT/dist}"
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT/source" "$BUILD_ROOT/install" "$OUTPUT_DIR"

readarray -t META < <(python3 - "$VERSIONS" "$CAPSULE_CONFIG" <<'PY'
import sys, tomllib
versions = tomllib.load(open(sys.argv[1], "rb"))
cfg = tomllib.load(open(sys.argv[2], "rb"))
version = versions["services"][cfg["version_key"]]
print(version)
print(cfg["source_url_template"].format(version=version))
print(cfg["source_sha256"])
print(str(cfg.get("default_port", 55432)))
for item in cfg.get("configure", []):
    print("CONFIGURE=" + item)
PY
)
PG_VERSION="${META[0]}"
SOURCE_URL="${META[1]}"
EXPECTED_SOURCE_SHA="${META[2]}"
DEFAULT_PORT="${META[3]}"
CONFIGURE_ARGS=()
for line in "${META[@]:4}"; do
  [[ "$line" == CONFIGURE=* ]] && CONFIGURE_ARGS+=("${line#CONFIGURE=}")
done

SOURCE_ARCHIVE="$BUILD_ROOT/source/postgresql-$PG_VERSION.tar.bz2"
curl --fail --location --retry 3 --retry-all-errors --output "$SOURCE_ARCHIVE" "$SOURCE_URL"
ACTUAL_SOURCE_SHA="$(sha256sum "$SOURCE_ARCHIVE" | awk '{print $1}')"
[[ "$ACTUAL_SOURCE_SHA" == "$EXPECTED_SOURCE_SHA" ]] || {
  echo "BUILD_BROKEN: PostgreSQL source digest mismatch expected=$EXPECTED_SOURCE_SHA actual=$ACTUAL_SOURCE_SHA" >&2
  exit 65
}

tar -xjf "$SOURCE_ARCHIVE" -C "$BUILD_ROOT/source"
SOURCE_DIR="$BUILD_ROOT/source/postgresql-$PG_VERSION"
[[ -x "$SOURCE_DIR/configure" ]] || { echo "BUILD_BROKEN: PostgreSQL source tree missing configure" >&2; exit 65; }

pushd "$SOURCE_DIR" >/dev/null
./configure --prefix="$BUILD_ROOT/install" "${CONFIGURE_ARGS[@]}"
make -j"${CAPSULE_BUILD_JOBS:-$(nproc)}"
make install
popd >/dev/null

for bin in postgres initdb pg_ctl psql createdb dropdb pg_isready; do
  [[ -x "$BUILD_ROOT/install/bin/$bin" ]] || { echo "BUILD_BROKEN: installed PostgreSQL missing $bin" >&2; exit 65; }
done
OBSERVED_VERSION="$($BUILD_ROOT/install/bin/postgres --version | awk '{print $3}')"
[[ "$OBSERVED_VERSION" == "$PG_VERSION" ]] || {
  echo "BUILD_BROKEN: PostgreSQL expected $PG_VERSION observed $OBSERVED_VERSION" >&2
  exit 65
}

STAGE="$BUILD_ROOT/capsule"
mkdir -p "$STAGE/runtime/postgres" "$STAGE/scripts" "$STAGE/source"
cp -a "$BUILD_ROOT/install/." "$STAGE/runtime/postgres/"
cp "$ROOT/scripts/postgres-server.sh" "$ROOT/scripts/verify-postgres-capsule.sh" "$STAGE/scripts/"
cp "$CAPSULE_CONFIG" "$STAGE/source/capsule.toml"
cp "$VERSIONS" "$STAGE/source/versions.toml"
chmod +x "$STAGE/scripts/"*.sh

cat > "$STAGE/activate" <<'EOF'
#!/usr/bin/env bash
CAPSULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CAPSULE_ROOT
export POSTGRES_ROOT="$CAPSULE_ROOT/runtime/postgres"
export PATH="$POSTGRES_ROOT/bin:$PATH"
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-55432}"
export PGUSER="${PGUSER:-postgres}"
export PGDATABASE="${PGDATABASE:-postgres}"
EOF
chmod +x "$STAGE/activate"

ldd "$STAGE/runtime/postgres/bin/postgres" > "$STAGE/runtime-deps.txt"
POSTGRES_BIN_SHA="$(sha256sum "$STAGE/runtime/postgres/bin/postgres" | awk '{print $1}')"
PSQL_BIN_SHA="$(sha256sum "$STAGE/runtime/postgres/bin/psql" | awk '{print $1}')"
SOURCE_SHA="${GITHUB_SHA:-unknown}"
BUILT_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export VARIANT SOURCE_SHA BUILT_AT PG_VERSION SOURCE_URL EXPECTED_SOURCE_SHA ACTUAL_SOURCE_SHA DEFAULT_PORT POSTGRES_BIN_SHA PSQL_BIN_SHA
python3 - "$CAPSULE_CONFIG" "$STAGE/manifest.json" <<'PY'
import json, os, sys, tomllib
cfg = tomllib.load(open(sys.argv[1], "rb"))
data = {
  "schema_version": 1,
  "capsule_kind": "service",
  "capsule_name": os.environ["VARIANT"],
  "source_repository": "seanchatmangpt/chatgpt-cloud-elixir",
  "source_sha": os.environ["SOURCE_SHA"],
  "built_at": os.environ["BUILT_AT"],
  "platform": {"os": "linux", "arch": "x86_64"},
  "service": {
    "name": "postgresql",
    "version": os.environ["PG_VERSION"],
    "source_url": os.environ["SOURCE_URL"],
    "source_sha256_expected": os.environ["EXPECTED_SOURCE_SHA"],
    "source_sha256_observed": os.environ["ACTUAL_SOURCE_SHA"],
    "default_port": int(os.environ["DEFAULT_PORT"]),
    "listen": cfg.get("listen", "127.0.0.1")
  },
  "binary_sha256": {
    "postgres": os.environ["POSTGRES_BIN_SHA"],
    "psql": os.environ["PSQL_BIN_SHA"]
  },
  "configure": cfg.get("configure", []),
  "acceptance": cfg.get("acceptance", []),
  "identity_fields": ["source_sha", "capsule_name", "platform", "service", "binary_sha256"]
}
with open(sys.argv[2], "w") as f:
    json.dump(data, f, indent=2, sort_keys=True)
    f.write("\n")
PY

MANIFEST_SHA="$(sha256sum "$STAGE/manifest.json" | awk '{print $1}')"
cat > "$STAGE/build-receipt.json" <<EOF
{
  "schema_version": 1,
  "phase": "construct",
  "source_sha": "$SOURCE_SHA",
  "capsule_name": "$VARIANT",
  "postgresql_version": "$PG_VERSION",
  "postgresql_source_sha256": "$ACTUAL_SOURCE_SHA",
  "manifest_sha256": "$MANIFEST_SHA",
  "standing": "ALIVE",
  "note": "Construction receipt only; fresh consumer service execution is required for capsule ALIVE standing."
}
EOF

NAME="chatgpt-cloud-elixir-${VARIANT}-pg${PG_VERSION}-linux-x86_64"
ARCHIVE="$OUTPUT_DIR/$NAME.tar.gz"
(
  cd "$STAGE"
  tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 --numeric-owner -cf - . | gzip -n > "$ARCHIVE"
)
ARCHIVE_SHA="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
printf '%s  %s\n' "$ARCHIVE_SHA" "$(basename "$ARCHIVE")" > "$ARCHIVE.sha256"
printf '%s\n' "$ARCHIVE"
