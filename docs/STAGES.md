# TenderCouncil delivery stages

## Current inventory — 2026-08-10

| Area | Status | Evidence |
|---|---|---|
| Repository isolation/provenance | DONE | Dedicated TenderCouncil repository and preserved artifacts |
| Stage 1 monolith foundation | DONE / superseded | `contracts/tender_council_production.py` |
| Two-contract architecture | IMPLEMENTED locally | Core, Evaluator, typed interfaces, one-time binding |
| Closed snapshot digest | IMPLEMENTED locally | Canonical sorted-key JSON and Core digest |
| Cross-contract correlation | IMPLEMENTED locally | Finalized message path and nonce/digest guards |
| Evidence integrity/schema | IMPLEMENTED locally | Evaluator exact-byte hash and bounded manifest/evidence validation |
| Response/challenge/review | IMPLEMENTED locally | One bounded review round and external challenge hash boundary |
| Finalized settlement/refunds | IMPLEMENTED locally | Winner-price wei payout, remainder refund, serialized outflow lock, pending confirmation, balance delta |
| Generated artifacts/size gate | GREEN locally | Preferred 40 KB target; conservative 42 KB fallback remains below Bradbury boundary and exact RPC estimate is required |
| Direct tests | IMPLEMENTED locally | Existing direct suite plus real all-semantic-fail and financial simulator trials |
| Mutation/security tests | IMPLEMENTED locally | Original suite plus split, semantic NO_VALID_BID, challenge, integrity, payout, and outflow-lock mutants |
| Bradbury estimate-only pair probe | NEXT | Must run and record both exact estimates |
| Bradbury broadcast/E2E | BLOCKED BY REVIEW | Explicitly not authorized in this stage |
| Final UI | STOPPED | UI stop gate remains closed |

## Locked next gates

1. Run the full local lint, semantic, direct, parity, size, and mutation suite.
2. Run the exact no-broadcast Core/Evaluator Bradbury estimates.
3. Stop for architecture/deployment review.
4. Only after approval, perform one controlled two-contract deployment.
5. After review, prove finality, funded procurement, the 7200-second Bradbury
   response window, challenge path, and finalized settlement.

The UI cannot begin until the complete backend/security/Bradbury stop gate is
explicitly opened.
