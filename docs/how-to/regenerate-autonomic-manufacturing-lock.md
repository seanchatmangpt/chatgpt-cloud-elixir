# How to run the ggen sync pipeline to regenerate the autonomic-manufacturing capability lock

`manufacturing/generated/capability-lock.json` and the `.mmd` topology
diagram are generated projections of `manufacturing/ontology.ttl` — never
hand-edit them. Edit the ontology (or `manufacturing/ggen.toml`, or a
query/template) and regenerate.

## Steps (matches `.github/workflows/autonomic-manufacturing.yml`)

1. Edit the source of truth, not the generated output:
   - `manufacturing/ontology.ttl` for the capability-source semantics
     (the manufacturing core plus every other admitted ecosystem member).
     Adding or removing a source also means editing
     `capsules/autonomic-manufacturing/capsule.toml` `required_sources`.
     The court refuses any difference between the two.
   - To re-pin already-admitted sources to their live HEADs, run
     `python3 scripts/refresh-capability-sources.py --write`. It rewrites
     only `cc:commitSha` values, plus `versions.toml` `ggen_sha` when ggen
     moves.
   - `manufacturing/ggen.toml` or `manufacturing/queries/`/`manufacturing/templates/`
     for the projection law.
   - `versions.toml [bootstrap]` only for the pinned ggen compiler revision
     itself (`ggen_repository`, `ggen_sha`, `rust_toolchain`) — this is a
     deliberate minimal exception to the ontology-is-canonical rule, needed
     because the ontology can't project the full lock before a ggen
     compiler exists to run it.

2. Qualify the bootstrap contract before touching anything downstream:

   ```bash
   python3 scripts/verify-autonomic-contract.py
   ```

   This refuses on any bootstrap/ontology identity drift.

3. Fetch the pinned ggen commit (exact SHA from `versions.toml
   [bootstrap]`) via a fresh shallow clone, and assert the checked-out SHA
   matches before building.

4. Build ggen from source with the pinned Rust toolchain:

   ```bash
   cargo build --locked --release -p ggen-cli-lib --bin ggen
   ```

5. Run the real sync from inside `manufacturing/`:

   ```bash
   cd manufacturing
   ggen sync run
   ```

   Assert `generated/capability-lock.json` and the `.mmd` topology diagram
   are non-empty afterward.

6. Fetch every source named by `capability-lock.json` at its exact SHA
   with the canonical fetcher (the same script CI runs):

   ```bash
   bash scripts/fetch-capability-sources.sh manufacturing/generated/capability-lock.json .capability-sources
   ```

   It asserts checkout identity for each source and reuses checkouts already
   at the admitted SHA. It applies the ontology's Git LFS law
   (`cc:lfsObjectPolicy "pointer-identity"`): LFS files are bound by their
   pointer blob (sha256 oid + size), which the commit and tree SHA already
   pin, and are never downloaded. The build refuses to stage an LFS pointer
   into shipped content. Never hand-roll a fetch loop, and never substitute
   a facsimile source.

7. Manufacture the capsule and verify a fresh consumer:

   ```bash
   scripts/build-autonomic-manufacturing.sh
   # verify the archive's sha256 against its .sha256 sidecar, then:
   rm -rf consumer && mkdir consumer
   tar -xzf dist/chatgpt-cloud-autonomic-manufacturing-*.tar.gz -C consumer
   bash consumer/scripts/verify-autonomic-manufacturing.sh
   ```

   The consumer verify step re-checks source identity/authority against the
   embedded capability lock, checks the SHA-256 of every
   `sources/<name>.tar.gz` against `manifest.json`, runs `ggen sync run` twice on the bundled
   Vision 2030 package and diffs the generated-file digest for
   determinism, and separately proves concurrent git-worktree fan-out (two
   branches, two worktrees, two parallel commits) as a live SwarmSH
   substrate falsifier, before writing `receipt.json` with per-component
   standings.

## Determinism check

If two consecutive `ggen sync run` invocations on the same input produce
different generated-file digests, that is `BUILD_BROKEN` —
non-deterministic regeneration is treated as a defect, not noise.

## Authority ceiling — read before running

This entire surface is `SELECT / CONSTRUCT / VERIFY` only.
`CONSTRUCT_VERIFY` is the maximum authority ceiling. No ontology, generated
manifest, capsule, or receipt from this pipeline may grant cloud
credentials, repository merge authority, external API authority, or any
consequential `DO`. The receipt's `do_authority` field is `false`.

## See also

- [Build a capsule from scratch and verify it locally](build-a-capsule.md)
- [Install an already-built capsule in a restricted offline environment](install-capsule-offline.md)
- `docs/reference/` — full `capsule.toml` schema for `autonomic-manufacturing`
- `docs/explanation/` — the SELECT/CONSTRUCT/DO authority model, and why
  SwarmSH v1 and v2 are deliberately never collapsed into one claim
