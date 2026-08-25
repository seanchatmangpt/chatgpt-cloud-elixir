# This Repo as Substrate for Other Repos

`chatgpt-cloud-elixir` is not only a product in its own right — it is designed to
be borrowed by an entirely different agent session working on an entirely
different, unrelated repository. This document explains why that pattern exists,
what problem it solves, and where its limits are.

## The problem it solves

A restricted ChatGPT cloud container can run native Linux binaries and interact
with GitHub (repos, workflow runs, artifacts) through its connector, but it
frequently cannot install system packages, run Docker, or reach package
registries like Hex over the network. An agent asked to work on some other
Elixir/Phoenix/Ash/Ecto/Livebook/Spark/Reactor/Igniter repository, in that kind
of container, hits a wall before it can even compile: there may be no BEAM
toolchain on the box at all, and no way to install one through normal means.

Rather than solving that problem freshly, badly, and separately inside every
target repo an agent happens to be dropped into, `chatgpt-cloud-elixir` exists
as a *shared, pre-built* answer to exactly that wall: a repository whose entire
purpose is to manufacture and verify portable, offline BEAM runtime closures
that any other session can pull in as a dependency.

## How the pattern actually works

`README.md`'s "Quick start for ChatGPT users" section is a complete,
copy-pasteable prompt template meant to be handed to a *different* session
working on a *different* target repo. The pattern it describes:

1. Treat `chatgpt-cloud-elixir` as read-only execution infrastructure — read its
   `AGENTS.md`/`README.md` at the current exact `main` SHA first, not from
   memory or a prior summary.
2. Inspect the *target* repo's own doctrine, manifests, and CI, and inspect the
   actual cloud container currently in use — its OS/arch, whatever BEAM tools
   already exist on it, and whether network/DB access is actually available
   right now.
3. Select the maximal already-verified capsule variant from this repo that fits
   the target's needs — or, if none fits, add a new versioned capsule variant to
   *this* repo on a purpose branch, manufacture it through this repo's own
   GitHub Actions, and leave that branch unmerged unless explicitly told
   otherwise.
4. Download the manufactured artifact through the GitHub connector, verify its
   digest against the sidecar checksum, extract it, and run this repo's own
   inspect/verify scripts against the fresh extraction.
5. Use the capsule purely as a local runtime dependency to run the *target*
   repo's own real acceptance command — e.g. `MIX_ENV=test mix compile
   --warnings-as-errors && mix test` — inside the restricted container. The
   target's own fixtures and tests are what get run; this repo's fixtures never
   substitute for them.
6. Classify failures and re-hypothesize rather than blindly retrying — the same
   offline-law discipline described in
   [authority-model.md](authority-model.md) applies here too.
7. Any changes made *to the target repo* follow the same purpose-branch,
   draft-PR, no-merge discipline this repo applies to itself.
8. Produce a final receipt naming both repos' exact SHAs, the capsule digest,
   the environment, the commands run and their exit codes, the test results,
   the standing, a replay command, and the branch/PR URL — the same evidence
   shape described in [authority-model.md](authority-model.md), applied to a
   target repo instead of to `chatgpt-cloud-elixir` itself.

## Why this is architecturally unusual

Most "shared infrastructure" repos are consumed as a package dependency
(published to a registry, pulled by a build tool) or as a template repo cloned
once at project creation. This repo is consumed neither way — it is pulled in
*at runtime, per session*, by an agent that downloads a specific GitHub Actions
artifact through a connector, verifies it locally, and discards it when the
session ends. The repository itself, plus its Actions runs, functions as a
dependency-injection channel for a restricted execution sandbox that has no
other route to a working toolchain. This is close to a vendored offline
toolchain distribution mechanism built entirely out of a GitHub repo, GitHub
Actions, and connector-mediated artifact download — worth naming explicitly
because it is not the normal way a repository is designed to be used, and a
reader unfamiliar with the pattern could easily mistake the capsule scripts for
ordinary internal build tooling rather than a deliberately externally-facing
capability.

## Limits, stated precisely

- **This repo never substitutes its own fixtures for a target repo's real
  tests.** A capsule proves a runtime closure works against its *own* fixture
  (`fixtures/mix_smoke`, `fixtures/ash_ets_smoke`) — that is evidence the
  runtime itself is sound, not evidence about the target repo. The target's own
  acceptance command is what must actually run, against the target's own code.
- **Adding a new capsule variant for a target's specific needs is itself
  governed by the same purpose-branch/draft-PR/no-merge discipline** as any
  other change to this repo — an agent working on a target repo does not get
  implicit merge authority over `chatgpt-cloud-elixir` just because it needed a
  new capsule variant.
- **The pattern depends on the GitHub connector being available and this repo's
  Actions runs actually completing** — if the container an agent is running in
  cannot reach the GitHub connector at all, this pattern has no fallback; it is
  not a solution to total network isolation, only to the specific and common
  case of "GitHub connector works, package registries do not."
- **Nothing in this pattern grants DO authority.** Manufacturing a capsule for a
  target repo's use, or even opening a draft PR against the target, stays inside
  SELECT/CONSTRUCT per [authority-model.md](authority-model.md) — merging,
  deploying, or otherwise consequentially acting on the target repo requires the
  same explicit gating this repo requires of itself.

## See also

- [architecture-overview.md](architecture-overview.md) — where capsules sit
  among this repo's other three subsystems
- [authority-model.md](authority-model.md) — the SELECT/CONSTRUCT/DO separation
  and evidence discipline this pattern inherits and applies to a target repo
- `docs/reference/` (capsule schema, build/verify command reference) and
  `docs/how-to/` for the concrete steps this document describes at the "why"
  level
