# TenderCouncil deployment

Target: GenLayer Bradbury testnet, chain ID `4221`, RPC
`https://rpc-bradbury.genlayer.com`. The current production pair is v2.1,
finalized, permanently bound, and documented in
[`docs/RELEASE.md`](RELEASE.md).

## Current production pair

| Component | Address | Status |
|---|---|---|
| `TenderCouncilCore` | `0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd` | FINALIZED |
| `TenderCouncilEvaluator` | `0x023AB3434761715a531884Ca0852aC14beE03acE` | FINALIZED |
| Core binding | `0x186e412e4132763dc5b437a23944b30a5bffa5cd751c872b6e25ad5631c4acbf` | FINALIZED / AGREE |

The original deployment sequence was:

1. Deploy `TenderCouncilCore` unconfigured and await finality.
2. Deploy `TenderCouncilEvaluator(core_address, tendercouncil.evaluator.v2.1)`
   and await finality.
3. Bind exactly once with `bind_evaluator(address, version,
   evaluator_code_hash)`, where the hash is the exact generated Evaluator
   artifact bytes.
4. Verify the finalized Core binding and `get_production_ready()` readback.

That sequence is historical release provenance. Do not execute it again for
this repository-polish task and do not reuse the production addresses for a
new deployment.

## Generated artifacts and gates

Canonical sources:

- `contracts/tender_council_core.py`
- `contracts/tender_council_evaluator.py`

Generated production artifacts:

- `artifacts/tender_council_core_v21_deployable.py`
- `artifacts/tender_council_evaluator_v21_deployable.py`

`tools/make_deployable.py` is the generator. `tools/split_size_check.py` checks
mechanical source/artifact parity and the conservative 42 KB outer target. The
production source/artifact hashes and final deployment readbacks are frozen in
`artifacts/tender_council_bradbury_v21_deployment.json`.

The deployment and split-probe scripts are operational provenance tooling. A
normal documentation or integration change must use the read-only checks in
[docs/CI.md](CI.md), not a deployment script.

## Historical provenance

Failed and superseded monolith, v1, and early v2/v2.1 deployment attempts
remain under `artifacts/` and are labeled historical. In particular, older
Core/Evaluator addresses must not be rebound, reused, or presented as current.
The canonical v2.1 E2E has `E2E_STATUS = POST_SUBMISSION_OPTIONAL` and is
parked; it is not a deployment prerequisite.
