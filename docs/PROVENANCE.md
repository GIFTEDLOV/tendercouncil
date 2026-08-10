# TenderCouncil provenance

Provenance is append-only in intent. Failed deployments and validator failures
are retained rather than erased.

## Repository anchor

- Repository: `GIFTEDLOV/tendercouncil`
- Branch: `main`
- Baseline HEAD at session start: `d363bb5c14eae2b5b3b8ab1d4c97d67addc01cb6`

## Existing evidence

The four JSON files under `artifacts/` preserve deployment addresses,
transaction IDs, validator votes, GenVM trace versions, and failure causes from
Stage 0/1. Their worktree hashes are checked against `HEAD` after direct tests
because the installed test plugin clears `artifacts/` on startup.

## Current changes

This continuation adds runtime due diligence, a threat model, the exact-byte
SHA-256 and evaluator-boundary hardening, a SHA-256 diagnostic probe, and a
changed-content mutation test. The production commercial contract has not yet
been substituted, and no frontend has been started.
