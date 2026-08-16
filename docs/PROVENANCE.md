# TenderCouncil provenance

Provenance is append-only in intent. Failed deployments, validator failures,
and superseded releases are retained rather than erased.

## Repository anchor

- Repository: `GIFTEDLOV/tendercouncil`
- Branch: `main`
- Current production: Bradbury v2.1, Core/Evaluator finalized and bound
- Authoritative manifest: `artifacts/tender_council_bradbury_v21_deployment.json`
- Current release details: [docs/RELEASE.md](RELEASE.md)

The manifest records the source and deployable hashes, deployment receipts,
binding attempts, finalized binding readback, and `production_ready=true`.

## Existing evidence

The JSON and Markdown files under `artifacts/` preserve deployment addresses,
transaction IDs, validator votes, GenVM trace versions, and failure causes from
the earlier stages. Historical evidence is not silently promoted to current
release evidence. The test runner's ephemeral `.local/` output and runtime
journals are not release-controlled manifest inputs.

## Release history in brief

The original monolith and earlier v1 pair are historical/superseded. The v2
split work then added the Core/Evaluator trust boundary, immutable close
snapshot, finalized-only callbacks, exact-byte integrity checks, bounded
evaluation/review recovery, and deterministic settlement accounting.

The first corrected split pair exposed a snapshot-shape mismatch before web/LLM
evaluation. That failure remains in its timestamped artifact. The current v2.1
source and generated artifacts correct the boundary, reduce the model output to
bounded semantic judgments, enforce exact result partitions, and bind the
finalized Evaluator artifact hash once in Core. The first binding address
encoding failure and the successful `CalldataAddress` recovery are both kept in
the current deployment manifest.

## Current production evidence

The v2.1 Core and Evaluator deployments are finalized on Bradbury chain `4221`.
The binding transaction is
`0x186e412e4132763dc5b437a23944b30a5bffa5cd751c872b6e25ad5631c4acbf`; its
manifest readback records the bound Evaluator address, version,
`sha256:e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b`,
and `get_production_ready=true`.

These facts prove deployment/binding readiness. They do not assert that an
external proposal/evidence URL or model provider will be available for every
future tender.

## Parked canonical E2E

The canonical five-bid lifecycle is recorded in
`artifacts/tender_council_bradbury_v21_e2e_parked.json` with:

```text
E2E_STATUS = POST_SUBMISSION_OPTIONAL
```

Its journal is preserved. The parked run is not a release blocker, is not a
defect in the production binding, and is not required for this repository
completion. No new close/evaluation/challenge/review/settlement operation is
authorized by this document.

## Evidence preservation rules

- Do not overwrite timestamped failure artifacts.
- Keep historical addresses and versions labeled historical/superseded.
- Do not treat reconstructed diagnostics as sole proof of a chain fact.
- Keep the parked E2E journal untouched unless a separately authorized E2E
  operation explicitly requires it.
- Release-facing claims must match the current source, manifest, and
  `MANIFEST.sha256`.
