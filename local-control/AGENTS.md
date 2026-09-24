# Local Control Agent Contract

Scope: `local-control/**` plus changes to `scripts/local_control_agent.py` and local-control service installers when this contract is the governing feature.

## Authority

Local control is an opt-in user-host actuation boundary. Preserve `SELECT != CONSTRUCT != DO`.

A remote request has **no ambient authority**. It must be admitted by all of:

1. exact configured repository and `local-control-bus` transport branch;
2. unique request ID matching its filename;
3. target `machine.id` or explicit wildcard;
4. unexpired request when `expires_at` is present;
5. local replay ledger;
6. operation allowlist;
7. operation-specific path/executable/app/destructive policy;
8. local platform/runtime availability.

Do not add request fields that mutate policy, inject arbitrary environment variables, transport secrets, or bypass replay/expiry/machine scope.

## Execution law

`process.run` must remain argv-based with `shell=False`. An allowlisted executable may itself be powerful; that power is an explicit local-policy decision. Do not silently add executables to the active local policy.

Arbitrary AppleScript text must not be accepted from a remote request. GUI macros are named locally in `named_applescripts` and requests may reference only the stable local name.

Destructive filesystem operations must remain separately gated by `allow_destructive` and `write_roots`.

No inbound network listener is required or admitted by the default design. The agent polls GitHub outbound and pushes receipts outbound.

## Evidence

Request commit != execution. Agent process existence != execution. `ALIVE` requires the exact request to execute on the exact target machine and a typed receipt to be persisted.

A receipt must bind request ID/hash, operation, machine ID, transport repo/branch, timing, result/error, reason, and standing. Do not include secrets or raw environment dumps.

Preserve the local replay ledger even if request/receipt Git traffic is later cleaned.

## Verification

At minimum qualify:

- Python compilation;
- machine-scope refusal;
- request-id/filename binding;
- expiry refusal;
- read/write root fencing;
- destructive-operation refusal by default;
- executable allowlist;
- argv execution with no shell interpretation;
- replay refusal;
- receipt production.

macOS UI operations require execution on an enrolled macOS host for `ALIVE`; Linux CI can only prove their refusal/platform branches and source-level contract.

## Change discipline

Prefer new typed operations with narrow payloads over widening `process.run`. Repeated useful action sequences should become named bounded capabilities with their own policy/falsifier surfaces.

Do not convert the local host into a generic self-hosted Actions runner as an implementation shortcut unless the user explicitly chooses that broader authority model.
