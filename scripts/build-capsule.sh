#!/usr/bin/env bash
set -euo pipefail

VARIANT="${1:?usage: scripts/build-capsule.sh <variant>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAPSULE_CONFIG="$ROOT/capsules/$VARIANT/capsule.toml"
VERSIONS="$ROOT/versions.toml"

[[ -f "$CAPSULE_CONFIG" ]] || { echo "UNSUPPORTED: capsule $VARIANT not found" >&2; exit 64; }
for cmd in python3 erl elixir mix tar gzip sha256sum; do
  command -v "$cmd" >/dev/null || { echo "BLOCKED: required build command '$cmd' is missing" >&2; exit 69; }
done

BUILD_ROOT="${CAPSULE_BUILD_ROOT:-$ROOT/.capsule-build/$VARIANT}"
OUTPUT_DIR="${CAPSULE_OUTPUT_DIR:-$ROOT/dist}"
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT/project" "$BUILD_ROOT/host/mix" "$BUILD_ROOT/host/hex" "$OUTPUT_DIR"
export MIX_HOME="$BUILD_ROOT/host/mix"
export HEX_HOME="$BUILD_ROOT/host/hex"

DEFAULT_OTP="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["runtime"]["otp"])' "$VERSIONS")"
DEFAULT_ELIXIR="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["runtime"]["elixir"])' "$VERSIONS")"
EXPECTED_OTP="${CAPSULE_OTP_OVERRIDE:-$DEFAULT_OTP}"
EXPECTED_ELIXIR="${CAPSULE_ELIXIR_OVERRIDE:-$DEFAULT_ELIXIR}"
ACTUAL_OTP="$(erl -noshell -eval 'io:format("~s", [erlang:system_info(otp_release)]), halt().')"
ACTUAL_ELIXIR="$(elixir -e 'IO.write(System.version())')"
[[ "${ACTUAL_OTP%%.*}" == "${EXPECTED_OTP%%.*}" ]] || { echo "BUILD_BROKEN: OTP expected $EXPECTED_OTP observed $ACTUAL_OTP" >&2; exit 65; }
[[ "$ACTUAL_ELIXIR" == "$EXPECTED_ELIXIR" ]] || { echo "BUILD_BROKEN: Elixir expected $EXPECTED_ELIXIR observed $ACTUAL_ELIXIR" >&2; exit 65; }

mix local.hex --force
mix local.rebar --force
HEX_VERSION="$(mix hex.info 2>/dev/null | sed -n 's/^Hex: //p' | head -1)"
REBAR_BIN="$(find "$MIX_HOME" -type f -name rebar3 -perm -u+x | head -1)"
REBAR_VERSION="$($REBAR_BIN version 2>/dev/null | awk '{print $2}' | head -1)"
MIX_VERSION="$(mix --version | sed -n 's/^Mix //p' | head -1)"

FIXTURE="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["fixture"])' "$CAPSULE_CONFIG")"
cp -a "$ROOT/fixtures/$FIXTURE/." "$BUILD_ROOT/project/"

python3 - "$VERSIONS" "$CAPSULE_CONFIG" "$BUILD_ROOT/project" "$EXPECTED_ELIXIR" <<'PY'
import pathlib, sys, tomllib
versions = tomllib.load(open(sys.argv[1], "rb"))
cfg = tomllib.load(open(sys.argv[2], "rb"))
project = pathlib.Path(sys.argv[3])
expected_elixir = sys.argv[4]
deps = []
for package in cfg.get("packages", []):
    version = versions["packages"][package]
    deps.append(f'{{:{package}, "== {version}"}}')
deps_text = ",\n        ".join(deps)
project.joinpath("mix.exs").write_text(f'''defmodule CloudCapsule.MixProject do
  use Mix.Project

  def project do
    [
      app: :cloud_capsule,
      version: "0.1.0",
      elixir: "~> {expected_elixir.rsplit(".", 1)[0]}",
      start_permanent: false,
      deps: deps()
    ]
  end

  def application, do: [extra_applications: [:logger]]

  defp deps do
    [
        {deps_text}
    ]
  end
end
''')
mods = cfg.get("required_modules", [])
body = ['defmodule CapsuleModulesTest do', '  use ExUnit.Case, async: true', '', '  test "admitted package modules load" do']
if mods:
    for mod in mods:
        body.append(f'    assert Code.ensure_loaded?({mod}), "expected {mod} to load"')
else:
    body.append('    assert Code.ensure_loaded?(Mix)')
body += ['  end', 'end', '']
project.joinpath("test", "capsule_modules_test.exs").write_text("\n".join(body))
PY

pushd "$BUILD_ROOT/project" >/dev/null
mix deps.get
MIX_ENV=test mix compile --warnings-as-errors
MIX_ENV=test mix test 2>&1 | tee "$BUILD_ROOT/build-test.log"
popd >/dev/null

