# chatgpt-cloud-elixir Agent Operating Contract

Scope: repository-wide unless a deeper `AGENTS.md` narrows a subtree. Live tree and observed execution outrank stale prose. This repository exists to manufacture portable Erlang/Elixir/Ash runtime capsules for restricted ChatGPT cloud containers where system packages, Docker, DNS, or direct Hex access may be absent.

GitHub Actions may manufacture and transport a capsule; CI is never the crown. The crown is execution of the exact admitted capsule in the consuming environment.

## Evidence / standing

Use `UNKNOWN | PARTIAL_ALIVE | ALIVE | BLOCKED | BUILD_BROKEN | UNSUPPORTED` plus typed `REFUSED_*`. `ALIVE` requires the exact admitted subject executing the exact acceptance command. Track observed/admitted/constructed/executed/changed/verified/inferred/refused/blocked/unsupported separately. Workflow existence, artifact existence, package metadata, or a file called `receipt.json` is not execution evidence.

`A = μ(O*)`; `R = receipt(A)`. A receipt binds target repo/ref/SHA, capsule identity/digest, platform/architecture, toolchain/framework versions, command/exit, relevant test result, observed network state, standing, and replay.

## Preserve → Fence → Calculus

Before changing this repository or using it against a target repo, resolve both subjects to exact SHAs. Read applicable root+nested doctrine, `versions.toml`, capsule manifests, build/install/inspect/verify scripts, fixture projects, verifier code, workflows, and the target's manifests/CI/database requirements. Inspect the consuming environment for OS/architecture, existing BEAM tools, DNS/egress, service binaries, and writable paths. Never silently move an admitted base.

Preserve maximal reversible compatible capsule variants before selecting one. A failed network/package/service edge is topology, not proof that every capsule route is impossible. Apply Chesterton's fence before removing compatibility or offline behavior.

## Authority and capsule lifecycle

Separate `SELECT`, `CONSTRUCT`, `DO`. Model/planner/workflow output has no ambient execution authority. Select the maximal compatible live-defined capsule variant; do not mutate an unrelated target project merely to fit an existing capsule. Manufacture new versioned variants here when needed.

Construction must pin relevant OTP/Elixir/Hex/Rebar/package identities, close dependencies explicitly, include relocatable runtime/build/dependency state required by the declared variant, exclude credentials/secrets, and verify the archive in a clean consumer phase rather than trusting the build workspace.

Import through the connected GitHub artifact path only after verifying the exact artifact identity/digest available from GitHub. A connector object is not a mounted file. Extract into a fresh path, run the live inspect/verify scripts before target use, and activate through the repository's relocatable activation path.

For target execution, prefer the target's exact acceptance command. Typical proof expands from BEAM/Mix version checks → offline dependency closure → compile → focused tests → full tests → required integration/e2e/service checks. Do not substitute unit proof for a requested database/browser/protocol boundary.

## Offline law

Assume package-network access may fail even while the GitHub connector works. Do not rerun an unchanged failed `apt`, `curl`, Hex, DNS, or dependency-fetch operation without a new hypothesis. An admitted offline capsule that unexpectedly fetches from Hex is `BUILD_BROKEN` unless the target explicitly requires a dependency outside that capsule's declared closure.

## Canonical surfaces

The live repository defines version/compatibility selection, per-capsule requirements, manufacture/install/inspect/verify/offline scripts, real acceptance fixtures, semantic verifier logic, and construction/consumer workflows. Generated archives, manifests, and receipts are projections; edit their owning version/capsule/build/verifier sources and regenerate rather than hand-editing outputs.

## Change / verification discipline

Preserve compatibility and receipts before convenience. Prefer deterministic configuration to runner ambient state. Preserve alternate compatible variants instead of deleting possibilities to make one graph solve. Do not weaken tests or fake offline proof. Hosted CI supplements consumer execution; it does not replace it.

`chatgpt-cloud-elixir` is `ALIVE` for a capsule tuple only when the exact source manufactures the artifact, digest/identity is recorded, a fresh consuming environment extracts it, the capsule verifier passes, the relevant ordinary Mix/Ash commands execute, and replay does not depend on hidden build-workspace state. Lesser evidence is typed accordingly.

## GitHub / receipt

Unless explicitly instructed otherwise: purpose branch from exact base, intentional commit, non-force push, draft PR, no merge. Final receipt exposes repo/base/tree, target identity, capsule tuple/digest, transports/failures, changes/generated status, commands/exits, verification ladder, replay, branch/SHA/PR, scoped standing, and falsifiers.