# TenderCouncil delivery stages

## Current inventory — 2026-08-16

| Area | Status | Evidence |
|---|---|---|
| Repository isolation/provenance | DONE | Dedicated repository and preserved artifacts |
| Stage 1 monolith foundation | DONE / historical and superseded | `contracts/tender_council_production.py` |
| Two-contract architecture | FINALIZED | `TenderCouncilCore` plus bound `TenderCouncilEvaluator` |
| Closed snapshot digest | FINALIZED | `tendercouncil.snapshot.v1`, canonical sorted-key JSON |
| Cross-contract correlation | FINALIZED | Finalized-only messages and nonce/digest guards |
| Evidence integrity/schema | FINALIZED | Exact-byte SHA-256 and bounded v2.1 manifest/evidence validation |
| Response/challenge/review | FINALIZED | One bounded review round and external challenge hash boundary |
| Finalized settlement/refunds | FINALIZED | Winner-price payout, remainder/full refunds, serialized outflow lock |
| Generated v2.1 artifacts/size gate | GREEN | Recorded in the v2.1 deployment and size manifests |
| Local tests and security verification | RECORDED | CI workflow, probes, direct tests, and mutation tools |
| Bradbury Core deployment | FINALIZED | `0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd` |
| Bradbury Evaluator deployment | FINALIZED | `0x023AB3434761715a531884Ca0852aC14beE03acE` |
| Core/Evaluator binding | FINALIZED | `production_ready=true`, binding tx in release manifest |
| Canonical five-bid E2E | POST_SUBMISSION_OPTIONAL / PARKED | `E2E_STATUS = POST_SUBMISSION_OPTIONAL` |
| Frontend | OPTIONAL | No frontend is required for the contract release |

## Release status

`RELEASE BLOCKERS = none`. The submitted v2.1 deployment remains the current
release. The parked E2E is preserved post-submission validation, not an
unresolved release gate or a defect. This repository polish does not resume it,
create another tender, or broadcast another transaction.

The authoritative release details are in [docs/RELEASE.md](RELEASE.md). The
historical deployment and E2E records remain append-only provenance and must
not be selected as current addresses.
