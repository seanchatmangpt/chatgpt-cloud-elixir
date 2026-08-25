# Authority Model: SELECT / CONSTRUCT / DO, and Why Green CI Is Not Proof

This document explains the authority-separation and evidence doctrine that
governs every workflow, script, and receipt in this repository. It is written
down explicitly in `AGENTS.md` and `manufacturing/AGENTS.md`, and it is worth
understanding *why* it exists, not just reciting it, because it shapes almost
every design decision elsewhere in the repo.

## The problem this doctrine responds to

An autonomous agent operating in a restricted cloud container, with a connected
GitHub interface and no reliable package-network access, is in a position to
generate a great deal of plausible-looking evidence very cheaply: a workflow that
runs, an artifact that uploads, a JSON file literally named `receipt.json`. None
of that is actually proof that admitted code executes correctly against its
real acceptance criteria. The authority model exists to stop a workflow's own
successful *completion* from being silently treated as a claim about the
*correctness* of what it built.

`AGENTS.md` states this directly: "GitHub Actions may manufacture and transport a
capsule; CI is never the crown. The crown is execution of the exact admitted
capsule in the consuming environment." Manufacturing capital and verifying
capital are treated as separate acts, done separately, and neither is allowed to
stand in for the other.

## SELECT / CONSTRUCT / DO

Three levels of authority, strictly separated:

- **SELECT** — choosing which capsule variant, which source SHA, which target
  base to work against. A planning act; it commits to nothing executable.
- **CONSTRUCT** — building an artifact: compiling a capsule, running `ggen sync
  run`, generating a manifest. Construction produces something, but production is
  not proof the thing produced is correct.
- **DO** — consequential external action: deploying a live service, merging a
  branch, spending a credential, granting cloud access. `manufacturing/AGENTS.md`
  states this precisely for the ggen surface: "This surface is SELECT /
  CONSTRUCT / VERIFY only. `CONSTRUCT_VERIFY` is the maximum authority ceiling. No
  ontology, generated manifest, capsule, or receipt may silently grant cloud
  credentials, repository merge authority, external API authority, or
  consequential DO."

Concretely: model output, workflow output, and generated manifests carry **no
ambient execution authority**. Nothing produced inside SELECT or CONSTRUCT is
permitted to reach into DO without an explicit, separately-gated step. This is
visible in the repo's one genuinely actuating workflow, `deploy-fly.yml`: it is
double-gated (a required `FLY_API_TOKEN` secret presence check *and* either a
manual dispatch or an explicit `vars.FLY_DEPLOY_ENABLED` repository variable for
the push-triggered path), and its concurrency group deliberately does not cancel
in-progress runs — a production deploy is treated as consequential enough that
even the workflow's own re-triggering behavior is more conservative than every
other workflow in the repo.

## Why "workflow green" is never treated as proof

`AGENTS.md` states this as a flat rule: "Workflow existence, artifact existence,
package metadata, or a file called `receipt.json` is not execution evidence."
The repo's own capsule build-receipts are a concrete, self-documented example of
why this matters: every `build-*.sh` script writes a `build-receipt.json` that
self-labels `standing: ALIVE` for the *construction* step, unconditionally,
regardless of whether the resulting capsule actually works for a downstream
consumer. Only a second, separate `receipt.json`, produced by a *consumer-side*
verify script running against a freshly extracted archive (not the build
workspace, which may carry stale state, cached deps, or leftover environment),
is treated as authoritative for whether the capsule is genuinely `ALIVE`. A
reader who greps for `"standing": "ALIVE"` in a build workspace can be misled by
design — the doctrine deliberately keeps these two receipts distinct so that
"it built" and "it verified" can never be silently collapsed into the same
claim.

The same pattern recurs at the CI level: `build-capsules.yml` runs its own
in-workflow "fresh extracted consumer" check, and then a *second*,
independently-triggered workflow, `verify-capsules.yml`, downloads the
already-uploaded artifact from that specific completed run and replays it again
— a genuinely separate re-verification pass on the transported artifact, not a
formality.

## Evidence and standing vocabulary

Every receipt, commit message, and CI step in this repo uses one shared status
vocabulary: `UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN |
UNSUPPORTED`, plus typed `REFUSED_*` reasons (e.g. `REFUSED[REPO_IDENTITY]`,
`REFUSED_FORMATTER_MUTATION`, `REFUSED_INEXACT_FORMAT_SUBJECT`,
`BLOCKED[IRREDUCIBLE_AUTHORITY]`). `ALIVE` specifically requires the *exact
admitted subject* to have executed the *exact acceptance command* successfully —
not a fixture standing in for it, not a subset of it, not a prior run of it.
Formally, `AGENTS.md` states this as `A = μ(O*)`; `R = receipt(A)` — a receipt
binds together the target repo/ref/SHA, the capsule identity and digest, the
platform/arch, toolchain versions, the exact command and its exit code, the test
result, the observed network state, the standing, and a replay command someone
else could run to reproduce it. A status claim without that binding is not
considered evidence, regardless of how confident its phrasing is.

This vocabulary is not decorative. Refusals discriminate on purpose, and the
repo tests that they do: `r48-independent-consumer.yml` deliberately re-runs its
own verification tool with a wrong repository identity and asserts it exits `2`
with `REFUSED[REPO_IDENTITY]` — proof the court actually rejects a bad subject
rather than always passing. `format-control-plane.yml` similarly diffs the
formatter's output *after* `mix format --check-formatted` already reported
clean, specifically to catch a formatter-version drift that `--check-formatted`
alone might miss, and fails with `REFUSED_FORMATTER_MUTATION` if any diff
appears. Verifying that a check can fail is itself part of the evidence
discipline, not an afterthought.

## The offline law

A specific, named instance of the broader discipline: assume package-network
access may fail even when the GitHub connector itself is reachable, and never
silently retry an unchanged failed apt/curl/Hex/DNS/dependency-fetch operation
without a new hypothesis for why it might succeed this time. `AGENTS.md` states
the consequence directly: "An admitted offline capsule that unexpectedly fetches
from Hex is `BUILD_BROKEN` unless the target explicitly requires a dependency
outside that capsule's declared closure." A capsule reaching the network when it
was declared self-contained is treated as a contract violation, not a lucky
extra connectivity check — the whole point of a capsule is that it does not
need what it did not declare.

`scripts/run-offline.sh` enforces this two different ways depending on host
capability: real `unshare -n` network-namespace isolation when available, or a
loopback-only proxy pointed at an unlistened port (`127.0.0.1:9`) to force any
accidental network call to fail fast when namespace isolation isn't. Either way
the goal is the same — make "no network" a property that gets *tested*, not
merely assumed.

## Why this matters for anyone extending the repo

Any new capsule, workflow, or MCP tool added to this repo inherits the same
obligations: construction and verification stay separate steps with separate
receipts; nothing generated grants itself DO authority; failures get a typed
reason, not a bare non-zero exit; and a green check on its own is never the
sentence written into a commit message or a receipt as "this works." What
*does* license that sentence is a real, replayable command with a real exit
code, bound to the exact subject it was run against.

## See also

- [architecture-overview.md](architecture-overview.md) — how the four subsystems
  this doctrine governs relate to each other
- [repo-as-substrate.md](repo-as-substrate.md) — the same evidence discipline,
  applied when this repo is used to unblock work on a different target repo
