# Project #2 transport invariants

This file defines the narrow transport law between connected GitHub CRUD and the bounded Project-v2 proxy. It does not replace `project-memory/README.md`; Project #2 remains canonical memory.

## ERRC 80/20 closure

**Eliminate** duplicate actuation from exact request replay and generic `BUILD_BROKEN` classification for malformed caller input.

**Reduce** branch-local race windows, request ambiguity, and the distance from a bad transport envelope to a typed falsifier.

**Raise** deterministic identity, receipt provenance, replay safety, and one-project serialization.

**Create** a fail-closed transport gate whose output is either an admitted proxy execution or an explicit non-actuation receipt.

## Law

```text
raw request bytes
  -> UTF-8 admission
  -> JSON-object admission
  -> bounded proxy request admission
  -> exact-request replay check
  -> globally serialized Project #2 execution
  -> digest-bound receipt
```

The transport gate records two identities:

- `request_transport_sha256`: digest of the exact bytes committed to Git;
- `request_sha256`: digest of canonical JSON semantics with stable key ordering.

An existing `ALIVE` receipt is replay-idempotent only when request id, operation, and canonical request digest all match. In that case the gate returns success without another Project mutation.

Malformed JSON, invalid UTF-8, and non-object JSON roots are caller-input refusals. They must return `REFUSED` with `actuation_performed=false`; they are not proxy implementation failures.

All branches share the same workflow concurrency group for Project #2. Branch identity is transport topology, not an independent memory authority domain.

## Falsifiers

The transport invariant is falsified by any of the following:

1. the same admitted successful request actuates Project #2 twice;
2. malformed request bytes reach GraphQL;
3. malformed caller input is classified as proxy `BUILD_BROKEN`;
4. two branch workflows mutate Project #2 concurrently through this workflow;
5. a receipt omits both transport and canonical request identity after gated execution;
6. an `ALIVE` replay short-circuits when request id, operation, or canonical digest differs.

## Scoped crown

The gate can be called `ALIVE` only after the exact branch executes the unit court and one real Project #2 request traverses:

```text
request commit -> gate -> proxy -> Project #2 -> receipt commit
```

CI metadata alone is not the crown; the committed operation receipt is.
