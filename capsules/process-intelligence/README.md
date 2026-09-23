# process-intelligence capsule

This capsule makes the AshR2RML/ex4pm process-intelligence qualification loop executable in a restricted ChatGPT Linux container without direct Hex or GitHub network access.

## Bound runtime

The capsule deliberately uses the target-native runtime declared by `ash_r2rml/.tool-versions`:

- Erlang/OTP `27.2.4`;
- Elixir `1.18.4`.

This is a distinct lawful capsule variant. Existing ChatGPT cloud capsules continue to use OTP 29 / Elixir 1.20.2. A real attempted qualification on OTP 29 / Elixir 1.20.2 reached AshR2RML compilation and was falsified by Elixir 1.20 compiler warnings under the repository's required `--warnings-as-errors` gate. That compatibility world remains a separate target; this capsule does not suppress those warnings or weaken the target acceptance contract.

## Bound subjects

The source identities are reviewable in `capsule.toml` and are verified during manufacture before either project is built:

- `seanchatmangpt/ash_r2rml` at `7ce5ff63da03fcc3bb661890f51b0c9494147140` / tree `c576f44096b5af0e0ef89094a520de8e99c71819`;
- `seanchatmangpt/ex4pm` at `542cef83cb8ce5aec6984c84c3234ca0f5ce2b2e` / tree `3ddcb90d49278444143f8af6be16d09603da9527`;
- dependency `seanchatmangpt/wasm4pm-compat` at `a1c98bb8f0b6f2f6efd39cba0bc48e1485f39193` / tree `084e0280666038d779ef0e6b57538ca83b47e319`.

`capsule.toml` is canonical for these identities. This list mirrors it.

### Re-pin qualification (2026-09-23)

On 2026-09-23 these pins were rebuilt with OTP 27.2.4 / Elixir 1.18.4, and a fresh consumer ran `run-offline.sh` in `namespace_offline` mode: **ALIVE** (archive sha256 `e426c2466d0342d0562c8d05d3db654f4a361a063c9980ac6d028e2efcd007d6`, 249,837,952 bytes).

The candidate heads were `ash_r2rml` `241342a9` (51/51 fortune5 tests pass), `ex4pm` `426455b6`, and `wasm4pm-compat` `c4fadd8e`. They are **not admitted**: ex4pm `mix verify` is `BUILD_BROKEN` at that SHA because of three upstream test defects:

1. `test/information/frontier_release_test.exs` defines `defp binding`, which collides with `Kernel.binding/0`, so the file does not compile.
2. Five `:real_wasm` test modules return `:skip` / `{:skip, …}` from `setup`, which ExUnit rejects.
3. Two `:integration` tests read `/Users/sac/xaas/priv/ocel/ash-actions.ndjson`.

The bridge harness itself passed against the candidates. Re-qualify after those defects are fixed upstream. The candidate ex4pm also no longer uses the `wasm4pm-compat` path dependency, and it adds a Rust NIF build (`ggen_igniter`).

The subjects are built as independent Mix projects with their own lockfiles, `deps`, and `_build` trees. They are deliberately not collapsed into one dependency graph.

## Offline crown

Fresh consumer replay performs:

1. capsule manifest/runtime verification;
2. `ash_r2rml` warnings-as-errors compilation;
3. the 51-test `test/fortune5/` ETS corpus;
4. ex4pm `mix verify`;
5. a black-box bridge over the same committed OCEL world:
   - AshR2RML validates and reconstructs the event log;
   - ex4pm ingests it through the public API, discovers a DFG, performs conformance, and simulates the model;
   - an independent bridge verifier requires event/object parity, exact known DFG edges, fitness `1.0`, ALIVE analytical standings, and the expected simulation language.

The bridge produces `harness/process-lab-receipt.json`, and the outer consumer verifier binds its digest into `receipt.json`.

## Scope boundary

`ALIVE` for this capsule means the exact offline in-memory process-intelligence crown above executed after transport into a fresh consumer. It does **not** manufacture standing for Docker, PostgreSQL, Ontop, or other external-service crowns. Those remain separately admitted and must be executed where those services exist.

## Manufacture

```bash
scripts/build-process-intelligence.sh
```

The standard `Build Capsules` and `Verify Capsules` workflows include this variant and select its declared runtime independently from the other capsule variants.
