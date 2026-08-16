# Bradbury E2E evidence

The current production release is the finalized and bound v2.1 pair:

- Core: `0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd`
- Evaluator: `0x023AB3434761715a531884Ca0852aC14beE03acE`
- chain: `4221`
- status: `production_ready=true`

This file keeps earlier E2E attempts as historical evidence and records the
current canonical run as `E2E_STATUS = POST_SUBMISSION_OPTIONAL`. The E2E is
not required for the release and this document does not authorize new writes.

This document records the controlled production proof. Failed and transient
attempts remain under `artifacts/`.

## Preserved v1 run

The following finalized pair and its failed evaluation are historical evidence
only. They are not authorized for any new transaction:

- Core: `0x8d776cE2c5Ed60e5e9E229669eaf91DE7f3Ae257`
- Evaluator: `0xcb4c472a9bB15103b885eC361701152Ec03b2681`
- network: `testnet-bradbury`, chain `4221`
- evaluator version: `tendercouncil.evaluator.v1`
- response-window demo policy: `7200` seconds

Its funded tenders, bids, failed child, and escrow state remain untouched. The
old statement in earlier run notes that no v2 pair existed is historical to
that checkpoint. The current v2.1 pair is separately documented in the
finalized deployment manifest, and the parked canonical run is recorded in
`artifacts/tender_council_bradbury_v21_e2e_parked.json`.

The earlier corrected pair remains preserved as a separate failed E2E artifact
and is not being reused:

- Core: `0xaf12cF3B7225c94E6674255780B16aDCfEb03E15`
- Evaluator: `0xEF30f069A8Be376D40F18758b9bfDa54D7c04Ec7`

The failed evaluation child is preserved in
`artifacts/tender_council_bradbury_e2e_failure_2026-08-12T070125233Z.json`.
Read-only tracing showed five deterministic-violation votes and a `KeyError`
because the Evaluator expected `bid.tender_id`, while Core's canonical snapshot
binds the tender ID once at the snapshot level and omits that redundant field.
No web call, LLM call, callback, payout, or refund occurred. The corrected
source now compares the manifest tender ID with the immutable snapshot tender
ID. The current run uses that corrected pair.

## Preserved failures

- `artifacts/tender_council_bradbury_e2e_failure_2026-08-12T011155901Z.json`
  records a transient DNS/RPC fetch failure while polling bid finality.
- `artifacts/tender_council_bradbury_e2e_failure_2026-08-12T012007850Z.json`
  records a tooling readback assertion that incorrectly expected a zero Core
  balance after the tender had already been funded.
- `artifacts/tender_council_bradbury_e2e_failure_2026-08-12T013201964Z.json`
  records a tooling-only resume variable defect after all five bids had been
  read back.
- `artifacts/tender_council_bradbury_e2e_failure_2026-08-12T070125233Z.json`
  records the finalized start transaction, failed Evaluator child, trace root
  cause, five deterministic-violation votes, and zero financial effect.

These are preserved as provenance and are classified as RPC observability or
E2E tooling failures, not contract execution failures. No duplicate deployment
or duplicate bid was broadcast during recovery.

The superseded finalized pairs remain historical evidence only. The canonical
v2.1 run is parked after its recorded open state; `E2E_STATUS =
POST_SUBMISSION_OPTIONAL`. No new live E2E, tender, or transaction is required
for the release.
