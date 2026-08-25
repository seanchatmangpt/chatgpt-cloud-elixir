# Autonomic manufacturing substrate — v26.8.25

This directory is the semantic source for the portable ggen + SwarmSH capability closure used by `chatgpt-cloud-elixir`.

The governing pipeline is:

```text
admitted RDF capability graph
        ↓
pinned ggen bootstrap
        ↓
ggen deterministic projection
        ↓
capability-lock.json + topology
        ↓
exact ecosystem source checkout
        ↓
portable autonomic-manufacturing capsule
        ↓
fresh consumer replay
        ↓
receipt
```

`ontology.ttl` is authoritative for the external capability-source set. `versions.toml` contains only the minimal ggen bootstrap trust anchor needed to build the compiler that projects the full lock. `scripts/verify-autonomic-contract.py` mechanically requires the bootstrap ggen identity to match the ggen identity admitted in the ontology.

## Ecosystem closure

The admitted source graph binds exact revisions of:

- `ggen` — deterministic semantic manufacturing engine;
- `ggen-marketplace` — accumulated executable manufacturing knowledge;
- `ggen-create` — working-example-to-production-function capitalization;
- `ggen-legacy` — legacy contract reconstruction/reconstitution;
- `ggen-spec-kit` — RDF-first intent/specification admission;
- `swarmsh` — working Unix process/worktree/claim/PID execution ancestry;
- `swarmsh-v2` — typed coordination/worktree/shell-export ancestry.

The portable capsule includes the real ggen binary, the DfCM and Vision 2030 marketplace capital, an exact SwarmSH v1 source tree, an exact SwarmSH v2 source tree, and exact source archives for the other ggen ecosystem members.

## Authority boundary

The manufacturing graph and capsule are `CONSTRUCT_VERIFY` only. They do not grant ambient external DO authority. The fresh-consumer crown proves deterministic ggen manufacture and Unix process/worktree fan-out; it does not promote SwarmSH v2's incomplete runtime paths beyond their observed standing.

```text
SELECT / CONSTRUCT / VERIFY ≠ consequential DO
```

External actuation still requires the consuming environment's separate authority broker and evidence boundary.

## Manufacture

The canonical hosted path is `.github/workflows/autonomic-manufacturing.yml`.

The workflow:

1. runs the dependency-free bootstrap court;
2. fetches and builds the exact ggen bootstrap with its pinned Rust nightly;
3. runs real `ggen sync run` over this directory;
4. fetches every source named by the generated capability lock at its exact SHA;
5. manufactures the portable capability capsule;
6. extracts it into a fresh consumer;
7. executes the consumer verifier;
8. uploads the archive, digest, and replay receipt.

A green construction step is not, by itself, the consuming ChatGPT cloud crown. The final cloud standing requires importing that exact artifact and replaying `bash scripts/verify-autonomic-manufacturing.sh` in the target environment.
