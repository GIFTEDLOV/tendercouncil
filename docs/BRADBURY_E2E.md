# Bradbury E2E evidence

This document records the controlled production proof. Failed and transient
attempts remain under `artifacts/`.

## Current live run

The previously reviewed replacement pair is finalized and bound. Its first
funded E2E evaluation exposed a contract defect before any payout or refund;
the pair is preserved as deployment/finality evidence and will not be reused
for a corrected E2E:

- Core: `0xaf12cF3B7225c94E6674255780B16aDCfEb03E15`
- Evaluator: `0xEF30f069A8Be376D40F18758b9bfDa54D7c04Ec7`
- network: `testnet-bradbury`, chain `4221`
- evaluator version: `tendercouncil.evaluator.v1`
- response-window demo policy: `7200` seconds

The funded tender `analytics-dashboard-2026` is stuck in `EVALUATING` with an escrow of
`80_000_000_000_000_000` wei. Five distinct bidder wallets have submitted
immutable bid envelopes. The runner waits for the onchain bidding deadline;
close, evaluation, response, challenge, review, payout, refund, and final
settlement are not claimed until their finalized evidence is recorded.

The failed evaluation child is preserved in
`artifacts/tender_council_bradbury_e2e_failure_2026-08-12T070125233Z.json`.
Read-only tracing showed five deterministic-violation votes and a `KeyError`
because the Evaluator expected `bid.tender_id`, while Core's canonical snapshot
binds the tender ID once at the snapshot level and omits that redundant field.
No web call, LLM call, callback, payout, or refund occurred. The corrected
source now compares the manifest tender ID with the immutable snapshot tender
ID, and the release gate must pass before a new pair is deployed.

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

The superseded finalized pair and the E2E-defective replacement pair remain
historical evidence only. No frontend work has begun; the UI STOP GATE remains
closed until a corrected pair completes the backend proof and final security
review.
