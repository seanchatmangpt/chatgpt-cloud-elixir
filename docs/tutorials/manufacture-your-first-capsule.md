# Tutorial: Manufacture and Verify Your First Capsule

This tutorial walks you through manufacturing a `beam-core` capsule from source,
then verifying it as a genuinely fresh consumer would — not by trusting the build
workspace, but by extracting the archive into a clean directory and replaying the
real acceptance command against it. By the end you will have a working, portable
Erlang/Elixir/Mix/Hex/Rebar runtime tarball on disk and a `receipt.json` proving it
passed its own acceptance test.

`beam-core` is the base capsule: it contains only the portable OTP/Elixir/Mix
runtime plus a `mix_smoke` fixture project, no Ash packages. It has no dependency
on any other capsule, which makes it the fastest one to manufacture end to end.

## Prerequisites

You need these on `PATH`: `erl`, `elixir`, `mix`, `python3`, `tar`, `gzip`,
`sha256sum`. Their versions should match `versions.toml`'s `[runtime]` table
(`otp = "29.0"`, `elixir = "1.20.2"` at the time of writing) unless you override
them with `CAPSULE_OTP_OVERRIDE` / `CAPSULE_ELIXIR_OVERRIDE`.

You need a checkout of this repository, `chatgpt-cloud-elixir`.

## Step 1: Make the scripts executable

```bash
cd chatgpt-cloud-elixir
chmod +x scripts/*.sh
```

## Step 2: Bind the capsule identity to the exact commit

The build records the exact source commit the capsule was built from. In CI this
is set automatically for you; when building locally, set it yourself:

```bash
export GITHUB_SHA="$(git rev-parse HEAD)"
```

## Step 3: Build the capsule

```bash
scripts/build-capsule.sh beam-core
```

What this does, concretely: it stages the `fixtures/mix_smoke` fixture into a
temporary Mix project (generating `mix.exs` on the fly from `capsules/beam-core/
capsule.toml`'s `packages`/`required_modules` list — that file is not checked in),
runs `mix deps.get`, `MIX_ENV=test mix compile --warnings-as-errors`, and
`MIX_ENV=test mix test` against it, then copies the real OTP/Elixir/Mix/Hex/Rebar
tree plus the built project, scripts, verifier, and `source/{capsule,versions}.toml`
into a tarball. The archive path is printed on stdout, e.g.:

```
dist/chatgpt-cloud-elixir-beam-core-otp29-elixir1.20.2-linux-x86_64.tar.gz
```

A `.sha256` sidecar is written next to it, and a `build-receipt.json` is written
recording the build phase's own result. That build-receipt always claims
`standing: "ALIVE"` for the *construction* step only — it is not the capsule's
final standing. The final standing comes only from Step 4 below, run against a
fresh extraction.

## Step 4: Verify a fresh extracted consumer

Never trust the build workspace as proof the capsule works — extract it fresh,
exactly as a downstream consumer would:

```bash
archive="$(ls dist/chatgpt-cloud-elixir-beam-core-*.tar.gz)"
rm -rf consumer && mkdir consumer
tar -xzf "$archive" -C consumer

CAPSULE_ARCHIVE_DIGEST="$(sha256sum "$archive" | awk '{print $1}')" \
  bash consumer/scripts/run-offline.sh
```

`run-offline.sh` forces UTF-8 filename handling (`ELIXIR_ERL_OPTIONS=+fnu`), then
tries `unshare -n` to run inside a real network namespace with no network access;
if `unshare` isn't available it falls back to pointing `HTTP_PROXY`/`HTTPS_PROXY`/
`ALL_PROXY` at an unlistened loopback port (`127.0.0.1:9`) so any accidental
network call fails fast instead of silently succeeding. Either way, this is a
genuine offline-execution proof, not a documentation claim.

It then execs `scripts/verify-capsule.sh`, which runs, in order:

1. `elixir verifier/verify_manifest.exs manifest.json` — checks required manifest
   keys and a valid `[release] version`.
2. `elixir verifier/verify_runtime.exs manifest.json` — asserts the observed OTP/
   Elixir versions match the manifest's expected values, and that `erl`/`elixir`/
   `mix` resolve to capsule-local paths (catching a false pass caused by silently
   falling back to a host-installed BEAM toolchain).
3. `cd project && MIX_ENV=test mix compile --warnings-as-errors && MIX_ENV=test mix test`
   — the real acceptance command.

## Step 5: Read the result

```bash
cat consumer/receipt.json
```

You should see `"standing": "ALIVE"` with `acceptance_exit_code: 0`, alongside
`source_sha`, `release_version`, `capsule_name`, `capsule_archive_sha256`,
`manifest_sha256`, `network_mode`, `acceptance_command`, `verified_at`, and a
`replay` command string you (or anyone else) can run again to reproduce this exact
result.

This `receipt.json`, written by the *consumer-side* verify script against a fresh
extraction, is the only thing this repository's doctrine treats as proof the
capsule is `ALIVE`. The earlier `build-receipt.json` from Step 3 is construction
evidence only — see `docs/explanation/` for why the two are deliberately kept
separate.

## What's next

- To build a capsule with Ash packages instead (`ash-core`, `ash-postgres`,
  `ash-phoenix`, or `ash-full`), replace `beam-core` with that variant name in
  Steps 3–4 — the same script and verification flow applies to all of them.
- For the full field-by-field schema of `capsule.toml` and `versions.toml`, see
  `docs/reference/`.
- For the status vocabulary (`ALIVE`/`BLOCKED`/`BUILD_BROKEN`/etc.) and why the
  build-receipt and consumer-receipt are deliberately not the same claim, see
  `docs/explanation/`.
- To use a manufactured capsule as a dependency for a *different* target
  repository's own test suite, see
  `docs/tutorials/use-this-repo-as-a-substrate-for-another-repo.md`.
