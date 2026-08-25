# Capsules

Reference for every capsule under `capsules/`: what each contains, what it depends
on, its acceptance command, and the full `capsule.toml` field schema (two shapes:
Mix/Elixir-runtime capsules and service capsules, plus the `process-intelligence` and
`autonomic-manufacturing` variants).

## Capsule table

| Capsule | Contains | Depends on | Acceptance command |
|---|---|---|---|
| `beam-core` | Portable OTP/Elixir/Mix/Hex/Rebar runtime + `mix_smoke` fixture project | none (base capsule) | `MIX_ENV=test mix compile --warnings-as-errors && MIX_ENV=test mix test` |
| `ash-core` | beam-core runtime + Ash, Spark, Reactor, Igniter compiled against `ash_ets_smoke` fixture | beam-core (same build path) | `MIX_ENV=test mix compile --warnings-as-errors && MIX_ENV=test mix test` |
| `ash-postgres` | ash-core packages + `ash_postgres` dep closure only (no server bundled) | `postgresql` service (e.g. `postgres17`) | `MIX_ENV=test mix compile --warnings-as-errors && MIX_ENV=test mix test` |
| `ash-phoenix` | ash-core packages + `ash_phoenix` | none extra | `MIX_ENV=test mix compile --warnings-as-errors && MIX_ENV=test mix test` |
| `ash-full` | Maximal admitted Ash ecosystem: ash, spark, reactor, igniter, ash_postgres, ash_phoenix, ash_json_api, ash_authentication, ash_oban, ash_state_machine, ash_archival, ash_money, ash_cloak, ash_graphql, ash_ai | `postgresql_for_service_level_tests` (external) | `MIX_ENV=test mix compile --warnings-as-errors && MIX_ENV=test mix test` |
| `postgres17` (kind = `service`) | Source-built portable PostgreSQL 17.11 with server helper scripts | none | `postgres --version`; `initdb`; `pg_ctl start`; real `CREATE`/`INSERT`/`SELECT`/`UPDATE`/`DELETE` SQL lifecycle; `pg_ctl stop` |
| `process-intelligence` | beam-core (OTP 27.2.4 / Elixir 1.18.4 variant) + exact-SHA source checkouts of `ash_r2rml` and `ex4pm` + an offline in-memory process-lab harness | beam-core build path; external repos pinned by commit + tree SHA | Per subject: `ash_r2rml` → `mix compile`/`mix test test/fortune5/`; `ex4pm` → `mix verify`; bridge → `bash harness/verify.sh` |
| `autonomic-manufacturing` | Real `ggen` binary + ggen-marketplace capital (DfCM pack, Vision 2030 package) + exact SwarmSH v1 source tree + SwarmSH v2 typed source + tarred source snapshots of ggen-create/ggen-legacy/ggen-spec-kit | Bootstrap ggen build (pinned Rust nightly) + `manufacturing/ontology.ttl`-driven capability lock; `authority_ceiling = CONSTRUCT_VERIFY` (no DO authority) | `bin/ggen --help`; `bash scripts/verify-autonomic-manufacturing.sh` |

## `capsule.toml` field reference

Two base shapes exist, plus two capsule-specific extensions.

### Shape A — Mix/Elixir-runtime capsule

Used by: `beam-core`, `ash-core`, `ash-postgres`, `ash-phoenix`, `ash-full`.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | Schema version of this file (`1`) |
| `name` | string | Capsule name, matches the directory name |
| `description` | string | Free-text description of the execution closure |
| `fixture` | string | Directory under `fixtures/` copied as the Mix project skeleton |
| `packages` | [string] | Package names, each a key into `versions.toml`'s `[packages]` table |
| `required_modules` | [string] | Elixir module names asserted loadable in the generated test |
| `requires_services` | [string] | External service capsule names required (e.g. `["postgresql"]` for `ash-postgres`); empty for most |
| `acceptance` | [string] | Ordered list of shell commands that constitute the acceptance test |

### Shape B — Service capsule

Used by: `postgres17`.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | Schema version (`1`) |
| `kind` | string | `"service"` |
| `name` | string | Capsule name |
| `description` | string | Free-text description |
| `version_key` | string | Key into `versions.toml`'s `[services]` table |
| `source_url_template` | string | URL template for fetching the source tarball, `{version}` substituted |
| `source_sha256` | string | Pinned source tarball digest, verified before building |
| `configure` | [string] | `./configure` flags passed at build time |
| `listen` | string | Bind address for the built server (`127.0.0.1`) |
| `default_port` | int | Default listen port (`55432`) |
| `acceptance` | [string] | Ordered acceptance steps (version check, `initdb`, `pg_ctl start`, CRUD SQL lifecycle, `pg_ctl stop`) |

### Shape C — `process-intelligence` (Mix-shaped base + nested subject/lab tables)

| Field | Type | Meaning |
|---|---|---|
| `schema_version`, `name`, `fixture` | — | Same meaning as Shape A |
| `[runtime]` `otp` | string | Pinned OTP version for this capsule specifically (`27.2.4`), overriding `versions.toml`'s default |
| `[runtime]` `elixir` | string | Pinned Elixir version for this capsule specifically (`1.18.4`) |
| `[subjects.<name>]` `repository` | string | Git URL of the external subject repo |
| `[subjects.<name>]` `sha` | string | Exact pinned commit SHA |
| `[subjects.<name>]` `tree_sha` | string | Exact pinned tree SHA — both `sha` and `tree_sha` are independently re-verified via `git rev-parse` after checkout |
| `[subjects.<name>]` `build_acceptance` | [string] | Acceptance commands run at build time |
| `[subjects.<name>]` `consumer_acceptance` | [string] | Acceptance commands re-run again at consumer replay time |
| `[process_lab]` `world` | string | Path to the lab world definition (`harness/world.json`) |
| `[process_lab]` `verifier` | string | Path to the lab verifier script (`harness/verify.sh`) |
| `[process_lab]` `standing_scope` | string | Named scope this capsule's standing is bounded to (`offline_in_memory_process_intelligence`) |
| `[process_lab]` `external_crowns` | [string] | Named boundaries explicitly NOT proven by this capsule (e.g. `["postgresql", "ontop", "docker"]`) |

### Shape D — `autonomic-manufacturing` (distinct schema, no `packages`/`fixture`)

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | Schema version (`1`) |
| `name` | string | `"autonomic-manufacturing"` |
| `authority_ceiling` | string | Hard authority cap, `"CONSTRUCT_VERIFY"` |
| `source_project` | string | Source project directory this capsule manufactures from (`"manufacturing"`) |
| `generated_contract` | string | Path to the generated capability-lock artifact this capsule consumes (`manufacturing/generated/capability-lock.json`) |
| `required_sources` | [string] | External ecosystem sources this capsule must fetch (`ggen`, `ggen-marketplace`, `ggen-create`, `ggen-legacy`, `ggen-spec-kit`, `swarmsh`, `swarmsh-v2`) |
| `required_host_commands` | [string] | Host commands that must be present (`bash`, `python3`, `git`, `tar`, `gzip`, `sha256sum`) |
| `acceptance` | [string] | `["bin/ggen --help", "bash scripts/verify-autonomic-manufacturing.sh"]` |
| `standing` | string | Self-declared default field in the file (`"UNKNOWN"`) — not the runtime-observed standing, which is computed by the verify script |
| `notes` | string | Free-text notes |

See also: `docs/explanation/` for why capsules are structured this way (offline law,
authority ceiling rationale); `docs/how-to/` for the step-by-step build/verify/install
workflow.
