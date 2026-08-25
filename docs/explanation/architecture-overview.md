# Architecture Overview

`chatgpt-cloud-elixir` is not one application — it is four independent subsystems
that happen to share a repository and a common evidence discipline. Understanding
why they are separate, and how they touch, matters more than any individual file
listing. This document gives that mental model.

## The four subsystems

1. **Capsules** (`capsules/`, `scripts/`, `verifier/`, `fixtures/`, `versions.toml`)
   — the offline manufacturing subsystem. It exists to solve a network asymmetry:
   restricted ChatGPT cloud containers can run Linux binaries and talk to GitHub
   through a connector, but frequently cannot reach Hex, apt, or DNS. Capsules turn
   pinned source into portable, self-contained Erlang/Elixir/Ash/PostgreSQL runtime
   closures that a container can extract and execute with zero network access.
2. **control-plane** (`control-plane/`) — a live Phoenix/Ash application deployed to
   Fly.io. It is the persistent operational projection of the capsule/process
   world: it ingests OCEL (Object-Centric Event Log) batches from producers,
   exposes them over LiveView, AshAdmin, JSON:API, GraphQL, and an AshAi MCP tool
   server, and runs its own internal qualification state machine over incoming
   receipts.
3. **project-memory** (`project-memory/`, `scripts/project_memory_proxy.py`) — a
   cross-run, cross-agent memory transport built on GitHub Project v2, used by both
   ChatGPT scheduled cells and Claude/MCP clients to persist capability-frontier
   state between otherwise-stateless runs.
4. **CI orchestration and repo doctrine** (`.github/workflows/`, `AGENTS.md`,
   `manufacturing/AGENTS.md`) — the workflows and written doctrine that manufacture
   and verify all of the above, and the authority/evidence rules (see
   [authority-model.md](authority-model.md)) that every workflow in this repo is
   built to satisfy.

## Why four, not one

Each subsystem answers a different question, on a different clock, with a
different failure mode:

- Capsules answer "how do I get a working BEAM toolchain into a container that has
  none?" — a one-shot, per-invocation problem. A capsule is built, downloaded,
  extracted, and discarded; it carries no memory between runs.
- control-plane answers "what actually happened, continuously, across every run
  that ever reported in?" — a long-running, stateful problem. It is a real
  deployed service with its own database, not a script that exits.
- project-memory answers "what did a *previous*, unrelated run already learn?" — a
  cross-session continuity problem that neither a one-shot capsule nor a
  request/response web service is shaped to solve on its own. It needed something
  that persists independent of any single deploy, is inspectable by humans, and is
  writable by both ChatGPT-side file/Action workflows and Claude-side MCP calls
  without either owning the other. See
  [shared-memory-philosophy.md](shared-memory-philosophy.md) and
  [two-transports-one-project.md](two-transports-one-project.md) for why GitHub
  Project v2 specifically was chosen for this.
- CI orchestration answers "how do I prove any of the above actually works,
  without trusting my own claim?" — it is deliberately kept as *construction and
  transport*, never as the source of truth for whether something works. See
  [authority-model.md](authority-model.md) for the precise doctrine.

Collapsing these into one system would conflate a stateless manufacturing step
with a stateful live service, and would conflate "I built it" with "it is proven
to work" — exactly the distinction this repo's evidence discipline exists to
preserve.

## How the four actually touch each other

The subsystems are loosely coupled, and it is worth being precise about exactly
where the coupling is, because it is much smaller than "four parts of one system"
might suggest:

- **capsules ↔ control-plane**: the `process-intelligence` capsule and
  control-plane's OCEL ingestion share only an envelope *format*
  (`chatgpt-cloud-ocel/1`), generated on both sides by structurally similar
  `emit-ocel.py` scripts. They do not share a runtime, a dependency graph, or a
  deployment. The capsule's OTP 27.2.4/Elixir 1.18.4 pin is deliberately different
  from control-plane's OTP 29.0/Elixir 1.20.2 pin — proof they are not the same
  build in different clothing.
- **capsules ↔ CI orchestration**: CI builds, then separately re-verifies, every
  capsule variant — and does so as two genuinely distinct passes (an in-run
  "fresh extracted consumer" check inside `build-capsules.yml`, and a second,
  later `verify-capsules.yml` run triggered by the first workflow's completion,
  downloading the artifact fresh rather than reusing build-workspace state).
- **control-plane ↔ project-memory**: control-plane's `ChatGPTCloud.DfcmMemory`
  domain is a second, independent transport onto the same GitHub Project #2 that
  the Python proxy writes to. It has no local storage of its own for this data —
  every MCP memory call is a live GraphQL round trip to the Project, not a read
  from control-plane's own Postgres database.
- **CI orchestration ↔ everything**: `release-integrity.yml` cross-checks that
  `versions.toml`'s release version and `control-plane/mix.exs`'s version agree;
  `autonomic-manufacturing.yml` builds the `manufacturing/` ggen surface into a
  capsule; `r48-independent-consumer.yml` runs an externally-owned verification
  tool from a different repository (`ggen-marketplace`) against this repo's own
  identity contract. Only `deploy-fly.yml` performs a genuinely consequential
  action (deploying a live service) — everything else in CI is manufacture or
  verify, never merge, never deploy without explicit gating.

## What this repo is, structurally

Put together, the four subsystems make `chatgpt-cloud-elixir` two things at once:
a product that manufactures and verifies its own artifacts, and a piece of
portable execution infrastructure that other, unrelated repositories can borrow
as a dependency. That second role is unusual enough to warrant its own document —
see [repo-as-substrate.md](repo-as-substrate.md).

## See also

- [authority-model.md](authority-model.md) — the SELECT/CONSTRUCT/DO separation
  and evidence discipline that every subsystem above is built to satisfy
- [repo-as-substrate.md](repo-as-substrate.md) — how this repo is used to unblock
  work on a *different* target repository
- [shared-memory-philosophy.md](shared-memory-philosophy.md) — why project-memory
  exists and what it is trying to preserve across runs
- [two-transports-one-project.md](two-transports-one-project.md) — why
  project-memory has two independent client implementations instead of one
