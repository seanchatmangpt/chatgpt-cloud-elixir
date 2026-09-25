#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="${CAPABILITY_SOURCE_ROOT:-$ROOT/.capability-sources}"
OUTPUT_DIR="${CAPSULE_OUTPUT_DIR:-$ROOT/dist}"
BUILD_ROOT="${CAPSULE_BUILD_ROOT:-$ROOT/.capsule-build/autonomic-manufacturing}"
LOCK="$ROOT/manufacturing/generated/capability-lock.json"
CAPSULE_CONFIG="$ROOT/capsules/autonomic-manufacturing/capsule.toml"
VERSIONS="$ROOT/versions.toml"
GGEN_BIN="${GGEN_BIN:-$SOURCE_ROOT/ggen/target/release/ggen}"
# full: ship every source-snapshot member as an archive (maximal offline closure).
# identity: bind every member by commit + tree SHA only; git transports the sources.
PROFILE="${AUTONOMIC_SOURCE_PROFILE:-full}"
[[ "$PROFILE" == full || "$PROFILE" == identity ]] || { echo "UNSUPPORTED: AUTONOMIC_SOURCE_PROFILE=$PROFILE" >&2; exit 64; }

for cmd in bash python3 git tar gzip sha256sum; do
  command -v "$cmd" >/dev/null || { echo "BLOCKED: required build command '$cmd' missing" >&2; exit 69; }
done
[[ -x "$GGEN_BIN" ]] || { echo "BUILD_BROKEN: pinned ggen binary missing at $GGEN_BIN" >&2; exit 65; }
[[ -f "$LOCK" ]] || { echo "BUILD_BROKEN: ggen capability lock not manufactured" >&2; exit 65; }

python3 "$ROOT/scripts/verify-autonomic-contract.py"

# The generated lock is authoritative after the bootstrap court and real ggen projection.
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT"
python3 - "$LOCK" "$SOURCE_ROOT" "$BUILD_ROOT/source-identities.json" <<'PY'
import json, pathlib, subprocess, sys
lock = json.load(open(sys.argv[1]))
root = pathlib.Path(sys.argv[2])
identities = {}
for src in lock["sources"]:
    path = root / src["name"]
    if not path.is_dir():
        if src.get("access_class") == "private" and src["execution_mode"] == "source-reference":
            # Typed, not hidden: the admitted SHA stands, construction could not verify it.
            identities[src["name"]] = {"sha": src["sha"], "tree_sha": None, "execution_mode": src["execution_mode"],
                                       "access_class": "private", "lfs_pointer_files": None,
                                       "standing": "BLOCKED", "reason": "IRREDUCIBLE_AUTHORITY: private source, no read credential at construction"}
            continue
        raise SystemExit(f"BUILD_BROKEN: source checkout missing: {path}")
    got = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    if got != src["sha"]:
        raise SystemExit(f"BUILD_BROKEN: {src['name']} expected {src['sha']} observed {got}")
    tree = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD^{tree}"], text=True).strip()
    # LFS-tracked files are bound by their pointer blob (cc:lfsObjectPolicy "pointer-identity").
    lfs = subprocess.run(["git", "-C", str(path), "grep", "-l", "-e", "^version https://git-lfs.github.com/spec/v1$", "HEAD"],
                         capture_output=True, text=True).stdout.splitlines()
    identities[src["name"]] = {"sha": got, "tree_sha": tree, "execution_mode": src["execution_mode"],
                               "access_class": src.get("access_class", "public"), "lfs_pointer_files": len(lfs),
                               "standing": "ALIVE"}
json.dump(identities, open(sys.argv[3], "w"), indent=2, sort_keys=True)
blocked = sorted(n for n, i in identities.items() if i["standing"] == "BLOCKED")
print(f"SOURCE_IDENTITY={'PARTIAL_ALIVE' if blocked else 'ALIVE'} count={len(lock['sources'])} verified={len(identities) - len(blocked)} blocked_private={blocked}")
PY

