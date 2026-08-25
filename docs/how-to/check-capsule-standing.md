# How to check whether a capsule is ALIVE vs PARTIAL_ALIVE vs BUILD_BROKEN

## The rule that matters most

Workflow existence, a green CI badge, an uploaded artifact, or a file
literally named `receipt.json` do **not** by themselves constitute `ALIVE`.
Only a receipt produced by a real local execution of the exact admitted
subject counts. Every `build-*.sh` script's own `build-receipt.json`
self-labels `standing: ALIVE` for the *construction* phase only — treat that
as construction-only evidence, not capsule-ALIVE. The authoritative receipt
is the one written by the **consumer-side** verify script, from a genuinely
fresh extraction.

## Standing vocabulary (repo-wide)

| State | Meaning | Evidence required |
|---|---|---|
| `UNKNOWN` | Not observed / insufficient evidence | Default state; nothing has run |
| `PARTIAL_ALIVE` | A lower execution boundary passed, requested crown did not | e.g. construction succeeded but consumer replay hasn't run yet; or one component of a multi-part capsule is proven present/parseable but not runtime-executed |
| `ALIVE` | The exact admitted subject executed the exact acceptance command successfully | Real acceptance command exit code 0, captured in a `receipt.json` produced by the *consumer* verify script after a fresh extract |
| `BLOCKED` | An external capability or authority boundary prevented execution | e.g. a required host command missing, `unshare` unavailable, `setpriv` missing for a root consumer, credential can't reach a resource |
| `BUILD_BROKEN` | A manufactured capsule reached execution but violated its contract | version mismatch, digest mismatch, missing manifest keys, non-capsule-local binary, nonzero acceptance exit, non-deterministic regeneration |
| `UNSUPPORTED` | Requested platform/version/capability tuple is outside the admitted matrix | e.g. unknown capsule variant name, non-`linux_x86_64` platform, non-github.com source repository |

## Steps to check a capsule you built or downloaded

1. Locate the archive and its `.sha256` sidecar.
2. Extract into a **fresh** directory — never trust the build workspace:

   ```bash
   rm -rf consumer && mkdir consumer
   tar -xzf <archive.tar.gz> -C consumer
   ```

3. Replay the offline acceptance:

   ```bash
   CAPSULE_ARCHIVE_DIGEST="$(sha256sum <archive.tar.gz> | awk '{print $1}')" \
     bash consumer/scripts/run-offline.sh
   ```

4. Read `consumer/receipt.json` (or `<dest>/receipt.json` for an installed
   capsule). Check the `standing` field and `acceptance_exit_code` — this is
   the real evidence, not the presence of the file.

5. For `postgres17`, the same fresh-consumer discipline applies but the
   acceptance sequence starts a real `pg_ctl` server, runs a CRUD+identity
   SQL lifecycle, and stops it — check that the receipt reflects a completed
   lifecycle, not just process startup.

6. For `autonomic-manufacturing`, the receipt carries **per-component**
   standings rather than one flat value — for example a real run produced
   `ggen_manufacture: ALIVE`, `swarmsh_v1_shell_source: ALIVE`,
   `swarmsh_v2_typed_source: PARTIAL_ALIVE`, with an overall
   `standing: ALIVE` and `do_authority: false`. Read every named component,
   not just the top-level `standing` — a `PARTIAL_ALIVE` component (e.g.
   SwarmSH v2, whose `Cargo.toml` identity is checked but which is never
   compiled or run) is a deliberate, documented distinction, not a defect.

## Automated double-check in CI

`.github/workflows/verify-capsules.yml` triggers on completion of the
`Build Capsules` workflow, downloads the **already-uploaded artifact** (not
the build workspace) for each of the 6 capsule variants, verifies its
sha256, extracts to a fresh `consumer/`, and runs
`consumer/scripts/run-offline.sh` — this is the repo's own automated second
look at transport integrity, separate from the same-run "verify fresh
extracted consumer" step already inside `build-capsules.yml`. Two
independent replay passes happen per push, not one.

## See also

- [Build a capsule from scratch and verify it locally](build-a-capsule.md)
- [Install an already-built capsule in a restricted offline environment](install-capsule-offline.md)
- `docs/reference/` — full status-vocabulary and receipt-field reference
- `docs/explanation/` — why CI is never treated as the crown
