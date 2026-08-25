#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/activate"

for cmd in bash python3 git sha256sum; do
  command -v "$cmd" >/dev/null || { echo "BLOCKED: consumer command '$cmd' missing" >&2; exit 69; }
done
[[ -x "$ROOT/bin/ggen" ]] || { echo "BUILD_BROKEN: ggen binary missing" >&2; exit 65; }
[[ -f "$ROOT/contract/capability-lock.json" ]] || { echo "BUILD_BROKEN: capability lock missing" >&2; exit 65; }
[[ -f "$ROOT/swarmsh/coordination_helper.sh" ]] || { echo "BUILD_BROKEN: SwarmSH v1 coordination helper missing" >&2; exit 65; }
[[ -f "$ROOT/swarmsh-v2/Cargo.toml" ]] || { echo "BUILD_BROKEN: SwarmSH v2 typed source missing" >&2; exit 65; }
[[ -d "$ROOT/capital/ggen-marketplace/packs/ggen-combinatorial-maximalism-pack" ]] || { echo "BUILD_BROKEN: DfCM marketplace capital missing" >&2; exit 65; }
[[ -d "$ROOT/capital/ggen-marketplace/packages/vision-2030-capability-generator" ]] || { echo "BUILD_BROKEN: Vision 2030 marketplace capital missing" >&2; exit 65; }

"$ROOT/bin/ggen" --help >/dev/null
bash -n "$ROOT/swarmsh/coordination_helper.sh"
bash -n "$ROOT/swarmsh/real_agent_coordinator.sh"

python3 - "$ROOT/contract/capability-lock.json" "$ROOT/swarmsh-v2/Cargo.toml" <<'PY'
import json, re, sys, tomllib
lock = json.load(open(sys.argv[1]))
if lock.get("release") != "26.8.25" or lock.get("authority_ceiling") != "CONSTRUCT_VERIFY":
    raise SystemExit("BUILD_BROKEN: generated lock identity/authority drift")
sources = {s["name"]: s for s in lock.get("sources", [])}
expected = {"ggen", "ggen-marketplace", "ggen-create", "ggen-legacy", "ggen-spec-kit", "swarmsh", "swarmsh-v2"}
if set(sources) != expected:
    raise SystemExit(f"BUILD_BROKEN: capability source set drift: {sorted(sources)}")
for source in sources.values():
    if not re.fullmatch(r"[0-9a-f]{40}", source["sha"]):
        raise SystemExit(f"BUILD_BROKEN: invalid exact SHA for {source['name']}")
v2 = tomllib.load(open(sys.argv[2], "rb"))
if v2.get("package", {}).get("name") != "swarmsh-v2" or v2.get("package", {}).get("version") != "2.1.0":
    raise SystemExit("BUILD_BROKEN: SwarmSH v2 source identity drift")
print("CAPABILITY_LOCK=ALIVE sources=7 authority=CONSTRUCT_VERIFY")
PY

# Prove the imported ggen runtime can manufacture a real marketplace package twice.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp -a "$ROOT/capital/ggen-marketplace/packages/vision-2030-capability-generator" "$TMP/vision"
(
  cd "$TMP/vision"
  "$ROOT/bin/ggen" sync run >/tmp/ggen-vision-first.log
)
[[ -f "$TMP/vision/generated/VISION_2030.md" ]] || { echo "BUILD_BROKEN: ggen Vision 2030 projection missing" >&2; exit 65; }
[[ -f "$TMP/vision/generated/capability-index.json" ]] || { echo "BUILD_BROKEN: ggen capability index missing" >&2; exit 65; }
first="$(find "$TMP/vision/generated" -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
(
  cd "$TMP/vision"
  "$ROOT/bin/ggen" sync run >/tmp/ggen-vision-second.log
)
second="$(find "$TMP/vision/generated" -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
[[ "$first" == "$second" ]] || { echo "BUILD_BROKEN: repeated ggen manufacture changed generated digest" >&2; exit 65; }

# Prove the Unix substrate that SwarmSH v1 operationalizes: independent worktrees + concurrent workers.
mkdir -p "$TMP/swarm-test"
git -C "$TMP/swarm-test" init -q
git -C "$TMP/swarm-test" config user.email cloud-capsule@example.invalid
git -C "$TMP/swarm-test" config user.name cloud-capsule
echo seed > "$TMP/swarm-test/state.txt"
git -C "$TMP/swarm-test" add state.txt
git -C "$TMP/swarm-test" commit -qm seed
git -C "$TMP/swarm-test" branch cell-a
git -C "$TMP/swarm-test" branch cell-b
git -C "$TMP/swarm-test" worktree add -q "$TMP/cell-a" cell-a
git -C "$TMP/swarm-test" worktree add -q "$TMP/cell-b" cell-b
(
  cd "$TMP/cell-a"
  echo A > result.txt
  git add result.txt
  git commit -qm cell-a
) &
pid_a=$!
(
  cd "$TMP/cell-b"
  echo B > result.txt
  git add result.txt
  git commit -qm cell-b
) &
pid_b=$!
wait "$pid_a"
wait "$pid_b"
[[ "$(cat "$TMP/cell-a/result.txt")" == A && "$(cat "$TMP/cell-b/result.txt")" == B ]] || { echo "BUILD_BROKEN: concurrent worktree fanout failed" >&2; exit 65; }

MANIFEST_SHA="$(sha256sum "$ROOT/manifest.json" | awk '{print $1}')"
LOCK_SHA="$(sha256sum "$ROOT/contract/capability-lock.json" | awk '{print $1}')"
GGEN_SHA="$(sha256sum "$ROOT/bin/ggen" | awk '{print $1}')"
VERIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "$ROOT/receipt.json" <<EOF
{
  "schema_version": 1,
  "phase": "consumer-replay",
  "capsule_name": "autonomic-manufacturing",
  "release_version": "26.8.25",
  "manifest_sha256": "$MANIFEST_SHA",
  "capability_lock_sha256": "$LOCK_SHA",
  "ggen_binary_sha256": "$GGEN_SHA",
  "vision2030_generated_digest": "$second",
  "ggen_manufacture": "ALIVE",
  "swarmsh_v1_shell_source": "ALIVE",
  "swarmsh_process_worktree_substrate": "ALIVE",
  "swarmsh_v2_typed_source": "PARTIAL_ALIVE",
  "authority_ceiling": "CONSTRUCT_VERIFY",
  "do_authority": false,
  "standing": "ALIVE",
  "verified_at": "$VERIFIED_AT",
  "replay": "bash scripts/verify-autonomic-manufacturing.sh"
}
EOF

echo "AUTONOMIC_MANUFACTURING=ALIVE ggen=$second worktree_fanout=ALIVE swarmsh_v2=PARTIAL_ALIVE"