mkdir -p "$BUILD_ROOT/capsule/bin" "$BUILD_ROOT/capsule/capital" "$BUILD_ROOT/capsule/sources" \
  "$BUILD_ROOT/capsule/scripts" "$BUILD_ROOT/capsule/contract" "$OUTPUT_DIR"
STAGE="$BUILD_ROOT/capsule"

cp "$GGEN_BIN" "$STAGE/bin/ggen"
chmod +x "$STAGE/bin/ggen"
cp "$LOCK" "$STAGE/contract/capability-lock.json"
cp "$ROOT/manufacturing/generated/autonomic-manufacturing.mmd" "$STAGE/contract/autonomic-manufacturing.mmd"
cp "$CAPSULE_CONFIG" "$STAGE/contract/capsule.toml"
cp "$VERSIONS" "$STAGE/contract/versions.toml"
cp "$ROOT/scripts/verify-autonomic-manufacturing.sh" "$STAGE/scripts/"
chmod +x "$STAGE/scripts/verify-autonomic-manufacturing.sh"

# Marketplace capital is included in executable form, not only as a source receipt.
mkdir -p "$STAGE/capital/ggen-marketplace/packs" "$STAGE/capital/ggen-marketplace/packages"
cp -a "$SOURCE_ROOT/ggen-marketplace/packs/ggen-combinatorial-maximalism-pack" \
  "$STAGE/capital/ggen-marketplace/packs/"
cp -a "$SOURCE_ROOT/ggen-marketplace/packages/vision-2030-capability-generator" \
  "$STAGE/capital/ggen-marketplace/packages/"

# SwarmSH v1 is the working shell/process ancestry. v2 is preserved as typed source ancestry.
mkdir -p "$STAGE/swarmsh" "$STAGE/swarmsh-v2"
git -C "$SOURCE_ROOT/swarmsh" archive HEAD | tar -x -C "$STAGE/swarmsh"
git -C "$SOURCE_ROOT/swarmsh-v2" archive HEAD | tar -x -C "$STAGE/swarmsh-v2"

# Every other source-snapshot member of the admitted ecosystem ships as an exact source
# archive. The marketplace is excluded because its capital is staged above in executable form.
python3 - "$LOCK" > "$BUILD_ROOT/source-snapshots.txt" <<'PY'
import json, sys
for src in json.load(open(sys.argv[1]))["sources"]:
    if src["execution_mode"] == "source-snapshot" and src["name"] != "ggen-marketplace":
        print(src["name"])
PY
[[ "$PROFILE" == full ]] || : > "$BUILD_ROOT/source-snapshots.txt"
: > "$BUILD_ROOT/source-archives.tsv"
while IFS= read -r name; do
  git -C "$SOURCE_ROOT/$name" archive --format=tar HEAD | gzip -n > "$STAGE/sources/$name.tar.gz"
  printf '%s\t%s\n' "$name" "$(sha256sum "$STAGE/sources/$name.tar.gz" | awk '{print $1}')" >> "$BUILD_ROOT/source-archives.tsv"
done < "$BUILD_ROOT/source-snapshots.txt"

# Shipped content must be real bytes, never an unmaterialized LFS pointer.
LFS_IN_STAGE="$(grep -rlx --binary-files=without-match 'version https://git-lfs.github.com/spec/v1' "$STAGE" || true)"
if [[ -n "$LFS_IN_STAGE" ]]; then
  echo "BUILD_BROKEN: Git LFS pointer staged into shipped content (content would be a stub):" >&2
  printf '%s\n' "$LFS_IN_STAGE" | sed "s#^$STAGE/#  #" >&2
  exit 65
fi

