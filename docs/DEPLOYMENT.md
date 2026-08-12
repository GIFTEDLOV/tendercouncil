# TenderCouncil deployment

Target: GenLayer Bradbury testnet, chain ID `4221`, RPC
`https://rpc-bradbury.genlayer.com`, CLI `0.39.1`, genlayer-js `1.1.8`.

## Production pair

The production pair is deployed in this order:

1. `TenderCouncilCore` unconfigured.
2. Wait for finalized Core deployment and record its address.
3. `TenderCouncilEvaluator(core_address, tendercouncil.evaluator.v1)`.
4. Wait for finalized Evaluator deployment.
5. One-time Core `bind_evaluator(address, version, evaluator_code_hash)`, where
   the hash is the exact SHA-256 of the generated Evaluator deployment artifact.
6. Verify the finalized Core binding before opening any tender.

`deploy/deploy_split.py` remains the repeatable dry-run manifest generator and
does not broadcast. The controlled replacement pair was deployed through the
reviewed broadcast workflow already recorded in
`artifacts/tender_council_bradbury_replacement_deployment.json`; future
redeployments require a new reviewed release pair. The current E2E runner is
guarded to reuse the approved finalized pair and cannot deploy contracts.

## Generated artifacts and gates

Canonical sources:

- `contracts/tender_council_core.py`
- `contracts/tender_council_evaluator.py`

Generated artifacts:

- `artifacts/tender_council_core_deployable.py`
- `artifacts/tender_council_evaluator_deployable.py`

`tools/make_deployable.py` is the only generator. Parity is checked before
deployment. `node tools/split_deployment_size_check.mjs` uses the installed
GenLayer encoding path without RPC and fails if either outer payload reaches
the 42 KB conservative fallback (40 KB remains preferred). `node
tools/bradbury_split_deployment_probe.mjs` performs read-only
`eth_estimateGas` for both exact deployment transactions and never signs or
broadcasts.

Current local encoded sizes (historical baseline; regenerate after source
changes):

| Component | Source | Artifact | Outer deployment | Target |
|---|---:|---:|---:|---:|
| Core | current manifest | 40,527 | 40,772 exact probe / 41,551 conservative | <42,000 fallback |
| Evaluator | current manifest | 30,557 | 30,820 exact probe / 31,581 conservative | <42,000 fallback |

## Historical provenance

Failed monolith and evaluator-boundary attempts remain under `artifacts/`.
The earlier finalized pair in `artifacts/tender_council_bradbury_deployment.json`
is preserved as `FINALIZED_DEPLOYMENT_PROOF_SUPERSEDED_BEFORE_E2E`. The
corrected finalized pair is recorded in
`artifacts/tender_council_bradbury_corrected_deployment.json` and is the only
pair approved for the canonical E2E. The funded tender and subsequent live
evidence must be recorded in `artifacts/tender_council_bradbury_e2e.json` only
after completion.

The canonical live demo must use the 7200-second Bradbury response-window
configuration documented in `docs/BRADBURY_DEMO_POLICY.md`.

Release evidence must include finalized deployment receipts, Core binding,
funding, multiple bids, close, evaluation, provisional award, response window,
challenge/review where practical, award, settlement, finality, and post-
settlement balance/state verification.
