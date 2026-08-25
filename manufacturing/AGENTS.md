# Manufacturing agent contract

## Canonical truth

`ontology.ttl` is the canonical external capability graph. Generated files under `manufacturing/generated/` are projections and must never be hand-maintained.

`versions.toml [bootstrap]` is a deliberately minimal bootstrap exception: it pins the exact ggen compiler revision/toolchain required before the ontology can project the complete capability lock. `scripts/verify-autonomic-contract.py` must refuse any bootstrap/ontology identity drift.

## Required implementation path

1. Change admitted semantics in `ontology.ttl` or projection law in `ggen.toml`/queries/templates.
2. Run the bootstrap court.
3. Build the exact admitted ggen revision.
4. Run real `ggen sync run` from `manufacturing/`.
5. Never manually repair generated projections.
6. Fetch external ecosystem sources only at the exact SHAs emitted by the generated lock.
7. Manufacture and fresh-consumer replay the capsule.
8. Report standing from observed execution, not file existence.

## DfCM law

Preserve alternatives and maximize lawful executable capability closure. Do not collapse SwarmSH v1 and v2 into one claim: v1 supplies working shell/process ancestry; v2 supplies typed architecture ancestry until its runtime paths independently qualify.

## Authority

This surface is SELECT / CONSTRUCT / VERIFY only. `CONSTRUCT_VERIFY` is the maximum authority ceiling. No ontology, generated manifest, capsule, or receipt may silently grant cloud credentials, repository merge authority, external API authority, or consequential DO.

## Gall / Rice discipline

Use the exact working ggen, marketplace, ggen-create, ggen-legacy, ggen-spec-kit, SwarmSH, and SwarmSH-v2 revisions as ancestry. Do not replace them with newly invented facsimiles. A generated artifact is not evidence of arbitrary semantic correctness; standing requires the named falsifiers and exact-subject replay.
