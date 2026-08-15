# TenderCouncil deployment

Target: GenLayer Bradbury testnet, chain ID `4221`, RPC
`https://rpc-bradbury.genlayer.com`, CLI `0.39.1`, genlayer-js `1.1.8`.

## Production pair

The production pair is deployed in this order:

1. `TenderCouncilCore` unconfigured.
2. Wait for finalized Core deployment and record its address.
3. `TenderCouncilEvaluator(core_address, tendercouncil.evaluator.v2.1)`.
4. Wait for finalized Evaluator deployment.
5. One-time Core `bind_evaluator(address, version, evaluator_code_hash)`, where
   the hash is the exact SHA-256 of the generated Evaluator deployment artifact.
6. Verify the finalized Core binding before opening any tender.

`deploy/deploy_split.py` remains the repeatable dry-run manifest generator and
does not broadcast. The v1 deployment scripts and manifests are historical
evidence only. No v2 Core or Evaluator has been deployed. A future v2 release
requires a newly reviewed pair and may not reuse either historical address.
The v2 E2E runner cannot deploy contracts and rejects the historical pair.

## Generated artifacts and gates

Canonical sources:

- `contracts/tender_council_core.py`
- `contracts/tender_council_evaluator.py`

Generated artifacts:

- `artifacts/tender_council_core_v21_deployable.py`
- `artifacts/tender_council_evaluator_v21_deployable.py`

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
| Core v2 | current manifest | 40,054 | 40,292 exact encoding / 41,078 conservative | <42,000 fallback |
| Evaluator v2 | current manifest | 31,952 | 32,292 exact encoding / 32,976 conservative | <42,000 fallback |

## Historical provenance

Failed monolith and evaluator-boundary attempts remain under `artifacts/`.
The earlier finalized pairs and funded tenders are immutable v1 historical
evidence. In particular, Core `0x8d776cE2c5Ed60e5e9E229669eaf91DE7f3Ae257`
and Evaluator `0xcb4c472a9bB15103b885eC361701152Ec03b2681` must
not be rebound, reused, or mutated. A v2 E2E remains forbidden until every
pre-broadcast gate passes and a separately reviewed v2 deployment exists.

The canonical live demo must use the 7200-second Bradbury response-window
configuration documented in `docs/BRADBURY_DEMO_POLICY.md`.

Release evidence must include finalized deployment receipts, Core binding,
funding, multiple bids, close, evaluation, provisional award, response window,
challenge/review where practical, award, settlement, finality, and post-
settlement balance/state verification.
