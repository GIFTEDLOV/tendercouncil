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
| Generated v2 artifacts/size gate | GREEN locally | Exact encoded Core 40,292 bytes and Evaluator 32,292 bytes; both below the 42 KB fail-closed boundary |
| Direct tests | IMPLEMENTED locally | Existing direct suite plus real all-semantic-fail and financial simulator trials |
| Mutation/security tests | IMPLEMENTED locally | Original suite plus split, semantic NO_VALID_BID, challenge, integrity, payout, and outflow-lock mutants |
| Five-validator GenVM simulation | GREEN locally | Generated Core + Evaluator finalize 5/5 AGREE through evaluation/callback, `NO_VALID_BID`, malformed evaluation/retry, review/callback, malformed review/retry, and stale/duplicate rejection; pinned calldata agrees at every captured boundary |
| Bradbury exact estimate gate | GREEN / NO BROADCAST | Core `0x1ea6b25`, Evaluator `0x18b01b8`; both RPC estimates returned HTTP 200 without signing |
| Historical v1 pair/funded tenders | PRESERVED / BLOCKED | Existing Core/Evaluator and tenders are immutable evidence and must not receive new transactions |
| Bradbury v2 deployment/binding | NOT STARTED | No v2 Core or Evaluator has been deployed |
| Bradbury v2 canonical E2E | NOT ALLOWED | No v2 tender exists; pre-broadcast and multi-validator gates remain closed |
| Final UI | STOPPED | UI stop gate remains closed |

## Locked next gates

1. Review the exact v2 sources, artifacts, hashes, proof artifacts, and CI.
2. Commit the reviewed tree so the clean-worktree release preflight can bind an
   immutable HEAD to the generated artifacts.
3. Explicitly open the v2 deployment gate; deploy and bind a new pair only.
4. Reconcile the durable journal before every later E2E write.

The UI cannot begin until the complete backend/security/Bradbury stop gate is
explicitly opened.
