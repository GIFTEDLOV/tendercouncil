# TenderCouncil provenance

Provenance is append-only in intent. Failed deployments and validator failures
are retained rather than erased.

## Repository anchor

- Repository: `GIFTEDLOV/tendercouncil`
- Branch: `main`
- Initial audit HEAD: `d5c4f50bfa08495c57511e602e47a6fc28337606`
- Current continuation HEAD: recorded by the release manifest after the live E2E completes.

## Existing evidence

The four JSON files under `artifacts/` preserve deployment addresses,
transaction IDs, validator votes, GenVM trace versions, and failure causes from
Stage 0/1. Production evidence is append-only. The test runner now writes to
`.local/gltest-artifacts/`; the installed test plugin recursively clears that
ephemeral directory at startup and must never target `artifacts/`.

## Reconstructed 2026-08-13 diagnostic

`artifacts/tender_council_bradbury_e2e_failure_2026-08-13T150054150Z.json`
is classified as `RECONSTRUCTED_AFTER_LOCAL_TEST_ARTIFACT_CLEAR`.

- Reconstructed SHA-256: `4b42ecd5e0ceb5da9f24cb31634b6ce36678bbd4267a47e01f2fc773a0a381e7`
- Known historical original SHA-256: `d2ebc3efe53fe9b369b11154c1b65e3f6403f5c707ed53f8f49363f2f2b3bfdf`
- Exact parity: not proven. The installed `genlayer-test` pytest plugin
  recursively cleared the configured `artifacts/` directory. Tracked evidence
  was restored byte-for-byte from Git, but this untracked diagnostic had no Git
  blob to restore. It was reconstructed from previously captured output.
- Authority: historical and non-authoritative. It must not be used as the sole
  proof of any chain fact or represented as the lost original.
- Independent facts: the old Core/Evaluator addresses, tender states, escrow
  totals, bid parent IDs, evaluation transaction, failed Evaluator child,
  validator votes, trace outputs, and callback absence were independently read
  again from Bradbury during the 2026-08-14 forensic audit. Fresh canonical
  machine-readable evidence is required before any future release.

## Current changes

The 2026-08-14 v2 remediation is local-only. It adds list-shaped nondeterministic
calldata, bounded model envelopes, nonce/deadline recovery from failed evaluator
children, deterministic uphold of an already valid winner after bounded review
failure, tender-scoped runner reconciliation, and a durable append-only
operation journal. The generated v2 Core/Evaluator artifacts pass the local
42 KB size boundary, but no v2 contract, binding, tender, bid, or other live
transaction exists. The local exact-artifact five-validator proof exercises
comparative evaluation, Core callback consumption, `NO_VALID_BID`, malformed
evaluation and review handling, retries, review, and stale/duplicate callback
rejection. The exact Bradbury
`eth_estimateGas` probes pass without signing or broadcasting. `NEW LIVE E2E
ALLOWED` remains false pending review, CI, and an immutable clean-worktree HEAD.

This continuation adds runtime due diligence, a threat model, the exact-byte
SHA-256 and evaluator-boundary hardening, public funded production tenders,
comparative evaluation, bounded challenges, finalized-safe settlement states,
mutation checks, and release tooling. The finalized two-contract pair is
preserved in `artifacts/tender_council_bradbury_deployment.json` as
`FINALIZED_DEPLOYMENT_PROOF_SUPERSEDED_BEFORE_E2E`. A post-deployment semantic
and challenge audit found defects before any tender was funded; no participant
funds were exposed and no settlement occurred. The pair is immutable historical
evidence and must not be rebound or used for the replacement E2E. Earlier
production Bradbury deployment attempts remain in
`artifacts/bradbury-production-deployment-*.json`; no frontend has been
started. This continuation adds exact GEN-wei escrow/payout/refund accounting,
serialized Core outflows for multi-tender balance verification, execution-level
all-semantic-fail `NO_VALID_BID`, exact integrity-set enforcement, and
deterministic invalid-challenge `UPHOLD` handling. The first replacement pair
is finalized and permanently bound in its separate historical deployment
manifest, but its funded E2E exposed a snapshot-shape contract defect before
web/LLM evaluation. That pair and the failed tender are preserved in append-only
failure artifacts; no payout, refund, or settlement occurred. The corrected pair
is finalized and permanently bound in
`artifacts/tender_council_bradbury_corrected_deployment.json`. Its funded
canonical tender and five finalized immutable bids are the active E2E proof;
new close, evaluation, challenge, review, payout, refund, and settlement
evidence is appended only after each corresponding transaction reaches the
required finalized/readback state.
