# Committed runtime: the ERRC grid

Goal: a fresh cloud container (ChatGPT cloud, Claude Code on the web, any Linux x86_64
sandbox) goes from `git clone` to a working ecosystem (ggen, OTP/Elixir/Mix/Hex/Rebar, and
the admitted Ash closure) in seconds, with no build, no package fetch, and no expiring
artifact import.

```bash
git clone --depth 1 https://github.com/seanchatmangpt/chatgpt-cloud-elixir
cd chatgpt-cloud-elixir
python3 scripts/ecosystem-up.py          # verify digests offline, install, smoke-execute
source ~/.chatgpt-cloud/runtime/env.sh   # ggen, erl, elixir, mix on PATH
```

## Eliminate

| What | Why it goes |
| --- | --- |
| Building before first use (ggen `cargo build` ≈14 min in CI, OTP/Elixir install, `mix deps.get` + compile) | Binaries are manufactured once, admitted with digests, and committed. |
| Expiring workflow artifacts (14-day retention) as the only way a container gets a capsule | Committed files are reachable through `git clone` and through the GitHub connector's file reads. |
| The connector artifact-import hop as a precondition for execution | `ecosystem-up.py` reads the parts straight out of the checkout. |
| Re-shipping sources git already transports | The autonomic capsule's `identity` profile binds all 65 sources by commit + tree SHA instead of carrying 395 MB of source archives. |
| Ambient "latest" | Every artifact is pinned by archive SHA-256, part SHA-256, and exact source commit. |
| Dependence on Git LFS endpoints and quotas | Capability sources are LFS pointer-identity only (`cc:lfsObjectPolicy`). Committed runtime parts are plain blobs, and admission refuses LFS routing. `ggen-marketplace` exhausting its LFS budget on 2026-09-24 broke CI until this became law. |

## Reduce

| What | To |
| --- | --- |
| Time to ready | One command. Measured cold start of all three default artifacts from a clean copy inside `unshare -n` (no network at all), digests verified: 7.1 s. Adding `--verify` (each capsule's own offline verifier) brings it to about 6 s warm. |
| Duplicate BEAM runtimes | One default OTP 29.1.1 / Elixir 1.20.4 runtime (`ash-full`, a superset of `beam-core`). |
| Committed file size | Parts of at most 45 MiB (GitHub hard-rejects files over 100 MB; connector-friendly). |
| Autonomic capsule | 408 MB full profile (CI artifact) → 16 MB identity profile (committed). |
| Host floor | Everything is built on Ubuntu 24.04: glibc ≥ 2.39 for most binaries, OpenSSL 3 for OTP crypto, `clnrm`, and `swarmsh_cli`. The floor is recorded, not hidden. |

## Raise

| What | How |
| --- | --- |
| Evidence per binary | `runtime/lock.json` records source repo + SHA, builder (`upstream-release` / `local-container` / `github-actions`), origin URL, archive + part digests, and the admission-time consumer replay receipt. |
| Independent replay | `.github/workflows/runtime-integrity.yml` installs every committed artifact on a clean GitHub runner and runs each capsule's own offline verifier. |
| Standing honesty | `ecosystem-up.py` reports `ALIVE` only for digest-verified, smoke-executed artifacts. Absent parts (sparse checkout) are `BLOCKED` and tampered parts are `BUILD_BROKEN`. |
| Currency | `scripts/refresh-capability-sources.py` reports CURRENT / DRIFT / BLOCKED for all 58 admitted repos in one command. |
| Security posture | Offline replay of the committed Hex cache surfaced Hex advisories against the old pins. Every `versions.toml` package pin now has zero OSV advisories at admission: ash 3.33.9, ash_authentication 5.0.0-rc.14, ash_ai 1.1.1, … on OTP 29.1.1 / Elixir 1.20.4. |

## Create

- `runtime/` as a committed binary projection, written only by `scripts/runtime-admit.py`.
  It is never hand-edited, which matches the repo's rule that projections are regenerated,
  not maintained.
- `scripts/ecosystem-up.py`: an offline, idempotent consumer. `--env-file "$CLAUDE_ENV_FILE"`
  lets a Claude Code SessionStart hook put the runtime on PATH for a whole session.
- The `identity` source profile for the autonomic-manufacturing capsule.

## Tranche status

`runtime/lock.json` is authoritative. It lists what is committed now, and `runtime/README.md`
summarizes it.

Backlog, in priority order:

1. ~~Ecosystem Rust CLIs~~: done. `wasm4pm-cli`, `clnrm`, `affidavit`, `cargo-cicd`,
   `lsp-max`, and `clap-noun-verb` are committed and default. `anti-llm-cheat-lsp` and
   `swarmsh-v2-cli` are opt-in. Remaining: the public TypeScript `wpm`, and a
   musl/older-glibc rebuild if hosts older than glibc 2.39 matter.
2. `process-intelligence` (OTP 27.2.4 / Elixir 1.18.4 variant with `ash_r2rml` + `ex4pm`
   compiled closures). It was re-qualified ALIVE at its current pins on 2026-09-23 (250 MB). It is
   not committed because it would add 250 MB to every clone for a specialist lab. It should
   ship as a non-default artifact once clones can skip it (sparse checkout or a dedicated
   runtime branch).
3. BEAM applications from the ecosystem (`beam4pm`, `ex4pm`, `ggen_igniter`, `xaas`) as
   compiled closures on the committed OTP 29 runtime.
4. JS closures (`unrdf`, `unjucks`, `gitvan`), Python wheels (`dspygen`, `autotel`), and
   the Lean toolchain for `mfact`.
5. A CI lane that manufactures and admits binaries on `github-actions` runners so
   provenance does not depend on a single container.

## Boundaries that do not move

- Admission never grants DO authority. Everything here is SELECT / CONSTRUCT / VERIFY.
- Committed binaries never contain credentials, tokens, or runner identity.
- A committed binary is not a crown for a target repository. The crown is still the
  target's exact acceptance command run with the admitted capsule in the consuming
  container.
