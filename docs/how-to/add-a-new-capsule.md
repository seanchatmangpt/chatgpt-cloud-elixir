# How to add a new capsule variant

Use this when a target project needs a specific version-pin combination not
covered by an existing capsule (`beam-core`, `ash-core`, `ash-postgres`,
`ash-phoenix`, `ash-full`, `postgres17`, `process-intelligence`,
`autonomic-manufacturing`).

## Steps

1. Pin any new package/runtime versions in `versions.toml` first — this file
   is the canonical version-selection surface. Add entries under
   `[packages]` (Ash-ecosystem packages), `[runtime]` (OTP/Elixir, if this
   capsule needs a different pin than the default), or `[services]` (for a
   service capsule).

2. Create `capsules/<name>/capsule.toml`. For a Mix/Elixir-runtime capsule,
   follow the shape used by `ash-core`, `ash-postgres`, etc.:

   ```toml
   schema_version = 1
   name = "<name>"                     # must match the directory name
   description = "..."
   fixture = "ash_ets_smoke"           # or "mix_smoke" — dir under fixtures/
   packages = ["ash", "spark", "..."]  # keys into versions.toml [packages]
   required_modules = ["Ash", "Spark", "..."]  # asserted loadable in generated test
   requires_services = []              # e.g. ["postgresql"] for a Postgres-dependent capsule
   acceptance = [
     "MIX_ENV=test mix compile --warnings-as-errors",
     "MIX_ENV=test mix test"
   ]
   ```

   For a service capsule, follow the `postgres17` shape instead (see
   `docs/reference/` for the full field list): `kind = "service"`,
   `version_key`, `source_url_template`, `source_sha256`, `configure`,
   `listen`, `default_port`, `acceptance`.

3. If the capsule needs a fixture project not already covered by
   `fixtures/mix_smoke/` or `fixtures/ash_ets_smoke/`, add a new fixture
   directory under `fixtures/<name>/` with `lib/` and `test/` source — do
   **not** check in a `mix.exs`; `build-capsule.sh` generates one at build
   time from `capsule.toml`'s `packages`/`required_modules` list.

4. Register the new variant so CI picks it up:
   - For a Mix-runtime capsule, add it to the matrix in
     `.github/workflows/build-capsules.yml` and
     `.github/workflows/verify-capsules.yml` (the latter also needs the
     correct `otpNN-elixirX.Y.Z` artifact-name pin).
   - For a service capsule, follow `.github/workflows/build-service-capsules.yml`
     instead.

5. Build and verify it locally before pushing, using the same
   fresh-extracted-consumer discipline as any existing capsule — see
   [Build a capsule from scratch and verify it locally](build-a-capsule.md).

6. Per the repo's own git-workflow convention: purpose-branch from an exact
   base, make an intentional commit, push non-force, open a draft PR, and do
   not merge unless explicitly instructed otherwise.

## Naming and identity discipline

- The `name` field in `capsule.toml` must match its directory name — this is
  asserted, not just conventional.
- Never hand-edit generated archives, manifests, or receipts. If something
  generated looks wrong, fix the source (`versions.toml`, `capsule.toml`,
  the build script) and regenerate.

## See also

- [Build a capsule from scratch and verify it locally](build-a-capsule.md)
- `docs/reference/` — full `capsule.toml`/`versions.toml` field reference
- `docs/explanation/` — why `process-intelligence` deliberately pins a
  different BEAM version than every other capsule (preserve-alternatives
  discipline under real compiler-warning pressure)
