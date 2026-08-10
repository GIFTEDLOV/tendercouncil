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
| Finalized settlement/refunds | IMPLEMENTED locally | Core-only transfer, pending confirmation, balance delta |
| Generated artifacts/size gate | GREEN locally | Both outer payloads below 40 KB target |
| Direct tests | PARTIAL | Core/Evaluator direct guards pass; simulator cross-contract coverage remains to be expanded |
| Mutation/security tests | PARTIAL | Existing monolith suite remains green; split-specific mutation harness remains to be expanded |
| Bradbury estimate-only pair probe | NEXT | Must run and record both exact estimates |
| Bradbury broadcast/E2E | BLOCKED BY REVIEW | Explicitly not authorized in this stage |
| Final UI | STOPPED | UI stop gate remains closed |

## Locked next gates

1. Run the full local lint, semantic, direct, parity, size, and mutation suite.
2. Run the exact no-broadcast Core/Evaluator Bradbury estimates.
3. Stop for architecture/deployment review.
4. Only after approval, perform one controlled two-contract deployment.
5. Prove finality, funded procurement, response window, challenge path, and
   finalized settlement.

The UI cannot begin until the complete backend/security/Bradbury stop gate is
explicitly opened.
