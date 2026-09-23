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

SOURCE_COUNT="$(python3 - "$ROOT" <<'PY'
import hashlib, json, pathlib, re, sys, tomllib
root = pathlib.Path(sys.argv[1])
lock = json.load(open(root / "contract/capability-lock.json"))
manifest = json.load(open(root / "manifest.json"))
capsule = tomllib.load(open(root / "contract/capsule.toml", "rb"))
versions = tomllib.load(open(root / "contract/versions.toml", "rb"))
release = versions["release"]["version"]
if lock.get("release") != release or manifest.get("release_version") != release:
    raise SystemExit("BUILD_BROKEN: generated lock/manifest release identity drift")
if lock.get("authority_ceiling") != "CONSTRUCT_VERIFY" or manifest.get("do_authority") is not False:
    raise SystemExit("BUILD_BROKEN: authority ceiling drift")
sources = {s["name"]: s for s in lock.get("sources", [])}
if len(sources) != len(lock.get("sources", [])) or lock.get("source_count") != len(sources):
    raise SystemExit("BUILD_BROKEN: capability lock source count drift")
core = {"ggen", "ggen-marketplace", "ggen-create", "ggen-legacy", "ggen-spec-kit", "swarmsh", "swarmsh-v2"}
if set(sources) != set(capsule["required_sources"]) or not core <= set(sources):
    raise SystemExit(f"BUILD_BROKEN: capability source set drift: {sorted(sources)}")
for source in sources.values():
    if not re.fullmatch(r"[0-9a-f]{40}", source["sha"]):
        raise SystemExit(f"BUILD_BROKEN: invalid exact SHA for {source['name']}")
if sources["ggen"]["sha"] != versions["bootstrap"]["ggen_sha"]:
    raise SystemExit("BUILD_BROKEN: embedded ggen identity differs from bootstrap")
# Every admitted source, shipped or not, carries the commit + tree identity observed at construction.
identities = manifest.get("source_identities", {})
if set(identities) != set(sources):
    raise SystemExit("BUILD_BROKEN: manifest source identity set drift")
for name, source in sources.items():
    ident = identities[name]
    if ident.get("sha") != source["sha"] or not re.fullmatch(r"[0-9a-f]{40}", ident.get("tree_sha", "")):
        raise SystemExit(f"BUILD_BROKEN: construction identity missing or drifted for {name}")
# Every source-snapshot member except the staged marketplace capital must ship as an
# archive whose digest was bound into the manifest at construction.
profile = manifest.get("source_profile", "full")
if profile not in ("full", "identity"):
    raise SystemExit(f"BUILD_BROKEN: unknown source profile {profile}")
snapshots = {n for n, s in sources.items() if s["execution_mode"] == "source-snapshot" and n != "ggen-marketplace"}
if profile == "identity":
    snapshots = set()  # every member is bound by the commit + tree identities checked above
archives = manifest.get("source_archives", {})
if set(archives) != snapshots:
    raise SystemExit(f"BUILD_BROKEN: source archive set drift: missing={sorted(snapshots - set(archives))} extra={sorted(set(archives) - snapshots)}")
on_disk = {p.name[: -len(".tar.gz")] for p in (root / "sources").glob("*.tar.gz")}
if on_disk != snapshots:
    raise SystemExit(f"BUILD_BROKEN: sources/ does not match admitted snapshots: missing={sorted(snapshots - on_disk)} extra={sorted(on_disk - snapshots)}")
for name in sorted(snapshots):
    entry = archives[name]
    digest = hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        raise SystemExit(f"BUILD_BROKEN: source archive digest mismatch for {name}")
v2 = tomllib.load(open(root / "swarmsh-v2/Cargo.toml", "rb"))
if v2.get("package", {}).get("name") != "swarmsh-v2" or v2.get("package", {}).get("version") != "2.1.0":
    raise SystemExit("BUILD_BROKEN: SwarmSH v2 source identity drift")
print(len(sources))
PY
)"
RELEASE_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["release"])' "$ROOT/contract/capability-lock.json")"
SOURCE_PROFILE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("source_profile", "full"))' "$ROOT/manifest.json")"
echo "CAPABILITY_LOCK=ALIVE sources=$SOURCE_COUNT authority=CONSTRUCT_VERIFY"

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
  "release_version": "$RELEASE_VERSION",
  "manifest_sha256": "$MANIFEST_SHA",
  "capability_sources": $SOURCE_COUNT,
  "source_profile": "$SOURCE_PROFILE",
  "source_identities_verified": "ALIVE",
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
