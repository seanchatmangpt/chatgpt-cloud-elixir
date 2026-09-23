# runtime/: committed ecosystem binaries

Everything a fresh Linux x86_64 cloud container needs to run the ecosystem immediately,
committed in binary form and pinned by digest. Written only by `scripts/runtime-admit.py`,
never by hand. `lock.json` is the authority for what is here.

## Up in one command (offline)

```bash
python3 scripts/ecosystem-up.py            # verify part + archive SHA-256, install, smoke-execute
source ~/.chatgpt-cloud/runtime/env.sh     # everything on PATH
python3 scripts/ecosystem-up.py --verify   # also run each capsule's own offline verifier
```

- Default prefix: `~/.chatgpt-cloud/runtime`. Override it with `--prefix` or `CHATGPT_CLOUD_RUNTIME_HOME`.
- Idempotent: a rerun at the same digests re-extracts nothing.
- `--env-file "$CLAUDE_ENV_FILE"` persists the activation for a Claude Code session.
- `--allow-hex-network` unsets `HEX_OFFLINE` for sessions that may still fetch new deps.
- Each artifact root is exported as `CHATGPT_CLOUD_<NAME>_ROOT`. Every capsule `activate`
  exports `CAPSULE_ROOT`, and the last one sourced wins.
- The receipt is written to `~/.chatgpt-cloud/runtime/ecosystem-up-receipt.json`. Each
  artifact gets one standing: `ALIVE`, `BUILD_BROKEN` (bad digest or smoke failure), or
  `BLOCKED` (parts not present, e.g. a sparse checkout).

## Artifacts

| Artifact | What it gives you | Built by |
| --- | --- | --- |
| `ggen` | ggen 26.9.21 manufacturing engine (`ggen sync run`, packs, receipts) | upstream release asset, byte-identical to `seanchatmangpt/ggen` v26.9.21 |
| `autonomic-manufacturing` | ggen, DfCM + Vision 2030 marketplace capital, SwarmSH v1 shell runtime, SwarmSH v2 typed source, and the 58-source capability lock bound by commit + tree SHA (identity profile) | `scripts/build-autonomic-manufacturing.sh` |
| `ash-full` | Erlang/OTP + Elixir + Mix + Hex + Rebar3, plus the compiled maximal Ash closure and its Hex package cache | `scripts/build-capsule.sh ash-full` |
| `wasm4pm-cli` | `wpm` 26.7.23: the **Rust** `crates/wasm4pm-cli` development surface (the public TypeScript `wpm` is not this) | cargo, exact SHA |
| `clnrm` | `clnrm`, `clnrm-lsp`: hermetic integration testing (needs OpenSSL 3) | cargo `--locked`, exact SHA |
| `affidavit` | `affi`, `affi-shell`: provenance receipt engine | cargo, exact SHA |
| `cargo-cicd` | `cargo-cicd`, `cicd-evidence-gen`, `cargo-cicd-lsp` | cargo `--locked`, exact SHA |
| `lsp-max` | `lsp-max-cli`, `lsp-max-specgen`, `lsp-max-mcp`, `lsp-max-lsif` | cargo, exact SHA |
| `clap-noun-verb` | `clap-noun-verb-gen` | cargo, exact SHA |
| `anti-llm-cheat-lsp` (opt-in) | admissibility canary LSP. Built with sibling sources outside its repo; see `lock.json` | cargo, exact SHA + recorded siblings |
| `swarmsh-v2-cli` (opt-in) | `swarmsh_cli` only. The declared v2 coordinator/agent binaries do not compile upstream | cargo, exact SHA |

Opt-in artifacts install with `--only <name>`. Host floor: built on Ubuntu 24.04. Most
binaries need glibc ≥ 2.39, and OTP crypto, `clnrm`, and `swarmsh_cli` need OpenSSL 3
(`libssl.so.3`). An older host reports `BUILD_BROKEN` at the smoke step rather than
failing silently.

Exact versions, source commits, digests, and admission-time consumer receipts are in
`lock.json`.

## A new Ash project with no network

The committed Hex cache holds exactly the admitted closure, so resolve against the admitted
lock:

```bash
source ~/.chatgpt-cloud/runtime/env.sh
mix new my_app && cd my_app
# add {:ash, "== <versions.toml pin>"} to deps in mix.exs
cp "$CHATGPT_CLOUD_ASH_FULL_ROOT/project/mix.lock" .
mix deps.get && mix compile      # served from $HEX_HOME; HEX_OFFLINE=1
```

This was observed inside `unshare -n` (no network at all) with `ash 3.33.9`: 16 packages fetched from the
cache with 0 Hex advisories, compile succeeded, and `Ash.Resource` loaded in about 80 s (mostly compilation).

## Admitting a new binary (producer)

```bash
python3 scripts/runtime-admit.py <name> <archive.tar.gz> \
  --version <v> --source-repo <owner/repo> --source-sha <40-hex> \
  --builder upstream-release|local-container|github-actions \
  --layout capsule|bin [--bin rel/path] --smoke "<cmd>" [--verify "<cmd>"] \
  [--evidence consumer-receipt.json] [--not-default]
python3 -m unittest tests/test_runtime_transport.py
```

Archives larger than 45 MiB are split into `.partNN` files, each digest-bound. Commit the
`lock.json` change and the parts together.
