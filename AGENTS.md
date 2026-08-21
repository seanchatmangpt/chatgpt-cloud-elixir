# AGENTS.md

## Mission

`chatgpt-cloud-elixir` exists to make real Erlang/Elixir/Ash execution available inside restricted ChatGPT cloud containers where system packages, Docker, DNS, or direct Hex access may be absent.

The repository manufactures portable runtime capsules. GitHub Actions may construct and transport a capsule, but CI is never the final proof. The crown is execution of the admitted capsule in the consuming cloud environment.

## Standing vocabulary

Use only these execution states:

- `UNKNOWN` — not observed or insufficient evidence.
- `PARTIAL_ALIVE` — a lower boundary executed, but the requested crown did not.
- `ALIVE` — the exact admitted subject executed the exact acceptance command successfully.
- `BLOCKED` — an external capability/authority boundary prevented execution.
- `BUILD_BROKEN` — construction reached execution but the manufactured object violated its contract.
- `UNSUPPORTED` — the requested tuple is outside the admitted compatibility matrix.

Do not collapse `UNSUPPORTED` into `REFUSED`, and do not call inspection, workflow existence, artifact existence, or compilation metadata `ALIVE`.

## Non-negotiable evidence model

Track separately:

1. **Observed** — versions, files, refs, environment facts actually inspected.
2. **Admitted** — exact repo/ref/SHA, capsule variant, platform/architecture, version tuple, and acceptance command.
3. **Constructed** — runtime/dependency closure produced by the manufacturing workflow.
4. **Executed** — commands actually run against the admitted subject.
5. **Changed** — repository mutations intentionally made.
6. **Verified** — assertions/tests/checks that passed.
7. **Inferred** — conclusions not directly observed; mark them explicitly.
8. **Blocked/unsupported/refused** — typed boundaries with causes.

A receipt must bind identity, construction, execution, result, and replay instructions. A file named `receipt.json` is not automatically a receipt.

## Required workflow for agents

### 1. Orient

Before changing a target Elixir repository:

- inspect this repository and its latest `AGENTS.md`;
- resolve `chatgpt-cloud-elixir` and the target repository to exact SHAs;
- inspect the target's root and nested `AGENTS.md`, manifests, `.tool-versions`, `mix.exs`, `mix.lock`, CI, test aliases, and database/runtime requirements;
- inspect the current execution environment for OS, architecture, existing `erl`, `elixir`, `mix`, DNS/egress, database binaries, and writable paths.

Never silently move the admitted base SHA.

### 2. Select

Choose the maximal compatible capsule variant that preserves lawful capabilities without adding unrelated services:

- `beam-core` — OTP + Elixir + Mix + Hex + Rebar.
- `ash-core` — Ash + Spark + Reactor + ETS-safe closure.
- `ash-postgres` — AshPostgres dependency/build closure; PostgreSQL service remains separately admitted.
- `ash-phoenix` — Phoenix/Ash integration closure.
- `ash-full` — maximal compatible Ash ecosystem closure defined by `versions.toml`.

If no compatible capsule exists, manufacture a new versioned variant in this repository. Do not mutate a target project merely to fit an unrelated existing capsule.

### 3. Construct

Capsule manufacture must:

- use pinned OTP, Elixir, Hex, Rebar, and package versions;
- resolve dependencies with an explicit lockfile;
- include runtime binaries, Mix/Hex/Rebar state, `deps`, `_build`, application metadata, native build outputs, activation scripts, manifest, checksums, and replay verifier;
- exclude credentials, tokens, publishing keys, and runner secrets;
- verify the archive in a clean second phase that consumes the artifact rather than the original build workspace.

GitHub Actions is a construction/transport edge, not truth.

### 4. Import

In the ChatGPT cloud container:

- download the exact workflow artifact through the connected GitHub interface;
- verify the artifact digest when supplied by GitHub;
- extract the capsule into a fresh path;
- run `./scripts/inspect-capsule.sh` and `./scripts/verify-capsule.sh` before using it on another repository;
- activate it only through its relocatable activation script.

Do not assume a connector object is already mounted as a local tree or file.

### 5. Execute locally

For a target project, prefer its documented acceptance command. Otherwise use the narrowest existing command that proves the requested behavior.

Typical ladder:

1. `erl` / `elixir --version` / `mix --version`
2. `mix deps` or offline dependency check
3. `MIX_ENV=test mix compile`
4. focused tests
5. `mix test`
6. repo-specific integration/e2e checks
7. quality/security/type checks when they are part of the repo contract

Do not substitute unit proof for a requested integration/service/browser/database proof.

### 6. Receipt

Every local verification must emit or preserve evidence containing:

- target repository/ref/SHA;
- capsule name/version/digest;
- OS/architecture;
- OTP/Elixir/Mix/Hex/Rebar versions;
- relevant framework/package versions;
- command and exit code;
- test counts/results where available;
- network/offline state if observed;
- final standing;
- exact replay command.

## Offline rule

Assume direct package-network access may fail even when GitHub connector access works. Do not repeatedly rerun an unchanged failing `apt`, `curl`, `mix deps.get`, or DNS operation without a new hypothesis.

A compatible capsule should let an already-closed project run ordinary developer commands without fetching dependencies. If Mix tries to fetch from Hex during an admitted offline replay, classify the capsule as `BUILD_BROKEN` unless the target explicitly requires a dependency not represented in the capsule.

## Repository structure contract

Canonical surfaces:

- `versions.toml` — human-reviewed version and compatibility selection.
- `capsules/*/capsule.toml` — per-variant requirements and acceptance commands.
- `scripts/build-capsule.sh` — manufacture one capsule.
- `scripts/install-capsule.sh` — relocatable activation/install helper.
- `scripts/inspect-capsule.sh` — non-actuating introspection.
- `scripts/verify-capsule.sh` — executable acceptance and receipt generation.
- `scripts/run-offline.sh` — offline verification entrypoint.
- `fixtures/*` — real Mix/Ash acceptance projects.
- `verifier/*` — semantic manifest/runtime verification.
- `.github/workflows/build-capsules.yml` — construction and artifact publication.
- `.github/workflows/verify-capsules.yml` — replay/consumer verification.

Generated archives, manifests, and receipts are projections. Do not hand-edit generated outputs when the source/version selection can regenerate them.

## Change discipline

- Preserve compatibility and receipts before adding convenience.
- Prefer deterministic configuration over ambient runner state.
- Keep version changes explicit and reviewable.
- Preserve alternate compatible variants instead of deleting possibilities to make one graph solve.
- Do not weaken tests to make a capsule green.
- Do not fabricate offline proof by disabling the code path being tested.
- Do not merge branches or PRs unless the user explicitly requests merge.

## Definition of ALIVE for this repository

`chatgpt-cloud-elixir` is `ALIVE` for a capsule tuple only when all are observed:

1. the exact source SHA manufactured the capsule;
2. construction succeeded;
3. the archive digest is recorded;
4. a fresh consumer environment extracts it;
5. the capsule's own verifier passes;
6. ordinary `mix compile` and `mix test` execute locally for the relevant fixture;
7. for Ash capsules, real Ash resource actions execute and assertions pass;
8. replay does not depend on hidden build-runner workspace state.

Anything less is `PARTIAL_ALIVE`, `BLOCKED`, `BUILD_BROKEN`, or `UNSUPPORTED` as appropriate.