OTP_BIN_REAL="$(dirname "$(readlink -f "$(command -v erl)")")"
ELIXIR_BIN_REAL="$(dirname "$(readlink -f "$(command -v elixir)")")"
OTP_ROOT="$(cd "$OTP_BIN_REAL/.." && pwd)"
ELIXIR_ROOT="$(cd "$ELIXIR_BIN_REAL/.." && pwd)"
STAGE="$BUILD_ROOT/capsule"
mkdir -p "$STAGE/runtime/otp" "$STAGE/runtime/elixir" "$STAGE/home/mix" "$STAGE/home/hex" "$STAGE/home/rebar" "$STAGE/scripts" "$STAGE/verifier" "$STAGE/source"
cp -a "$OTP_ROOT/." "$STAGE/runtime/otp/"
cp -a "$ELIXIR_ROOT/." "$STAGE/runtime/elixir/"
cp -a "$MIX_HOME/." "$STAGE/home/mix/"
cp -a "$HEX_HOME/." "$STAGE/home/hex/"
cp -a "$BUILD_ROOT/project" "$STAGE/project"
cp "$ROOT/scripts/install-capsule.sh" "$ROOT/scripts/inspect-capsule.sh" "$ROOT/scripts/verify-capsule.sh" "$ROOT/scripts/run-offline.sh" "$ROOT/scripts/emit-ocel-capsule-event.sh" "$STAGE/scripts/"
cp "$ROOT/verifier/verify_manifest.exs" "$ROOT/verifier/verify_runtime.exs" "$STAGE/verifier/"
cp "$CAPSULE_CONFIG" "$STAGE/source/capsule.toml"
cp "$VERSIONS" "$STAGE/source/versions.toml"
chmod +x "$STAGE/scripts/"*.sh

ERTS_DIR="$(basename "$(find "$STAGE/runtime/otp" -maxdepth 1 -type d -name 'erts-*' | sort -V | tail -1)")"
[[ -n "$ERTS_DIR" ]] || { echo "BUILD_BROKEN: copied OTP runtime has no erts directory" >&2; exit 65; }
cat > "$STAGE/runtime/otp/bin/erl" <<EOF
#!/usr/bin/env bash
set -e
ROOTDIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")/.." && pwd)"
BINDIR="\$ROOTDIR/$ERTS_DIR/bin"
EMU=beam
PROGNAME="\${0##*/}"
export ROOTDIR BINDIR EMU PROGNAME
exec "\$BINDIR/erlexec" "\$@"
EOF
cat > "$STAGE/runtime/otp/bin/erlc" <<'EOF'
#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$HERE/erl" -noshell -noinput -s erl_compile compile_cmdline -extra "$@"
EOF
chmod +x "$STAGE/runtime/otp/bin/erl" "$STAGE/runtime/otp/bin/erlc"

cat > "$STAGE/activate" <<'EOF'
#!/usr/bin/env bash
CAPSULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CAPSULE_ROOT
export PATH="$CAPSULE_ROOT/runtime/elixir/bin:$CAPSULE_ROOT/runtime/otp/bin:$PATH"
export MIX_HOME="$CAPSULE_ROOT/home/mix"
export HEX_HOME="$CAPSULE_ROOT/home/hex"
export REBAR_CACHE_DIR="$CAPSULE_ROOT/home/rebar"
export HEX_OFFLINE=1
EOF
chmod +x "$STAGE/activate"

LOCK_SHA="none"
[[ -f "$STAGE/project/mix.lock" ]] && LOCK_SHA="$(sha256sum "$STAGE/project/mix.lock" | awk '{print $1}')"
SOURCE_SHA="${GITHUB_SHA:-unknown}"
BUILT_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export VARIANT SOURCE_SHA BUILT_AT EXPECTED_OTP EXPECTED_ELIXIR ACTUAL_OTP ACTUAL_ELIXIR MIX_VERSION HEX_VERSION REBAR_VERSION LOCK_SHA
python3 - "$VERSIONS" "$CAPSULE_CONFIG" "$STAGE/manifest.json" <<'PY'
import json, os, sys, tomllib
versions = tomllib.load(open(sys.argv[1], "rb"))
cfg = tomllib.load(open(sys.argv[2], "rb"))
packages = {name: versions["packages"][name] for name in cfg.get("packages", [])}
data = {
  "schema_version": 1,
  "capsule_name": os.environ["VARIANT"],
  "source_repository": "seanchatmangpt/chatgpt-cloud-elixir",
  "source_sha": os.environ["SOURCE_SHA"],
  "built_at": os.environ["BUILT_AT"],
  "platform": {"os": "linux", "arch": "x86_64"},
  "runtime": {
    "otp_expected": os.environ["EXPECTED_OTP"],
    "otp_observed": os.environ["ACTUAL_OTP"],
    "elixir_expected": os.environ["EXPECTED_ELIXIR"],
    "elixir_observed": os.environ["ACTUAL_ELIXIR"],
    "mix": os.environ["MIX_VERSION"],
    "hex": os.environ["HEX_VERSION"],
    "rebar": os.environ["REBAR_VERSION"]
  },
  "packages": packages,
  "required_modules": cfg.get("required_modules", []),
  "requires_services": cfg.get("requires_services", []),
  "acceptance": cfg.get("acceptance", []),
  "dependency_lock_sha256": os.environ["LOCK_SHA"],
  "identity_fields": ["source_sha", "capsule_name", "platform", "runtime", "packages", "dependency_lock_sha256"]
}
with open(sys.argv[3], "w") as f:
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
  "manifest_sha256": "$MANIFEST_SHA",
  "build_fixture_tests_exit_code": 0,
  "standing": "ALIVE",
  "note": "Construction receipt only; consumer replay is required for capsule ALIVE standing."
}
EOF

NAME="chatgpt-cloud-elixir-${VARIANT}-otp${EXPECTED_OTP%%.*}-elixir${EXPECTED_ELIXIR}-linux-x86_64"
ARCHIVE="$OUTPUT_DIR/$NAME.tar.gz"
(
  cd "$STAGE"
  tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 --numeric-owner -cf - . | gzip -n > "$ARCHIVE"
)
ARCHIVE_SHA="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
printf '%s  %s\n' "$ARCHIVE_SHA" "$(basename "$ARCHIVE")" > "$ARCHIVE.sha256"
printf '%s\n' "$ARCHIVE"
