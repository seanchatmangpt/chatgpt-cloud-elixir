# External reference checkouts (`.capability-sources/`, formerly documented as `vendors/`)

> **Naming correction (2026-08-29):** this page originally called the checkout
> directory `vendors/`, following the root `.gitignore`'s "vendored reference repos"
> entry and several `docs/errc-tracker.md` items about it. A repo-wide grep found `vendors`
> referenced nowhere in `manufacturing/` or `scripts/` — the directory the actual
> build tooling reads and writes is `.capability-sources/`
> (`scripts/build-autonomic-manufacturing.sh`'s `CAPABILITY_SOURCE_ROOT`, explicitly
> set to `$PWD/.capability-sources` by `.github/workflows/autonomic-manufacturing.yml`).
> `vendors/` in `.gitignore` is currently vestigial: nothing populates or reads a
> directory by that name. This page now documents `.capability-sources/`, the name
> that matches what actually runs; the evidence below (originally gathered against a
> checkout literally named `vendors/`, in an earlier session/environment) still
> applies to the *content* of the checkouts, just not to the directory name.

`.capability-sources/` holds local, exact-SHA-pinned checkouts of the external
repositories that `capsules/autonomic-manufacturing/capsule.toml` and
`manufacturing/` depend on (SwarmSH v1, SwarmSH v2, and the various `ggen*` ecosystem
sources). It is not committed source — `CAPABILITY_SOURCE_ROOT` defaults to
`$ROOT/.capability-sources` (overridable), is fetched fresh per build environment,
and is gitignored via its own root `.gitignore` entry (`/.capability-sources/`,
added alongside `/dist` and `/.capsule-build/`) separate from the older, currently
unused `vendors/` entry.

## Pinning contract

Each vendor is pinned by exact commit SHA in `manufacturing/ontology.ttl` (a
`cc:CapabilitySource` individual with `cc:commitSha`), restated in the generated
`manufacturing/generated/capability-lock.json`. As of this writing:

| Vendor | Repository | Pinned SHA |
|---|---|---|
| `swarmsh` | `seanchatmangpt/swarmsh` | `745008438b9493d31e8af3735ad6116ac01c150f` |
| `swarmsh-v2` | `seanchatmangpt/swarmsh-v2` | `02e5eaae14bd03a832c0f031acc56c6d4db3845e` |

`scripts/verify-autonomic-manufacturing.sh` (running inside a *built and extracted*
capsule, not against `.capability-sources/` directly — that script checks the
capsule's own internal `swarmsh/`/`swarmsh-v2/` layout staged by
`build-autonomic-manufacturing.sh`, per the Misdiagnosed entry in
`docs/errc-tracker.md`) re-checks source identity against the embedded capability
lock at consume-time.
Each checkout should be on its pinned SHA, not merely a branch that happened to be at
that SHA at fetch time — no automated check currently confirms detached-HEAD state
inside `.capability-sources/` before a build, so a stray `git pull` there could
silently drift.

## Signal-to-noise (from the 2026-08-26 ERRC domain review)

The only sweep with a real checkout on disk (`docs/errc-tracker.md`'s original
2026-08-26 domain review — gathered against a checkout literally named `vendors/`,
in a different session/environment than this page's naming correction above; not
re-verified in this pass) found:

- The SwarmSH checkout is ~264 files, but only 2 are load-bearing for this repo's own
  scripts/capsules: `coordination_helper.sh` and `real_agent_coordinator.sh`
  (referenced by `scripts/verify-autonomic-manufacturing.sh`). The rest is telemetry
  dumps, `.backup.*` copies of `coordination_helper.sh`, and speculative arxiv-paper
  drafts — upstream project content, not something this repo consumes.
- `swarmsh/backlog.yaml` is upstream "Scrum at Scale" planning content, over a year
  stale relative to when it was last reviewed, and unrelated to this repo's actual
  work.
- No equivalent per-file breakdown has been recorded for the `swarmsh-v2` or `ggen*`
  checkouts; treat their signal-to-noise ratio as unknown rather than assuming it
  matches `swarmsh`'s.

If you are trying to understand what the SwarmSH checkout actually contributes to a
build, start at `coordination_helper.sh` and `real_agent_coordinator.sh` and ignore
the rest of the tree.

## See also

- `docs/how-to/regenerate-autonomic-manufacturing-lock.md` — the fetch/build/verify
  procedure that consumes these checkouts.
- `manufacturing/ontology.ttl` — the authoritative pin source.
- `docs/errc-tracker.md`'s REDUCE and Misdiagnosed entries about the SwarmSH
  checkout — the evidence this page compiles from.
