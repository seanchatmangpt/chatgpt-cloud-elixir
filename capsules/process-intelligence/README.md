# process-intelligence capsule

This capsule makes the AshR2RML/ex4pm process-intelligence qualification loop executable in a restricted ChatGPT Linux container without direct Hex or GitHub network access.

## Bound runtime

The capsule deliberately uses the target-native runtime declared by `ash_r2rml/.tool-versions`:

- Erlang/OTP `27.2.4`;
- Elixir `1.18.4`.

This is a distinct lawful capsule variant. Existing ChatGPT cloud capsules continue to use OTP 29 / Elixir 1.20.2. A real attempted qualification on OTP 29 / Elixir 1.20.2 reached AshR2RML compilation and was falsified by Elixir 1.20 compiler warnings under the repository's required `--warnings-as-errors` gate. That compatibility world remains a separate target; this capsule does not suppress those warnings or weaken the target acceptance contract.

## Bound subjects

The source identities are reviewable in `capsule.toml` and are verified during manufacture before either project is built:

- `seanchatmangpt/ash_r2rml` at `a3445b7b252514880cd0f3c9843c0353b0385af1` / tree `d76b113d16aeecd47d246cac5e18619a8bd4be88`;
- `seanchatmangpt/ex4pm` at `f4f8776e66af6f0704407827635a446a5df7595b` / tree `3de6002793cdd38e205a710dcb274bfb1dd704c9`.

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
