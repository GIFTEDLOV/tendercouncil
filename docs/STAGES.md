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
| Bradbury replacement pair deployment/binding | DONE | Corrected finalized Core, Evaluator, and one-time binding are recorded in `artifacts/tender_council_bradbury_corrected_deployment.json` |
| Bradbury funded canonical E2E | IN PROGRESS | `analytics-dashboard-2026` is funded/open; five finalized immutable bid submissions are recorded; deadline wait is active |
| Bradbury evaluation/settlement proof | PENDING | Close, asynchronous evaluation, challenge/review, exact payout, remainder refund, and final settlement remain to be recorded |
| Final UI | STOPPED | UI stop gate remains closed |

## Locked next gates

1. Wait for the immutable live bidding deadline and close the funded tender.
2. Record the finalized Core → Evaluator → Core evaluation graph and canonical
   classifications.
3. Prove the 7200-second response window, authenticated challenge, bounded
   review, exact winner-price payout, and exact buyer remainder refund.
4. Run the final local/CI/security/provenance release gate.

The UI cannot begin until the complete backend/security/Bradbury stop gate is
explicitly opened.
