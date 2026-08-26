#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="$ROOT/capsules/process-intelligence/capsule.toml"
OUTPUT_DIR="${CAPSULE_OUTPUT_DIR:-$ROOT/dist}"
WORK="${CAPSULE_BUILD_ROOT:-$ROOT/.capsule-build/process-intelligence}"
BASE_OUT="$WORK/base-dist"
BASE_BUILD="$WORK/base-build"
rm -rf "$WORK"
mkdir -p "$WORK" "$BASE_OUT" "$OUTPUT_DIR"

for cmd in git python3 tar gzip sha256sum erl elixir mix; do
  command -v "$cmd" >/dev/null || { echo "BLOCKED: required build command '$cmd' is missing" >&2; exit 69; }
done

PROCESS_OTP="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["runtime"]["otp"])' "$CFG")"
PROCESS_ELIXIR="$(python3 -c 'import tomllib,sys; print(tomllib.load(open(sys.argv[1],"rb"))["runtime"]["elixir"])' "$CFG")"
ACTUAL_OTP="$(erl -noshell -eval 'io:format("~s", [erlang:system_info(otp_release)]), halt().')"
ACTUAL_ELIXIR="$(elixir -e 'IO.write(System.version())')"
[[ "${ACTUAL_OTP%%.*}" == "${PROCESS_OTP%%.*}" ]] || {
  echo "BUILD_BROKEN: process-intelligence OTP expected $PROCESS_OTP observed $ACTUAL_OTP" >&2; exit 65;
}
[[ "$ACTUAL_ELIXIR" == "$PROCESS_ELIXIR" ]] || {
  echo "BUILD_BROKEN: process-intelligence Elixir expected $PROCESS_ELIXIR observed $ACTUAL_ELIXIR" >&2; exit 65;
}

CAPSULE_OTP_OVERRIDE="$PROCESS_OTP" \
CAPSULE_ELIXIR_OVERRIDE="$PROCESS_ELIXIR" \
CAPSULE_OUTPUT_DIR="$BASE_OUT" \
CAPSULE_BUILD_ROOT="$BASE_BUILD" \
  bash "$ROOT/scripts/build-capsule.sh" beam-core >/dev/null
BASE_ARCHIVE="$(ls "$BASE_OUT"/chatgpt-cloud-elixir-beam-core-*.tar.gz)"
STAGE="$WORK/stage"
mkdir -p "$STAGE"
tar -xzf "$BASE_ARCHIVE" -C "$STAGE"
# shellcheck disable=SC1091
source "$STAGE/activate"
export HEX_OFFLINE=0

mkdir -p "$STAGE/subjects"
SUBJECT_ROWS="$WORK/subjects.ndjson"
: > "$SUBJECT_ROWS"

# Materialize dependency-closed local-path inputs before any subject build.
# ex4pm/apps/ex4pm_domain resolves ../../../wasm4pm-compat/bindings/elixir
# to this sibling of subjects/ex4pm. Identity is pinned in capsule.toml.
python3 - "$CFG" <<'PY' > "$WORK/dependencies.ndjson"
import json, sys, tomllib
cfg = tomllib.load(open(sys.argv[1], "rb"))
for name, dep in sorted(cfg.get("dependencies", {}).items()):
    row = {"name": name, **dep}
    print(json.dumps(row, sort_keys=True))
