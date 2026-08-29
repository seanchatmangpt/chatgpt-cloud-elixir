# chatgpt-cloud-elixir

Portable, offline-capable Erlang/Elixir/Ash runtime capsules for restricted ChatGPT cloud execution environments.

## Why this exists

Some ChatGPT cloud containers can execute native Linux binaries but cannot reliably install system packages or reach Hex directly. At the same time, the connected GitHub interface can inspect repositories, workflow runs, logs, and workflow artifacts.

`chatgpt-cloud-elixir` turns that asymmetry into a deterministic execution path:

```text
pinned source + versions
        ↓
GitHub Actions manufactures dependency/runtime closure
        ↓
versioned capsule + manifest + checksums + receipt
        ↓
GitHub workflow artifact
        ↓
ChatGPT imports the artifact
        ↓
local clean-container execution
        ↓
mix compile / mix test / real Ash actions
        ↓
ALIVE receipt
```

GitHub Actions is used for **construction and transport**. It is not the final test oracle. The final proof is local execution against the exact admitted subject.

## Status model

This repository uses a small explicit standing vocabulary:

| State | Meaning |
| --- | --- |
| `UNKNOWN` | Not observed or insufficient evidence. |
| `PARTIAL_ALIVE` | A lower execution boundary passed, but the requested crown did not. |
| `ALIVE` | The exact admitted subject executed the exact acceptance command successfully. |
| `BLOCKED` | An external capability or authority boundary prevented execution. |
| `BUILD_BROKEN` | A manufactured capsule reached execution but violated its contract. |
| `UNSUPPORTED` | The requested platform/version/capability tuple is outside the admitted matrix. |

Workflow existence, a green status badge, an uploaded artifact, or a file named `receipt.json` are not by themselves `ALIVE`.

## What the repository manufactures

The initial capsule graph is:

- **beam-core** — Erlang/OTP, Elixir, Mix, Hex, Rebar.
- **ash-core** — `beam-core` plus Ash, Spark, Reactor and a real ETS-backed Ash acceptance application.
- **ash-postgres** — AshPostgres dependency/build closure. The PostgreSQL server is a separately admitted runtime dependency.
- **ash-phoenix** — Phoenix/Ash integration dependency/build closure.
- **ash-full** — the maximal compatible Ash ecosystem closure admitted by `versions.toml`.

Alternative incompatible dependency graphs should become separate named variants rather than being silently discarded.

## Intended consumer environment

The primary target is Linux x86_64 with:

- writable filesystem;
- no assumed system Erlang/Elixir installation;
- no assumed Docker daemon;
- possibly blocked DNS or outbound TCP;
- ability to retrieve GitHub workflow artifacts through the connected GitHub interface.

The capsule is relocatable and must not require installation under `/usr/local`.

## Quick start for ChatGPT users

If you want ChatGPT to work on an Elixir, Phoenix, Ecto, Livebook, Ash, Spark, Reactor, Igniter, or related BEAM repository in its cloud environment, copy and paste the prompt below and replace the target repository/task fields.

### Copy/paste prompt

```text
Use https://github.com/seanchatmangpt/chatgpt-cloud-elixir as the execution substrate for this work.

Target repository: <OWNER/REPO or GitHub URL>
Base ref: <branch/tag/SHA, or resolve the default branch to an exact SHA if omitted>
Task: <the outcome I want>
Acceptance: <the exact command/behavioral proof I require, or infer the narrowest documented repo acceptance command if omitted>

Before changing the target repository:
1. Read chatgpt-cloud-elixir/AGENTS.md and README.md from the current exact main SHA.
2. Inspect the target repo's root and nested AGENTS.md, mix.exs, mix.lock, .tool-versions, CI, aliases, test setup, database/service requirements, and relevant architecture docs.
3. Inspect the current cloud container for OS/architecture and existing Erlang/Elixir/Mix/network/database capabilities.
4. Select the maximal compatible chatgpt-cloud-elixir capsule. Prefer an existing verified artifact when its source/version/toolchain identities match the target requirements.
5. If no compatible capsule exists, add a new versioned capsule variant to chatgpt-cloud-elixir on a purpose branch, manufacture it with GitHub Actions, and keep that work unmerged unless I explicitly request merge.
6. Download the exact workflow artifact through the GitHub connector, verify its digest/checksums, extract it locally, and run its own inspect/verify commands.
7. Use the imported capsule to run the target repo's tests locally in the ChatGPT cloud container. GitHub CI may supplement local proof but must not substitute for it.
8. Do not call the target ALIVE unless the exact acceptance behavior executed successfully against the admitted target SHA.
9. If a command fails, preserve/classify the failure, form a new hypothesis, repair the narrowest cause, and rerun the failed boundary. Do not repeatedly rerun an unchanged network/toolchain failure.
10. Publish target-repo changes only on a purpose branch and draft PR unless I explicitly ask for another state. Never merge unless I explicitly request it.

Final receipt must state:
- target repo/ref/exact SHA;
- chatgpt-cloud-elixir repo/ref/exact SHA;
- capsule name/version/digest;
- observed environment and network state;
- construction/transport failures, if any;
- files changed;
- exact commands and exit codes;
- tests/results;
- final standing: UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN | UNSUPPORTED;
- replay command;
- branch/SHA/draft PR URL for any published changes.

Do the work in this response. Do not stop at a plan, documentation-only change, or CI metadata when local execution is possible.
```

