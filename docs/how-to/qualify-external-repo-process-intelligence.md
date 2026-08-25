# How to qualify an external repo against the process-intelligence capsule

The `process-intelligence` capsule qualifies that a black-box OCEL bridge
(AshR2RML validates/reconstructs an event log → ex4pm ingests it, discovers
a DFG, runs conformance, simulates) reproduces exact expected results
(event/object parity, exact DFG edges, fitness `1.0`, `ALIVE` standings,
expected simulation language) inside a restricted, no-network container.

This capsule is offline-only and deliberately separate from
`control-plane/` — different runtime (OTP 27.2.4 / Elixir 1.18.4, not the
29.0 / 1.20.2 used by every other capsule), different subjects
(`ash_r2rml` and `ex4pm`, two independently-built Mix projects that are
never merged into one dependency graph).

## Steps

1. Pin the two external subjects in `capsules/process-intelligence/capsule.toml`
   under `[subjects.<name>]` — **both** a commit SHA and a tree SHA:

   ```toml
   [subjects.ash_r2rml]
   repository = "https://github.com/seanchatmangpt/ash_r2rml.git"
   sha = "a14b08db7960..."
   tree_sha = "65f7e5b66cac..."
   build_acceptance = ["MIX_ENV=test mix compile --warnings-as-errors", "MIX_ENV=test mix test test/fortune5/"]
   consumer_acceptance = [ ... ]
   ```

   The build script independently verifies both SHAs after
   `git checkout --detach FETCH_HEAD` — this guards against a
   rewritten-but-same-hash-looking ref, or a commit whose tree drifted from
   what was reviewed. Adding or updating a subject means updating both
   fields together.

2. Build the capsule:

   ```bash
   scripts/build-process-intelligence.sh
   ```

   This cross-checks the capsule's own `[runtime]` OTP/Elixir pins against
   `versions.toml`, builds the `mix_smoke`-based base, and checks out each
   pinned external subject at its exact commit+tree.

3. Verify per-subject acceptance:
   - `ash_r2rml`: `MIX_ENV=test mix compile --warnings-as-errors` and
     `mix test test/fortune5/`
   - `ex4pm`: `mix verify`
   - bridge integration: `bash harness/verify.sh`

4. Verify a fresh extracted consumer, same discipline as any other capsule:

   ```bash
   capsules/process-intelligence/verify-capsule.sh
   ```

## Scope boundary — read before reporting standing

`ALIVE` here proves only the offline in-memory crown. It does **not**
manufacture standing for `control-plane/`'s Postgres/Docker/Fly-hosted
crown, and `control-plane/` never runs inside or depends on this capsule.
The capsule's own `process_lab` config names its external crowns
explicitly as *not* proven by this capsule: `postgresql`, `ontop`, `docker`.
Do not report a passing `process-intelligence` run as evidence for any of
those three.

## Why this capsule pins a different BEAM version

A real attempted qualification on OTP 29 / Elixir 1.20 (the pin every other
capsule uses) reached compilation but was falsified by new 1.20 compiler
warnings under the required `--warnings-as-errors` gate against `ash_r2rml`/
`ex4pm`. Rather than weakening the warnings gate, the repo kept both as
separate lawful capsule variants — preserve alternatives, don't collapse
them to force compatibility.

## See also

- [Build a capsule from scratch and verify it locally](build-a-capsule.md)
- [Check whether a capsule is ALIVE vs PARTIAL_ALIVE vs BUILD_BROKEN](check-capsule-standing.md)
- `docs/reference/` — full `[subjects.*]`/`[process_lab]` schema
- `docs/explanation/` — Chesterton's-fence / preserve-alternatives doctrine
