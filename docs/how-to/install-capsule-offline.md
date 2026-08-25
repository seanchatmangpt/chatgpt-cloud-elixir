# How to install an already-built capsule in a restricted offline environment

Use this when you are a ChatGPT/Claude session running inside a restricted
cloud container (no apt/Hex/DNS access) and need a working BEAM/Ash runtime
that was manufactured elsewhere by this repo's GitHub Actions.

## Steps

1. Import the exact GitHub workflow artifact through the connected GitHub
   interface (see the README's "Quick start for ChatGPT users" section),
   and verify its digest before trusting it.

2. Install it:

   ```bash
   scripts/install-capsule.sh <archive.tar.gz> [destination]
   ```

   - If `archive.tar.gz.sha256` sits alongside the archive, the checksum is
     verified first (`BUILD_BROKEN` on mismatch); otherwise it extracts
     unconditionally.
   - Extracts (`tar -xzf`) into `DEST` (default
     `./chatgpt-cloud-elixir-capsule`).
   - Prints `installed=<abs path>` and `activate=source <abs path>/activate`.

3. Activate the capsule. This adds the capsule-local `erl`/`elixir`/`mix` to
   `PATH`, and sets `MIX_HOME`, `HEX_HOME`, `HEX_OFFLINE=1` — no system BEAM
   install required:

   ```bash
   source <dest>/activate
   ```

4. Inspect what you actually have before trusting it:

   ```bash
   bash <dest>/scripts/inspect-capsule.sh
   ```

   This prints `capsule_root`, the manifest sha256, the resolved
   `erl`/`elixir`/`mix` paths and versions, and the full `manifest.json`.

5. Replay the acceptance proof offline — this is the local evidence, not the
   CI green check:

   ```bash
   bash <dest>/scripts/run-offline.sh
   ```

   Writes `<dest>/receipt.json` with `standing` = `ALIVE` or `BUILD_BROKEN`
   and the real `acceptance_exit_code`.

## Service capsule variant: `postgres17`

Activation additionally exports `POSTGRES_ROOT`, `PGHOST=127.0.0.1`,
`PGPORT=55432`. Manage a real cluster (stored under `state/postgres`, or
`$POSTGRES_STATE_DIR`) with:

```bash
scripts/postgres-server.sh {init|start|stop|restart|status|env|psql}
```

Root-run consumers are demoted via `setpriv`. There is a Unix-socket
path-length guard (107-byte AF_UNIX limit) — if the computed socket path is
too long, the script refuses explicitly with
`REFUSED(POSTGRES_SOCKET_PATH_TOO_LONG)` rather than letting Postgres fail
opaquely.

## Manufacturing-graph variant: `autonomic-manufacturing`

Activation instead exports `GGEN_MARKETPLACE_ROOT`, `SWARMSH_ROOT`,
`SWARMSH_V2_ROOT`, and puts `bin/ggen` + `swarmsh/` on `PATH`. Replay with:

```bash
bash scripts/verify-autonomic-manufacturing.sh
```

This capsule has `authority_ceiling = CONSTRUCT_VERIFY` — it proves
manufacture/fan-out capability only; it grants zero cloud credentials, no
repository merge authority, and no external API authority (`do_authority:
false` in its receipt).

## See also

- [Build a capsule from scratch and verify it locally](build-a-capsule.md)
- [Check whether a capsule is ALIVE vs PARTIAL_ALIVE vs BUILD_BROKEN](check-capsule-standing.md)
- [Bootstrap this repo as a substrate against a target repo](bootstrap-as-substrate-for-a-target-repo.md)
