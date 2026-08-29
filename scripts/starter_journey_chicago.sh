#!/usr/bin/env bash
set -euo pipefail

: "${SUBJECT_REPOSITORY:?SUBJECT_REPOSITORY is required}"
: "${SUBJECT_REF:?SUBJECT_REF is required}"
: "${SUBJECT_SHA:?SUBJECT_SHA is required}"

work_root="${RUNNER_TEMP:-/tmp}/starter-journey-chicago"
rm -rf "$work_root"
mkdir -p "$work_root"
repo_url="https://github.com/${SUBJECT_REPOSITORY}.git"

anonymous_clone() {
  local dest="$1"
  env -u GITHUB_TOKEN -u GH_TOKEN git -c credential.helper= clone --quiet --depth 1 --no-tags --branch "$SUBJECT_REF" "$repo_url" "$dest"
  test "$(git -C "$dest" rev-parse HEAD)" = "$SUBJECT_SHA"
}

generated_digest() {
  local consumer="$1"
  (
    cd "$consumer/manufacturing/generated"
    find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}'
  )
}

assert_expected_runtime_writes() {
  local consumer="$1"
  local status
  status="$(git -C "$consumer" status --porcelain --untracked-files=all)"
  test -n "$status"
  while IFS= read -r line; do
    case "$line" in
      "?? manufacturing/generated/"*) ;;
      "?? manufacturing/.ggen-v2/receipt-log.jsonl") ;;
      *) echo "unexpected worktree mutation: $line" >&2; return 1 ;;
    esac
  done <<< "$status"
}

verify_ggen_receipt_log() {
  local consumer="$1"
  local receipt_log="$consumer/manufacturing/.ggen-v2/receipt-log.jsonl"
  test -s "$receipt_log"
  python3 - "$receipt_log" <<'PY'
import json, sys
lines = [line for line in open(sys.argv[1]) if line.strip()]
assert lines, "empty ggen receipt log"
for line in lines:
    value = json.loads(line)
    assert isinstance(value, dict) and value, "malformed ggen receipt"
print(len(lines))
PY
}

# Chicago edge 1: a stranger performs real anonymous clones of the public PR branch.
anonymous_clone "$work_root/consumer-a"
anonymous_clone "$work_root/consumer-b"

# Resolve the real bootstrap identity from the exact consumer subject.
mapfile -t bootstrap < <(python3 - "$work_root/consumer-a/versions.toml" <<'PY'
import sys, tomllib
v = tomllib.load(open(sys.argv[1], "rb"))["bootstrap"]
print(v["ggen_repository"])
print(v["ggen_sha"])
print(v["rust_toolchain"])
PY
)
ggen_repository="${bootstrap[0]}"
ggen_sha="${bootstrap[1]}"
rust_toolchain="${bootstrap[2]}"
[[ "$ggen_sha" =~ ^[0-9a-f]{40}$ ]]

# Chicago edge 2: resolve the exact immutable GGen source through public Git transport.
ggen_dir="$work_root/ggen"
mkdir -p "$ggen_dir"
git -C "$ggen_dir" init -q
git -C "$ggen_dir" remote add origin "https://github.com/${ggen_repository}.git"
env -u GITHUB_TOKEN -u GH_TOKEN git -C "$ggen_dir" -c credential.helper= fetch -q --depth 1 origin "$ggen_sha"
git -C "$ggen_dir" checkout -q --detach FETCH_HEAD
test "$(git -C "$ggen_dir" rev-parse HEAD)" = "$ggen_sha"

# Chicago edge 3: manufacture and execute the exact production GGen binary.
rustup toolchain install "$rust_toolchain" --profile minimal
cargo +"$rust_toolchain" build --manifest-path "$ggen_dir/Cargo.toml" --locked --release -p ggen-cli-lib --bin ggen
ggen_bin="$ggen_dir/target/release/ggen"
test -x "$ggen_bin"
"$ggen_bin" --help >/dev/null

# Chicago edges 4-6: execute real generation, verify its real receipt, replay it,
# and independently regenerate from a second anonymous consumer.
(
  cd "$work_root/consumer-a/manufacturing"
  "$ggen_bin" sync run
)
test -s "$work_root/consumer-a/manufacturing/generated/capability-lock.json"
test -s "$work_root/consumer-a/manufacturing/generated/autonomic-manufacturing.mmd"
python3 -m json.tool "$work_root/consumer-a/manufacturing/generated/capability-lock.json" >/dev/null
digest_first="$(generated_digest "$work_root/consumer-a")"
receipt_lines_first="$(verify_ggen_receipt_log "$work_root/consumer-a")"
assert_expected_runtime_writes "$work_root/consumer-a"

