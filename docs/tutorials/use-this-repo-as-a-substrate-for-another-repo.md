# Tutorial: Use This Repo as Execution Infrastructure for a Different Target Repo

`chatgpt-cloud-elixir` isn't only a project that manufactures and verifies its own
capsules — it's also a portable execution-infrastructure package that a
Hex/apt/DNS-restricted ChatGPT (or other agent) session can pull in to unblock
BEAM work on a completely different, unrelated repository. This tutorial walks
through that pattern concretely, using a placeholder target repo. Substitute your
own target repository's name and requirements wherever `<TARGET_REPO>` appears.

This pattern is documented in this repository's own `README.md` "Quick start for
ChatGPT users" section as a copy-pasteable prompt template; this tutorial expands
it into concrete steps you can actually run.

## Prerequisites

- You (or the agent session you're driving) can read this repository
  (`chatgpt-cloud-elixir`) at its current `main` HEAD — clone it or access it via
  a connected GitHub interface.
- You can inspect `<TARGET_REPO>` — its own `AGENTS.md`/`README.md` (if present),
  its Mix project structure, and its CI, to learn what BEAM toolchain versions and
  Ash/Ecto/Phoenix dependencies it actually needs.
- You're running in a container that can execute native Linux binaries but cannot
  reliably reach Hex or apt (the exact restriction this repo exists to route
  around). If your container has normal network access, you likely don't need
  this pattern at all — just `mix deps.get` directly in `<TARGET_REPO>`.

## Step 1: Read this repo's doctrine at its current SHA

```bash
cd chatgpt-cloud-elixir
git rev-parse HEAD
```

Read `AGENTS.md` and `README.md` at that exact commit before doing anything else
— they state the authority model (`GitHub Actions is never the crown — the crown
is execution of the exact admitted capsule in the consuming environment`) and the
standing vocabulary (`UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN |
UNSUPPORTED`) that governs every claim you'll make about whether this worked.

## Step 2: Inspect the target repo's actual toolchain needs

Look at `<TARGET_REPO>`'s `mix.exs` (Elixir/OTP requirements, dependency list) and
any `.tool-versions` file. Compare against `versions.toml`'s `[runtime]` table in
this repo (`otp = "29.0"`, `elixir = "1.20.2"` at the time of writing) and the
`[packages]` table (exact pinned versions for `ash`, `spark`, `reactor`, `igniter`,
`ash_postgres`, `ash_phoenix`, `ash_json_api`, `ash_authentication`, `ash_oban`,
`ash_state_machine`, `ash_archival`, `ash_money`, `ash_cloak`, `ash_graphql`,
`ash_ai`, and more).

Decide which existing capsule variant covers what `<TARGET_REPO>` needs:

- Needs only core Elixir/Mix, no Ash → `beam-core`
- Needs `ash`/`spark`/`reactor`/`igniter` only → `ash-core`
- Needs `ash_postgres` too → `ash-postgres`
- Needs `ash_phoenix` too → `ash-phoenix`
- Needs the maximal Ash ecosystem → `ash-full`

If none of the existing variants cover what `<TARGET_REPO>` needs (e.g. it needs a
package not in `[packages]`, or a different OTP/Elixir pin), you would add a new
versioned capsule variant to this repo on a purpose branch rather than force a
mismatch — see `docs/how-to/` for adding a new capsule variant. This tutorial
assumes an existing variant already covers your target.

## Step 3: Manufacture (or reuse) the matching capsule

If a matching capsule artifact from a previous GitHub Actions run already exists,
download it through your connected GitHub interface and skip to Step 4. Otherwise,
build it yourself:

```bash
chmod +x scripts/*.sh
export GITHUB_SHA="$(git rev-parse HEAD)"
scripts/build-capsule.sh ash-core   # or whichever variant Step 2 selected
```

See `docs/tutorials/manufacture-your-first-capsule.md` for the full walkthrough of
this step, including the fresh-consumer verification pass — run that verification
here too, before trusting the archive.

## Step 4: Install the capsule as a local runtime dependency

```bash
scripts/install-capsule.sh dist/chatgpt-cloud-elixir-ash-core-*.tar.gz /path/to/<TARGET_REPO>-capsule
source /path/to/<TARGET_REPO>-capsule/activate
```

`activate` puts the capsule-local `erl`/`elixir`/`mix`/`hex`/`rebar` on `PATH` and
sets `MIX_HOME`/`HEX_HOME`/`HEX_OFFLINE=1` — no system BEAM install required.
Confirm what you actually have:

```bash
bash /path/to/<TARGET_REPO>-capsule/scripts/inspect-capsule.sh
```

## Step 5: Run the target repo's own real acceptance command — never this repo's fixtures

```bash
cd /path/to/<TARGET_REPO>
MIX_ENV=test mix compile --warnings-as-errors
MIX_ENV=test mix test
```

Use whatever `<TARGET_REPO>`'s own CI or documentation states as its real
acceptance command — the capsule's job is only to supply the runtime; it must
never substitute this repo's `mix_smoke`/`ash_ets_smoke` fixtures for the target's
actual tests.

## Step 6: Classify failures, don't blindly retry

If `mix deps.get` inside `<TARGET_REPO>` tries to reach Hex and fails (expected in
a restricted container, since the capsule's `HEX_OFFLINE=1` forces this), that is
expected behavior, not a bug to retry unchanged — it means `<TARGET_REPO>` has a
dependency outside the capsule's declared closure. Check whether the missing
package is one you could add to a new capsule variant (Step 2's "no match" branch)
rather than re-running the same failing command hoping for a different result.

## Step 7: If you needed to change the target repo, use purpose-branch discipline

Any change made *to `<TARGET_REPO>`* (not to this repo) still follows the standard
discipline this repo documents for itself: purpose branch from an exact base,
intentional commit, non-force push, draft PR, no merge — unless the target repo's
own maintainers have told you otherwise.

## Step 8: Report what actually happened

State, plainly: `<TARGET_REPO>`'s exact SHA, this repo's exact SHA, which capsule
variant and digest you used, the environment you ran in, the exact commands you
ran and their exit codes, the real test results, and the overall standing
(`ALIVE`/`BLOCKED`/`BUILD_BROKEN`/etc.) — using this repo's own status vocabulary,
not an informal "it worked."

## What's next

- For the field-by-field `capsule.toml`/`versions.toml` schema you'll need to read
  or extend in Step 2, see `docs/reference/`.
- For why this repo is deliberately designed to be reusable this way — the
  "repo as substrate for other repos" design rationale — see `docs/explanation/`.
- For adding a brand-new capsule variant when Step 2 finds no match, see
  `docs/how-to/`.
