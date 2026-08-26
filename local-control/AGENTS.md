# Track B Local Control Contract

Scope: `local-control/**`, `scripts/local_control_agent.py`, and its tests.

## Preserve / fence

Track B exists to close one observed portability gap: capsule build/verify scripts require Linux semantics that macOS tooling does not always provide (the observed case was GNU `tar --sort=name`). Colima is the admitted Linux execution environment on the enrolled Mac. Do not widen this feature into generic local shell, Docker, Kubernetes, GUI automation, or filesystem control without a new observed requirement.

## Authority

`SELECT != CONSTRUCT != DO`. A Git request is an intent, never execution authority.

The only admitted remote operation is `process.run`, and it does **not** accept argv or a shell command. Its payload names exactly one repository script matching `scripts/build-*.sh` or `scripts/verify-*.sh`. The local agent validates the path against the configured repository root, verifies the local repository identity, resolves local Colima, and manufactures the literal `colima ssh -- bash -lc ...` command itself.

Every admitted request must first persist a `PENDING_APPROVAL` receipt containing the exact request hash and literal manufactured command, then issue a best-effort macOS notification. Execution is forbidden until the human runs `local_control_agent.py approve <request-id>` on the enrolled Mac after seeing that literal command. Approval state lives only under the local state directory and is bound to the exact request SHA-256; modifying a pending request invalidates prior approval.

No auto-run. No wildcard machine target. No request-provided environment. No request-provided arguments. No request-provided repository root. No arbitrary shell text.

## Receipt law

The same receipt path is a state transition:

`PENDING_APPROVAL -> ALIVE | REFUSED | BUILD_BROKEN`

`PENDING_APPROVAL` is non-terminal and must not enter the replay ledger. Terminal standing does. `ALIVE` requires exit code 0 from the exact approved command on the enrolled Mac. Non-zero exit is `BUILD_BROKEN[PROCESS_EXIT_NONZERO]` and must retain stdout/stderr evidence.

Receipts bind request ID/hash, machine, repo/transport branch, script digest, repo HEAD/dirty state, exact literal command, stdout/stderr, byte counts/digests/truncation, exit code, duration, and standing. A Git commit or service process alone is not local execution evidence.

## Verification

Hosted tests may prove parsing, fencing, hash-bound approval, pending receipt persistence, terminal receipt replacement, replay, command manufacture, and output capture. They cannot prove Colima execution on the user's Mac. The crown is a receipt produced by the exact Mac-local `colima` run of an admitted build/verify script.

`kind` is explicitly out of scope until an observed local Kubernetes requirement exists.