(
  cd "$work_root/consumer-a/manufacturing"
  "$ggen_bin" sync run
)
digest_replay="$(generated_digest "$work_root/consumer-a")"
test "$digest_replay" = "$digest_first"
receipt_lines_replay="$(verify_ggen_receipt_log "$work_root/consumer-a")"
test "$receipt_lines_replay" -ge "$receipt_lines_first"
assert_expected_runtime_writes "$work_root/consumer-a"

(
  cd "$work_root/consumer-b/manufacturing"
  "$ggen_bin" sync run
)
digest_independent="$(generated_digest "$work_root/consumer-b")"
test "$digest_independent" = "$digest_first"
receipt_lines_independent="$(verify_ggen_receipt_log "$work_root/consumer-b")"
assert_expected_runtime_writes "$work_root/consumer-b"

# Chicago edge 7: malformed real configuration must fail through the real GGen parser.
anonymous_clone "$work_root/malformed"
printf '\n[broken\n' >> "$work_root/malformed/manufacturing/ggen.toml"
set +e
(
  cd "$work_root/malformed/manufacturing"
  "$ggen_bin" sync run
) >"$work_root/malformed.out" 2>&1
malformed_exit=$?
set -e
test "$malformed_exit" -ne 0

# Chicago edge 8: a nonexistent immutable source identity must be refused by real Git transport.
stale_dir="$work_root/stale-ggen"
mkdir -p "$stale_dir"
git -C "$stale_dir" init -q
git -C "$stale_dir" remote add origin "https://github.com/${ggen_repository}.git"
set +e
env -u GITHUB_TOKEN -u GH_TOKEN git -C "$stale_dir" -c credential.helper= fetch -q --depth 1 origin 0000000000000000000000000000000000000000 >"$work_root/stale.out" 2>&1
stale_exit=$?
set -e
test "$stale_exit" -ne 0

os="$(uname -s)"
arch="$(uname -m)"
receipt="$work_root/receipt.json"
python3 - "$receipt" "$SUBJECT_REPOSITORY" "$SUBJECT_SHA" "$SUBJECT_REF" "$ggen_repository" "$ggen_sha" "$rust_toolchain" "$digest_first" "$digest_replay" "$digest_independent" "$receipt_lines_first" "$receipt_lines_replay" "$receipt_lines_independent" "$malformed_exit" "$stale_exit" "$os" "$arch" <<'PY'
import json, sys
(path, repo, sha, ref, ggen_repo, ggen_sha, toolchain, first, replay, independent,
 receipt_first, receipt_replay, receipt_independent, malformed_exit, stale_exit,
 os_name, arch) = sys.argv[1:]
receipt = {
    "schema_version": 1,
    "subject": {"repository": repo, "ref": ref, "sha": sha},
    "bootstrap": {"repository": ggen_repo, "sha": ggen_sha, "rust_toolchain": toolchain},
    "execution": {
        "command": "ggen sync run",
        "first_generation_sha256": first,
        "replay_sha256": replay,
        "independent_consumer_sha256": independent,
        "ggen_receipt_lines_first": int(receipt_first),
        "ggen_receipt_lines_replay": int(receipt_replay),
        "ggen_receipt_lines_independent": int(receipt_independent),
        "malformed_config_exit": int(malformed_exit),
        "stale_sha_fetch_exit": int(stale_exit),
    },
    "environment": {"os": os_name, "arch": arch},
    "standing": "ALIVE",
}
with open(path, "w") as f:
    json.dump(receipt, f, indent=2, sort_keys=True)
    f.write("\n")
PY

# Independent receipt verifier: identity and observed consequences must agree.
python3 - "$receipt" "$SUBJECT_REPOSITORY" "$SUBJECT_SHA" "$ggen_sha" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
assert r["subject"]["repository"] == sys.argv[2]
assert r["subject"]["sha"] == sys.argv[3]
assert r["bootstrap"]["sha"] == sys.argv[4]
e = r["execution"]
assert e["first_generation_sha256"] == e["replay_sha256"] == e["independent_consumer_sha256"]
assert e["ggen_receipt_lines_first"] >= 1
assert e["ggen_receipt_lines_replay"] >= e["ggen_receipt_lines_first"]
assert e["ggen_receipt_lines_independent"] >= 1
assert e["malformed_config_exit"] != 0
assert e["stale_sha_fetch_exit"] != 0
assert r["standing"] == "ALIVE"
PY

printf 'STARTER_JOURNEY_CHICAGO ALIVE subject=%s ggen=%s digest=%s receipts=%s/%s/%s os=%s arch=%s\n' \
  "$SUBJECT_SHA" "$ggen_sha" "$digest_first" "$receipt_lines_first" "$receipt_lines_replay" "$receipt_lines_independent" "$os" "$arch"