PY
while IFS= read -r DEP_ROW; do
  [[ -n "$DEP_ROW" ]] || continue
  DEP_NAME="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["name"])' "$DEP_ROW")"
  DEP_REPOSITORY="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["repository"])' "$DEP_ROW")"
  DEP_SHA="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["sha"])' "$DEP_ROW")"
  DEP_TREE_SHA="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["tree_sha"])' "$DEP_ROW")"
  DEP_MATERIALIZE_AS="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["materialize_as"])' "$DEP_ROW")"
  [[ "$DEP_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "BUILD_BROKEN: invalid SHA for dependency $DEP_NAME" >&2; exit 65; }
  [[ "$DEP_TREE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "BUILD_BROKEN: invalid tree SHA for dependency $DEP_NAME" >&2; exit 65; }
  [[ "$DEP_MATERIALIZE_AS" != /* && "$DEP_MATERIALIZE_AS" != *".."* ]] || {
    echo "REFUSED: unsafe materialization path for dependency $DEP_NAME" >&2; exit 64;
  }
  DEP_GIT_DIR="$WORK/git-dependency-$DEP_NAME"
  DEP_SOURCE_DIR="$STAGE/subjects/$DEP_MATERIALIZE_AS"
  git init -q "$DEP_GIT_DIR"
  git -C "$DEP_GIT_DIR" remote add origin "$DEP_REPOSITORY"
  git -C "$DEP_GIT_DIR" fetch -q --depth=1 origin "$DEP_SHA"
  git -C "$DEP_GIT_DIR" checkout -q --detach FETCH_HEAD
  [[ "$(git -C "$DEP_GIT_DIR" rev-parse HEAD)" == "$DEP_SHA" ]] || { echo "BUILD_BROKEN: dependency $DEP_NAME commit identity mismatch" >&2; exit 65; }
  [[ "$(git -C "$DEP_GIT_DIR" rev-parse 'HEAD^{tree}')" == "$DEP_TREE_SHA" ]] || { echo "BUILD_BROKEN: dependency $DEP_NAME tree identity mismatch" >&2; exit 65; }
  mkdir -p "$DEP_SOURCE_DIR"
  git -C "$DEP_GIT_DIR" archive HEAD | tar -x -C "$DEP_SOURCE_DIR"
done < "$WORK/dependencies.ndjson"

for SUBJECT in ash_r2rml ex4pm; do
  REPOSITORY="$(python3 - "$CFG" "$SUBJECT" <<'PY'
import sys, tomllib
cfg = tomllib.load(open(sys.argv[1], "rb"))
print(cfg["subjects"][sys.argv[2]]["repository"])
PY
)"
  SHA="$(python3 - "$CFG" "$SUBJECT" <<'PY'
import sys, tomllib
cfg = tomllib.load(open(sys.argv[1], "rb"))
print(cfg["subjects"][sys.argv[2]]["sha"])
PY
)"
  TREE_SHA="$(python3 - "$CFG" "$SUBJECT" <<'PY'
import sys, tomllib
cfg = tomllib.load(open(sys.argv[1], "rb"))
print(cfg["subjects"][sys.argv[2]]["tree_sha"])
PY
)"
  [[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "BUILD_BROKEN: invalid SHA for $SUBJECT" >&2; exit 65; }
  [[ "$TREE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "BUILD_BROKEN: invalid tree SHA for $SUBJECT" >&2; exit 65; }
  [[ "$REPOSITORY" == https://github.com/*.git ]] || {
    echo "UNSUPPORTED: subject repository must be public github.com git URL" >&2; exit 64;
  }

  GIT_DIR="$WORK/git-$SUBJECT"
  SOURCE_DIR="$STAGE/subjects/$SUBJECT"
  git init -q "$GIT_DIR"
  git -C "$GIT_DIR" remote add origin "$REPOSITORY"
  git -C "$GIT_DIR" fetch -q --depth=1 origin "$SHA"
  git -C "$GIT_DIR" checkout -q --detach FETCH_HEAD
  OBSERVED_SHA="$(git -C "$GIT_DIR" rev-parse HEAD)"
  OBSERVED_TREE="$(git -C "$GIT_DIR" rev-parse 'HEAD^{tree}')"
  [[ "$OBSERVED_SHA" == "$SHA" ]] || { echo "BUILD_BROKEN: $SUBJECT commit identity mismatch" >&2; exit 65; }
  [[ "$OBSERVED_TREE" == "$TREE_SHA" ]] || { echo "BUILD_BROKEN: $SUBJECT tree identity mismatch" >&2; exit 65; }

  mkdir -p "$SOURCE_DIR"
  git -C "$GIT_DIR" archive HEAD | tar -x -C "$SOURCE_DIR"
  pushd "$SOURCE_DIR" >/dev/null
  mix deps.get
  mapfile -t BUILD_COMMANDS < <(python3 - "$CFG" "$SUBJECT" <<'PY'
import sys, tomllib
cfg = tomllib.load(open(sys.argv[1], "rb"))
for command in cfg["subjects"][sys.argv[2]]["build_acceptance"]:
    print(command)
PY
)
  for command in "${BUILD_COMMANDS[@]}"; do
    echo ">>> [$SUBJECT build] $command"
    bash -lc "$command"
  done
  popd >/dev/null

  LOCK_SHA="none"
  [[ -f "$SOURCE_DIR/mix.lock" ]] && LOCK_SHA="$(sha256sum "$SOURCE_DIR/mix.lock" | awk '{print $1}')"
  python3 - "$SUBJECT_ROWS" "$SUBJECT" "$REPOSITORY" "$SHA" "$TREE_SHA" "$LOCK_SHA" <<'PY'
import json, sys
path, name, repository, sha, tree_sha, lock_sha = sys.argv[1:]
with open(path, "a") as f:
    f.write(json.dumps({
        "name": name,
        "repository": repository,
        "sha": sha,
        "tree_sha": tree_sha,
        "dependency_lock_sha256": lock_sha,
        "build_acceptance_exit_code": 0,
    }, sort_keys=True) + "\n")
PY
done

rm -rf "$STAGE/harness"
cp -a "$ROOT/capsules/process-intelligence/harness" "$STAGE/harness"
cp "$ROOT/capsules/process-intelligence/verify-capsule.sh" "$STAGE/scripts/verify-capsule.sh"
chmod +x "$STAGE/scripts/verify-capsule.sh" "$STAGE/harness/verify.sh"
cp "$CFG" "$STAGE/source/capsule.toml"

python3 - "$STAGE/manifest.json" "$CFG" "$SUBJECT_ROWS" <<'PY'
import json, sys, tomllib
manifest_path, cfg_path, rows_path = sys.argv[1:]
manifest = json.load(open(manifest_path))
cfg = tomllib.load(open(cfg_path, "rb"))
subjects = {}
for line in open(rows_path):
    item = json.loads(line)
    subjects[item.pop("name")] = item
manifest["capsule_name"] = cfg["name"]
manifest["required_modules"] = cfg.get("required_modules", [])
manifest["requires_services"] = cfg.get("requires_services", [])
manifest["acceptance"] = cfg.get("acceptance", [])
manifest["subjects"] = subjects
manifest["dependencies"] = cfg.get("dependencies", {})
manifest["process_lab"] = cfg.get("process_lab", {})
manifest["identity_fields"] = [
    "source_sha", "capsule_name", "platform", "runtime", "subjects", "dependencies"
]
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
    f.write("\n")
PY

MANIFEST_SHA="$(sha256sum "$STAGE/manifest.json" | awk '{print $1}')"
SOURCE_SHA="${GITHUB_SHA:-unknown}"
cat > "$STAGE/build-receipt.json" <<EOF2
{
  "schema_version": 1,
  "phase": "construct",
  "source_sha": "$SOURCE_SHA",
  "capsule_name": "process-intelligence",
  "manifest_sha256": "$MANIFEST_SHA",
  "subject_build_acceptance_exit_code": 0,
  "standing": "ALIVE",
  "note": "Construction receipt only; fresh offline consumer replay is required for capsule ALIVE standing."
}
EOF2

EXPECTED_OTP="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["runtime"]["otp_expected"])' "$STAGE/manifest.json")"
EXPECTED_ELIXIR="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["runtime"]["elixir_expected"])' "$STAGE/manifest.json")"
NAME="chatgpt-cloud-elixir-process-intelligence-otp${EXPECTED_OTP%%.*}-elixir${EXPECTED_ELIXIR}-linux-x86_64"
ARCHIVE="$OUTPUT_DIR/$NAME.tar.gz"
(
  cd "$STAGE"
  tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 --numeric-owner -cf - . | gzip -n > "$ARCHIVE"
)
ARCHIVE_SHA="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
printf '%s  %s\n' "$ARCHIVE_SHA" "$(basename "$ARCHIVE")" > "$ARCHIVE.sha256"
printf '%s\n' "$ARCHIVE"
