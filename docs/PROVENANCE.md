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
Stage 0/1. Their worktree hashes are checked against `HEAD` after direct tests
because the installed test plugin clears `artifacts/` on startup.

## Current changes

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
deterministic invalid-challenge `UPHOLD` handling. The replacement pair is
finalized and permanently bound in the separate replacement deployment
manifest. The funded canonical tender and five immutable bids are now in the
controlled Bradbury E2E; its runner waits for the onchain deadline and remains
idempotent after transient RPC/tooling failures. Close, evaluation, challenge,
review, payout, refund, and settlement evidence will be appended only after
finalized readback.
