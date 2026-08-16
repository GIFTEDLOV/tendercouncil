# TenderCouncil — Submission

## One-line summary

TenderCouncil is a GenLayer intelligent-contract system for authenticated,
evidence-backed procurement awards: deterministic escrow, lifecycle, and
settlement in Core; authenticated evidence retrieval and comparative
validator judgment in a bound Evaluator.

## Project

- **Name:** TenderCouncil
- **Category:** GenLayer Intelligent Contracts (procurement / evaluation)
- **Repository:** https://github.com/GIFTEDLOV/tendercouncil (branch `main`)
- **Network:** GenLayer Bradbury testnet (chain id `4221`)

## Production deployment (Bradbury v2.1)

| Item | Value |
| --- | --- |
| Core (`TenderCouncilCore`) | `0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd` |
| Evaluator (`TenderCouncilEvaluator`) | `0x023AB3434761715a531884Ca0852aC14beE03acE` |
| Evaluator schema version | `tendercouncil.evaluator.v2.1` |
| Evaluator code hash | `sha256:e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b` |
| Binding consensus tx | `0x186e412e4132763dc5b437a23944b30a5bffa5cd751c872b6e25ad5631c4acbf` |
| Binding outcome | `FINALIZED` / `AGREE` / `FINISHED_WITH_RETURN` / zero deterministic violations |
| `get_production_ready` | `true` |

## Architecture (concise)

Two contracts, one trust boundary:

- **Core** (`contracts/tender_council_core.py`) is the deterministic financial
  source of truth. It holds the buyer's escrow and owns the whole lifecycle —
  tender creation, bidding, close, evaluation orchestration, the guaranteed
  response window, at most one bounded integrity-checked challenge review, and
  finalized-only payout/refund settlement. Bid admissibility (budget, delivery,
  support, deadline, schema) is computed deterministically on chain.
- **Evaluator** (`contracts/tender_council_evaluator.py`) is permanently bound to
  Core. It authenticates each bidder's committed proposal and evidence by exact
  SHA-256 and schema, runs deterministic disqualification first, then performs
  the bounded comparative semantic judgment across the remaining candidates via
  GenLayer validators, and calls back into Core with a digest-verified result.

Core never trusts evidence merely because validators agree: a bidder's wallet
authenticates the offer, on-chain commitments bind proposal/evidence bytes, and
Core re-validates the evaluator result partition before recording a provisional
award.

## Why GenLayer

The hard procurement question is comparative — which compliant proposal best
satisfies one published rubric — which no single model or centralized committee
should decide unilaterally. GenLayer validators derive the bounded semantic
comparison under consensus, while Core keeps money and lifecycle fully
deterministic.

## Provenance

- Deployment record, both binding attempts, and readback evidence:
  `artifacts/tender_council_bradbury_v21_deployment.json`.
- The first binding reverted (evaluator address encoded as a raw string instead
  of a GenLayer `Address`); the recovery re-encoded it with the SDK's calldata
  `Address` wrapper and finalized cleanly. Both attempts are preserved.
- Contract quality gates (tests, mutation tests, state determinism, GenVM
  lint/validation, source⇄artifact parity, size gate, CI) pass for the deployed
  artifacts.

## End-to-end status

A canonical five-bid end-to-end run is **post-submission validation only**
(`E2E_STATUS = POST_SUBMISSION_OPTIONAL`) and is not part of the submission
gate. Its parked state and preserved journal are recorded in
`artifacts/tender_council_bradbury_v21_e2e_parked.json`.
