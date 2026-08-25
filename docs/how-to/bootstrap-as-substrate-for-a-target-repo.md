# How to bootstrap this repo as a substrate against a target repo

Use this when you (a ChatGPT/Claude session) are working on a **different**
Elixir/Phoenix/Ash/Ecto/Livebook/Spark/Reactor/Igniter repository inside a
restricted cloud container that cannot install a system BEAM toolchain, and
you want to use `chatgpt-cloud-elixir` purely as portable execution
infrastructure.

This is the pattern documented in this repo's own README ("Quick start for
ChatGPT users") for treating `chatgpt-cloud-elixir` as a
dependency-injection channel for restricted sandboxes — not something you
build a feature inside, but something you pull a capsule from.

## Steps

1. Treat `chatgpt-cloud-elixir` as read-only execution infrastructure. Read
   its `AGENTS.md` and `README.md` at the current exact `main` SHA first, so
   you know the current capsule graph and doctrine.

2. Inspect the **target** repo you're actually working on: its own doctrine,
   manifests, and CI, plus the actual cloud container you're running in
   right now (OS/arch, any pre-existing BEAM tools, network/DB
   availability).

3. Select the maximal compatible existing capsule variant from this repo's
   graph (`beam-core`, `ash-core`, `ash-postgres`, `ash-phoenix`,
   `ash-full`, `postgres17`, `process-intelligence`,
   `autonomic-manufacturing`), preferring an already-verified artifact if
   one is available from a recent workflow run.

   If none of the existing variants match the target repo's exact
   package/version needs, add a new capsule variant to this repo instead —
   see [Add a new capsule variant](add-a-new-capsule.md) — on a purpose
   branch, manufacture it via this repo's own GitHub Actions, and leave it
   unmerged unless explicitly told otherwise.

4. Download the manufactured artifact through the GitHub connector, verify
   its digest, extract it, and run this repo's own inspect/verify scripts —
   see [Install an already-built capsule in a restricted offline
   environment](install-capsule-offline.md).

5. Use the capsule purely as a local runtime dependency to run the
   **target** repo's own real acceptance command inside the restricted
   container — for example `MIX_ENV=test mix compile --warnings-as-errors
   && mix test` run against the target repo's actual `mix.exs`, never
   substituting this repo's own fixtures for the target's real tests.

6. If a step fails (dependency fetch, DNS, an unexpected compiler warning,
   etc.), classify the failure and form a new hypothesis before retrying —
   never blindly rerun an unchanged failed network/dependency operation.
   Offline law: assume package-network access may fail even when the GitHub
   connector itself works.

7. Any changes made **to the target repo** go through the same purpose
   branch → intentional commit → non-force push → draft PR → no-merge
   discipline as changes to this repo.

8. Produce a final receipt covering both repos: both repos' exact SHAs, the
   capsule identity/digest used, the consuming environment, every
   command run and its exit code, the real test result, the standing, a
   replay command, and the branch/PR URL if one was opened.

## What "standing" means in this cross-repo context

The capsule's own `ALIVE`/`BUILD_BROKEN`/etc. standing (see [Check whether a
capsule is ALIVE vs PARTIAL_ALIVE vs BUILD_BROKEN](check-capsule-standing.md))
only certifies the capsule itself. It does not automatically certify the
target repo's own test suite passing — that is a separate, second standing
claim, earned only by actually running the target repo's real acceptance
command inside the capsule and observing its own exit code.

## See also

- [Install an already-built capsule in a restricted offline environment](install-capsule-offline.md)
- [Add a new capsule variant](add-a-new-capsule.md)
- `docs/explanation/` — "repo as substrate for other repos" as a design
  pattern, and the offline law in full