That prompt is deliberately repository-agnostic. For an Ash project, a useful acceptance line is usually:

```text
Acceptance: MIX_ENV=test mix compile --warnings-as-errors && mix test
```

For a project with database-backed integration tests, specify the repo's real setup command instead of accepting an ETS-only substitute.

## Repository layout

This tree covers only the original capsule-manufacturing core. `CLAUDE.md`'s "Repository
layout" section and `docs/README.md` are the current, fuller maps of the whole repo
(manufacturing/, control-plane/, project-memory/, ggen/, ontology/+templates/+ggen.toml,
local-control/, verification/, tests/, docs/ — see those for what each one is).

```text
.
├── AGENTS.md
├── README.md
├── versions.toml
├── capsules/
│   ├── beam-core/capsule.toml
│   ├── ash-core/capsule.toml
│   ├── ash-postgres/capsule.toml
│   ├── ash-phoenix/capsule.toml
│   ├── ash-full/capsule.toml
│   ├── postgres17/capsule.toml
│   ├── process-intelligence/capsule.toml
│   └── autonomic-manufacturing/capsule.toml
├── fixtures/
│   ├── mix_smoke/
│   └── ash_ets_smoke/
├── scripts/
│   ├── build-capsule.sh
│   ├── install-capsule.sh
│   ├── inspect-capsule.sh
│   ├── verify-capsule.sh
│   └── run-offline.sh
├── verifier/
│   ├── verify_manifest.exs
│   └── verify_runtime.exs
└── .github/workflows/
    ├── build-capsules.yml
    ├── verify-capsules.yml
    └── ... 16 more — capsule/service builds, control-plane CI/format/deploy, the two
        ggen pipelines (autonomic-manufacturing + GGEN Ecosystem OCEL), local-control CI,
        project-memory proxy, release integrity, and standing court/qualification checks
```

Generated capsule archives, manifests, checksums and receipts are build projections and should not be hand-maintained in the source tree.

## Capsule contract

A consumable capsule contains enough state to execute normal developer commands without a global BEAM installation or a fresh dependency fetch:

- relocatable OTP runtime;
- Elixir/`iex`/`mix` launchers;
- Hex archive/state;
- Rebar3;
- pinned `mix.lock`;
- dependency source closure;
- compiled `_build` closure including `.app` metadata;
- native artifacts used by dependencies;
- activation/install helper;
- source/version manifest;
- SHA-256 checksums;
- verification/replay scripts;
- machine-readable execution receipt.

The preferred acceptance interface is ordinary Mix:

```bash
MIX_ENV=test mix compile
MIX_ENV=test mix test
```

A direct-BEAM runner can be useful diagnostically, but it does not replace normal Mix acceptance.

## Security boundary

Capsules must never contain:

- GitHub tokens;
- Hex publishing credentials;
- private package credentials;
- CI secrets;
- cloud credentials;
- runner identity material.

Only public dependency retrieval is required by the initial implementation.

## Development

Read `AGENTS.md` before changing this repository. The canonical version selection surface is `versions.toml`; capsule definitions describe allowed capabilities and acceptance commands. Workflows manufacture and verify projections from those inputs.

The repository is intentionally evidence-oriented: construction, execution, verification and standing are separate facts. A green workflow can prove the manufacturing edge is healthy. Only replay in the consuming environment proves that the capsule solves the consumer's execution problem.

## Definition of Done for `ash-core`

`ash-core` is `ALIVE` only when all of these are observed for the exact capsule:

1. pinned OTP/Elixir/Hex/Rebar/Ash versions are recorded;
2. the workflow constructs the closure successfully;
3. the exact archive digest is recorded;
4. a clean consumer extracts and activates it without a system BEAM installation;
5. `elixir --version` and `mix --version` execute from the capsule;
6. a plain Mix fixture passes `mix test`;
7. an Ash fixture passes `MIX_ENV=test mix test`;
8. the Ash fixture performs real create/read/update/destroy actions through `Ash.DataLayer.Ets` and verifies validation/identity behavior;
9. no hidden build-runner workspace is required for replay;
10. the local verifier emits an `ALIVE` receipt binding capsule identity and execution results.