cat > "$STAGE/activate" <<'EOF'
#!/usr/bin/env bash
CAPSULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CAPSULE_ROOT
export GGEN_MARKETPLACE_ROOT="$CAPSULE_ROOT/capital/ggen-marketplace"
export SWARMSH_ROOT="$CAPSULE_ROOT/swarmsh"
export SWARMSH_V2_ROOT="$CAPSULE_ROOT/swarmsh-v2"
export PATH="$CAPSULE_ROOT/bin:$CAPSULE_ROOT/swarmsh:$PATH"
EOF
chmod +x "$STAGE/activate"

SOURCE_SHA="${GITHUB_SHA:-unknown}"
RELEASE_VERSION="$(python3 -c 'import tomllib; print(tomllib.load(open("'"$VERSIONS"'","rb"))["release"]["version"])')"
LOCK_SHA="$(sha256sum "$LOCK" | awk '{print $1}')"
GGEN_SHA="$(sha256sum "$STAGE/bin/ggen" | awk '{print $1}')"
BUILT_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export SOURCE_SHA RELEASE_VERSION LOCK_SHA GGEN_SHA BUILT_AT PROFILE
python3 - "$STAGE/manifest.json" "$LOCK" "$BUILD_ROOT/source-archives.tsv" "$BUILD_ROOT/source-identities.json" <<'PY'
import json, os, sys
lock = json.load(open(sys.argv[2]))
source_archives = dict(line.rstrip("\n").split("\t") for line in open(sys.argv[3]) if line.strip())
source_identities = json.load(open(sys.argv[4]))
manifest = {
    "schema_version": 1,
    "capsule_name": "autonomic-manufacturing",
    "release_version": os.environ["RELEASE_VERSION"],
    "source_repository": "seanchatmangpt/chatgpt-cloud-elixir",
    "source_sha": os.environ["SOURCE_SHA"],
    "built_at": os.environ["BUILT_AT"],
    "platform": {"os": "linux", "arch": "x86_64"},
    "authority_ceiling": "CONSTRUCT_VERIFY",
    "do_authority": False,
    "capability_lock_sha256": os.environ["LOCK_SHA"],
    "ggen_binary_sha256": os.environ["GGEN_SHA"],
    "sources": lock["sources"],
    "source_profile": os.environ["PROFILE"],
    "source_identities": source_identities,
    "source_archives": {
        name: {"path": f"sources/{name}.tar.gz", "sha256": digest}
        for name, digest in sorted(source_archives.items())
    },
    "standing": "PARTIAL_ALIVE",
    "standing_note": "Construction is observed; fresh consumer replay is required for ALIVE. Source archives prove exact-source presence only. SwarmSH v2 remains source-bound typed ancestry."
}
with open(sys.argv[1], "w") as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
    f.write("\n")
PY

MANIFEST_SHA="$(sha256sum "$STAGE/manifest.json" | awk '{print $1}')"
cat > "$STAGE/build-receipt.json" <<EOF
{
  "schema_version": 1,
  "phase": "construct",
  "source_sha": "$SOURCE_SHA",
  "release_version": "$RELEASE_VERSION",
  "capsule_name": "autonomic-manufacturing",
  "manifest_sha256": "$MANIFEST_SHA",
  "capability_lock_sha256": "$LOCK_SHA",
  "ggen_binary_sha256": "$GGEN_SHA",
  "standing": "PARTIAL_ALIVE",
  "note": "Exact source closure and construction observed; consumer replay remains required."
}
EOF

NAME="chatgpt-cloud-autonomic-manufacturing-${RELEASE_VERSION}-linux-x86_64"
[[ "$PROFILE" == full ]] || NAME="chatgpt-cloud-autonomic-manufacturing-${RELEASE_VERSION}-${PROFILE}-linux-x86_64"
ARCHIVE="$OUTPUT_DIR/$NAME.tar.gz"
(
  cd "$STAGE"
  tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 --numeric-owner -cf - . | gzip -n > "$ARCHIVE"
)
ARCHIVE_SHA="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
printf '%s  %s\n' "$ARCHIVE_SHA" "$(basename "$ARCHIVE")" > "$ARCHIVE.sha256"
printf '%s\n' "$ARCHIVE"
