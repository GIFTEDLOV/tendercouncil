# Bradbury E2E evidence

This document records the controlled production proof. Failed and transient
attempts remain under `artifacts/`.

## Current live run

The reviewed replacement pair is finalized, bound, and reused without
redeployment:

- Core: `0xaf12cF3B7225c94E6674255780B16aDCfEb03E15`
- Evaluator: `0xEF30f069A8Be376D40F18758b9bfDa54D7c04Ec7`
- network: `testnet-bradbury`, chain `4221`
- evaluator version: `tendercouncil.evaluator.v1`
- response-window demo policy: `7200` seconds

The funded tender `analytics-dashboard-2026` is OPEN with an escrow of
`80_000_000_000_000_000` wei. Five distinct bidder wallets have submitted
immutable bid envelopes. The runner waits for the onchain bidding deadline;
close, evaluation, response, challenge, review, payout, refund, and final
settlement are not claimed until their finalized evidence is recorded.

The recovery runner reads the existing tender and bid records and polls the
recorded transaction IDs, so an RPC outage cannot cause duplicate submissions.

## Preserved failures

- `artifacts/tender_council_bradbury_e2e_failure_2026-08-12T011155901Z.json`
  records a transient DNS/RPC fetch failure while polling bid finality.
- `artifacts/tender_council_bradbury_e2e_failure_2026-08-12T012007850Z.json`
  records a tooling readback assertion that incorrectly expected a zero Core
  balance after the tender had already been funded.
- `artifacts/tender_council_bradbury_e2e_failure_2026-08-12T013201964Z.json`
  records a tooling-only resume variable defect after all five bids had been
  read back.

These are preserved as provenance and are classified as RPC observability or
E2E tooling failures, not contract execution failures. No duplicate deployment
or duplicate bid was broadcast during recovery.

The superseded finalized pair remains historical evidence only. No frontend
work has begun; the UI STOP GATE remains closed until the complete backend proof
and final security review are green.
