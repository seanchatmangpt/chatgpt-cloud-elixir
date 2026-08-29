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
8. local platform/runtime availability;
9. **explicit local human approval**, recorded in `ApprovalStore`
   (`~/.local/state/chatgpt-local-control/approvals/`) via the `approve`
   subcommand, for every operation in `Policy.require_approval_for` (every
   operation except `system.snapshot`, by default and by floor — policy may
   require approval for *more* operations, never fewer).

Requirement 9 is deliberately unbypassable from the git transport: the
approval store lives under `state_dir`, never under the synced `checkout`
directory (`ensure_checkout`/`sync_checkout` only ever touch `checkout`, and
`sync_checkout`'s `git reset --hard` never runs against `state_dir`), so no
commit landed on `local-control-bus` — by ChatGPT, by Claude, or by anyone
else with push access to that branch — can create, forge, or otherwise
satisfy its own approval. Only a human running `approve <request_id>` on the
enrolled machine itself, after reading the pulled request text the CLI
prints, can do that. A request awaiting approval is not executed and no
receipt is written for it (so it is re-checked, not re-executed, on every
poll) until a human approves or denies it locally; a denied request is
refused with reason `LOCAL_APPROVAL_DENIED`.

Do not add request fields that mutate policy, inject arbitrary environment variables, transport secrets, or bypass replay/expiry/machine scope/approval.

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
- receipt production;
- unapproved requests do not execute and produce no receipt (re-checked, not re-executed);
- approved requests execute exactly as before approval was introduced;
- denied requests refuse with `LOCAL_APPROVAL_DENIED` and produce a receipt;
- an `.approved` marker placed inside the *synced git checkout* (an attempted
  remote self-approval) is ignored, because the approval store is read only
  from `state_dir`, never from `checkout`.

macOS UI operations require execution on an enrolled macOS host for `ALIVE`; Linux CI can only prove their refusal/platform branches and source-level contract.

## Change discipline

Prefer new typed operations with narrow payloads over widening `process.run`. Repeated useful action sequences should become named bounded capabilities with their own policy/falsifier surfaces.

Do not convert the local host into a generic self-hosted Actions runner as an implementation shortcut unless the user explicitly chooses that broader authority model.
