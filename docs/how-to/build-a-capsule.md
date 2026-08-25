# How to build a capsule from scratch and verify it locally

This guide covers building one of the existing Mix/Elixir-runtime capsules
(`beam-core`, `ash-core`, `ash-postgres`, `ash-phoenix`, `ash-full`) and
proving it works by replaying its acceptance command against a **fresh
extracted consumer** — never the build workspace.

## Prerequisites

- `erl`, `elixir`, `mix`, `python3`, `tar`, `gzip`, `sha256sum` on `PATH`
- Versions matching `versions.toml`'s `[runtime]` table (`otp`, `elixir`), or
  set `CAPSULE_OTP_OVERRIDE` / `CAPSULE_ELIXIR_OVERRIDE`

## Steps

1. Make the scripts executable:

   ```bash
   chmod +x scripts/*.sh
   ```

2. Bind the capsule identity to the exact commit under proposal (CI does
   this for every PR too):

   ```bash
   export GITHUB_SHA="$(git rev-parse HEAD)"
   ```

3. Build the capsule. Replace `ash-core` with `beam-core`, `ash-postgres`,
   `ash-phoenix`, or `ash-full` as needed:

   ```bash
   scripts/build-capsule.sh ash-core
   ```

   This generates a `mix.exs` on the fly from `capsules/ash-core/capsule.toml`'s
   `packages`/`required_modules` list, stages it onto the fixture project
   (`fixtures/ash_ets_smoke/`), runs `mix deps.get`, then
   `MIX_ENV=test mix compile --warnings-as-errors` and `MIX_ENV=test mix test`
   against it, then copies the real OTP/Elixir/Mix/Hex/Rebar tree, the built
   project, scripts, verifier, and `source/{capsule,versions}.toml` into
   `dist/chatgpt-cloud-elixir-ash-core-otp29-elixir1.20.2-linux-x86_64.tar.gz`
   plus a `.sha256` sidecar. The archive path is printed on stdout.

4. Verify a **fresh extracted consumer** — this is the step that actually
   counts as evidence, per the repo's own doctrine (a build workspace pass is
   not sufficient):

   ```bash
   archive="$(ls dist/chatgpt-cloud-elixir-ash-core-*.tar.gz)"
   rm -rf consumer && mkdir consumer
   tar -xzf "$archive" -C consumer
   CAPSULE_ARCHIVE_DIGEST="$(sha256sum "$archive" | awk '{print $1}')" \
     bash consumer/scripts/run-offline.sh
   ```

   `run-offline.sh` forces UTF-8 filename handling
   (`ELIXIR_ERL_OPTIONS=+fnu`), tries `unshare -n` (real network-namespace
   isolation) to prove there is no accidental network dependency, falls back
   to a loopback-only proxy fence (`HTTP_PROXY=http://127.0.0.1:9`) if
   `unshare` is unavailable, then execs `scripts/verify-capsule.sh`, which:

   1. Runs `elixir verifier/verify_manifest.exs manifest.json` — checks
      required manifest keys and a valid `[release] version`.
   2. Runs `elixir verifier/verify_runtime.exs manifest.json` — asserts the
      observed OTP/Elixir match `manifest.json`'s expected values **and**
      that `erl`/`elixir`/`mix` resolve to capsule-local paths, not a
      host-installed BEAM.
   3. Runs the real acceptance:
      `cd project && MIX_ENV=test mix compile --warnings-as-errors && MIX_ENV=test mix test`.
   4. Writes `receipt.json` with `standing = ALIVE` (exit 0) or
      `BUILD_BROKEN` (nonzero), binding `source_sha`, `release_version`,
      `capsule_name`, `capsule_archive_sha256`, `manifest_sha256`,
      `network_mode`, `acceptance_command`, `acceptance_exit_code`,
      `verified_at`, and a `replay` command string.

## Important: two different receipts, don't confuse them

- `build-receipt.json` (written by `build-capsule.sh` during construction)
  **always** self-labels `standing: ALIVE` for the build step, regardless of
  whether a real consumer can use the result. Treat this as
  construction-only evidence.
- `receipt.json` (written by `consumer/scripts/verify-capsule.sh`, step 4
  above) is the one produced from a genuinely fresh extraction with a real
  computed standing — this is the receipt the repo's own doctrine treats as
  authoritative.

## Other capsule types (different build/verify scripts)

- `postgres17` (service capsule): `scripts/build-postgres-capsule.sh` +
  `scripts/verify-postgres-capsule.sh` — the verify step actually starts a
  real `pg_ctl`-managed server on `127.0.0.1:55432` and runs a
  CRUD+identity SQL lifecycle before stopping it.
- `process-intelligence`: `scripts/build-process-intelligence.sh` +
  `capsules/process-intelligence/verify-capsule.sh` — see
  [Qualify an external repo against the process-intelligence capsule](qualify-external-repo-process-intelligence.md).
- `autonomic-manufacturing`: see
  [Run the ggen sync pipeline to regenerate the autonomic-manufacturing capability lock](regenerate-autonomic-manufacturing-lock.md).

## See also

- [Install an already-built capsule in a restricted offline environment](install-capsule-offline.md)
- [Check whether a capsule is ALIVE vs PARTIAL_ALIVE vs BUILD_BROKEN](check-capsule-standing.md)
- [Add a new capsule variant](add-a-new-capsule.md)
- `docs/reference/` — full `capsule.toml`/`versions.toml` schema reference
- `docs/explanation/` — why CI is never the crown (offline law, authority model)
