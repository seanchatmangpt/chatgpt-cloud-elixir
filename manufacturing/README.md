# Autonomic manufacturing substrate — v26.9.23

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

The admitted source graph binds exact revisions of 58 public `seanchatmangpt` repositories, grouped by capital class:

- **manufacturing core** — `ggen` (deterministic semantic manufacturing engine), `ggen-marketplace`, `ggen-create`, `ggen-legacy`, `ggen-spec-kit`, `swarmsh`, `swarmsh-v2`;
- **ecosystem composition hubs** — `ggen-ecosystem`, `chatman-ecosystem`, `gym-ecosystem`;
- **manufacturing extensions and semantic substrate** — `ggen_igniter`, `ggen-skills`, `agile-protocol-specification`, `clap-noun-verb`, `unjucks`, `gitvan`, `dspygen`, `open-ontologies`, `unrdf`;
- **BEAM / Ash family** — `xaas`, `ash_surface`, `ash_a2a`, `ash_pplan`, `ash_expo`, `ash_planning_center`, `ash_supabase`, `ash_ex4pm`, `ash_r2rml`;
- **process intelligence** — `beam4pm`, `ex4pm`, `wasm4pm`, `wasm4pm-compat`, `pm4wasm`, `process-intelligence`, `mfact`, `autotel`;
- **gyms, forward deployment, planning** — `gymact`, `autofde-lab`, `autofde`, `ferroplan`, `fdegym`, `SREGym`, `lifegym`, `ww3gym`, `rrgym`, `biblegym`, `chatgptgym`, `claudecodegym`, `awesome-ai-gyms`;
- **verification, provenance, systems** — `affidavit`, `truex`, `clnrm`, `chicago-tdd-tools`, `lsp-max`, `anti-llm-cheat-lsp`, `cargo-cicd`, `bcinr`, `frozen-duckdb`.

Each source records `cc:admissionBasis`: `manufacturing-core`, `ecosystem-hub`, `ecosystem-lock:<hub>` when one of the three ecosystem locks pins it, `project-memory-workstream` when Project v2 memory tracks it, `beam-ash-family`, or `owner-project`.

Admission is a subset of observation. `cc:OwnerPublicCatalog` puts every public `seanchatmangpt` repository in observation scope, but only the enumerated sources are admitted. Private repositories are never named: observation authority is not publication authority.

The portable capsule includes the real ggen binary, the DfCM and Vision 2030 marketplace capital, an exact SwarmSH v1 source tree, an exact SwarmSH v2 source tree, and an exact `sources/<name>.tar.gz` archive of every other `source-snapshot` member. Each archive's SHA-256 is bound into `manifest.json` and re-checked by the consumer verifier. An archive proves exact-source presence only. It does not promote that member's own runtime crown.

A `source-reference` member (currently only `autofde-lab`, whose tree is ~530 MB of research-paper PDFs around ~30 MB of code) is fetched and identity-checked at construction but not shipped. Its commit and tree SHA are bound into `manifest.json` `source_identities`, which records construction identity for every admitted source.

## Keeping the graph current

```bash
python3 scripts/refresh-capability-sources.py            # CURRENT / DRIFT / BLOCKED per source; exit 1 on drift
python3 scripts/refresh-capability-sources.py --write    # re-pin drifted SHAs (and versions.toml bootstrap for ggen)
python3 scripts/verify-autonomic-contract.py             # bootstrap court
```

The refresh tool never admits or drops a source. Admission stays a reviewed edit of `ontology.ttl` plus `capsules/autonomic-manufacturing/capsule.toml` `required_sources`, and the court refuses any difference between the two. A ggen bump is refused unless the new revision still pins the bootstrap Rust toolchain.

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
