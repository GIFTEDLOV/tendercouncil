# TenderCouncil provenance

Provenance is append-only in intent. Failed deployments and validator failures
are retained rather than erased.

## Repository anchor

- Repository: `GIFTEDLOV/tendercouncil`
- Branch: `main`
- Baseline HEAD at session start: `f1f52022e7ae59d503fc484e3eb4da20343b65e4`

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
started.
