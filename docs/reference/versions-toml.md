# `versions.toml` Reference

`versions.toml` (repo root) is the canonical version-selection surface: capsule
definitions (`capsules/*/capsule.toml`) describe allowed capabilities and acceptance
commands, but the actual pinned version numbers live here and are read at build time
via `python3 -c 'import tomllib...'` snippets embedded in the build scripts.

## `schema_version`

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | Schema version of this file (`2`) |

## `[release]`

| Field | Type | Meaning |
|---|---|---|
| `version` | string | This release's CalVer identity (`YY.M.D` form, e.g. `"26.8.25"`), embedded in every manifest/receipt. Must equal `control-plane/mix.exs`'s declared `version:` — checked by `scripts/verify-release.py` and CI's `release-integrity.yml`. |
| `date` | string | Literal calendar date matching `version` (e.g. `"2026-08-25"`) — checked for drift by `scripts/verify-release.py` |

## `[bootstrap]`

Minimal trust anchor needed to build the `ggen` compiler, used only by the
`autonomic-manufacturing` capsule — a deliberate exception to "the ontology is
canonical" (the ontology can't be projected until the compiler that projects it
exists).

| Field | Type | Meaning |
|---|---|---|
| `ggen_repository` | string | Source repo for the ggen compiler (`"seanchatmangpt/ggen"`) |
| `ggen_sha` | string | Exact pinned commit SHA of the ggen compiler to build |
| `rust_toolchain` | string | Pinned Rust toolchain (e.g. `"nightly-2026-06-22"`) used to build ggen |

## `[runtime]`

Default OTP/Elixir pins used by `scripts/build-capsule.sh`. Overridable per capsule
(e.g. `process-intelligence` pins its own `otp`/`elixir` inside its own
`capsule.toml`'s `[runtime]` table, and `build-process-intelligence.sh` cross-checks
against this file's defaults).

| Field | Type | Meaning |
|---|---|---|
| `otp` | string | Default OTP version (e.g. `"29.0"`) |
| `elixir` | string | Default Elixir version (e.g. `"1.20.2"`) |

## `[packages]`

Exact pinned versions for every Ash-ecosystem package a `capsule.toml`'s `packages`
list can reference by name.

| Key | Example pin |
|---|---|
| `ash` | `"3.32.0"` |
| `spark` | `"2.7.2"` |
| `reactor` | `"1.0.6"` |
| `igniter` | `"0.8.3"` |
| `ash_postgres` | `"2.12.0"` |
| `ash_phoenix` | `"2.3.24"` |
| `ash_json_api` | `"1.7.1"` |
| `ash_authentication` | `"5.0.0-rc.12"` |
| `ash_oban` | `"0.8.13"` |
| `ash_state_machine` | `"0.2.13"` |
| `ash_archival` | `"2.0.3"` |
| `ash_money` | `"0.2.6"` |
| `ash_cloak` | `"0.3.1"` |
| `ash_graphql` | `"1.10.1"` |
| `ash_ai` | `"0.8.2"` |

## `[services]`

| Field | Type | Meaning |
|---|---|---|
| `postgresql_17` | string | Version key referenced by `postgres17/capsule.toml`'s `version_key` field (e.g. `"17.11"`) |

## `[platforms.linux_x86_64]`

| Field | Type | Meaning |
|---|---|---|
| `os` | string | `"linux"` |
| `arch` | string | `"x86_64"` |
| `status` | string | `"admitted"` — the only currently-admitted platform tuple. Any other platform tuple is `UNSUPPORTED`. |

## `[standing]`

| Field | Type | Meaning |
|---|---|---|
| `default` | string | `"UNKNOWN"` — the default standing before any evidence is gathered |
| `allowed` | [string] | The full closed vocabulary: `["UNKNOWN", "PARTIAL_ALIVE", "ALIVE", "BLOCKED", "BUILD_BROKEN", "UNSUPPORTED"]` — see `docs/reference/status-vocabulary.md` for precise definitions |

See also: `docs/reference/status-vocabulary.md` for the standing definitions,
`docs/reference/capsules.md` for how `[packages]`/`[runtime]`/`[services]` are
consumed by each capsule's `capsule.toml`.
