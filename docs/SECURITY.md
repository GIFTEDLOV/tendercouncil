# TenderCouncil security status

This document records the current security posture and distinguishes the
preserved Stage 1 prototype from the production foundation.

## Implemented now

- Caller addresses authenticate issuers, suppliers, and evidence submitters.
- Tender, bid, and evidence IDs are unique in persistent state.
- HTTPS is required for evidence locators.
- Evidence commitments require `sha256:` followed by exactly 64 lowercase hex
  characters.
- The evaluator hashes fetched response bytes before decoding or prompting.
- Hash mismatch, oversized content, and non-UTF-8 content fail closed.
- Source data is explicitly untrusted in the evaluator prompt.
- Validator callbacks independently rerun the task and compare bounded stable
  fields: exact classifications and winner identity, bounded subjective score
  drift, and no tolerance for a changed winner. Rationale is informational.
- Direct regression probes exercise the nondeterministic boundary and changed
  content rejection.
- Production tenders are public-buyer, sender-authenticated, exactly funded in
  integer GEN wei. `max_budget_wei` is escrowed, bids commit `price_wei`, and
  payout is the immutable winning quote rather than a fixed prize.
- Production evaluation ranks all deterministically admissible bids under one
  locked rubric; the buyer has no arbitrary winner-substitution method.
- Provisional awards require a separate non-zero response window. Challenges
  are admitted deterministically by Core without buyer validity approval,
  sender-authenticated, and restricted to pre-close evidence commitments;
  one validator-agreed review round is allowed.
- `settle_award` pays the immutable winning `price_wei` through an external
  `on="finalized"` transfer, then refunds the unused escrow remainder. Explicit
  payout/refund accounting must sum to deposited escrow. A global serialized
  financial-outflow lock prevents multi-tender balance-delta races; each
  confirmation still requires observable balance verification before state is
  marked complete.
- Core's one-time evaluator binding calls the commitment `evaluator_code_hash`.
  It is the SHA-256 digest of the exact generated Evaluator artifact bytes sent
  in deployment, not the readable canonical source digest.  Source and artifact
  digests are recorded separately in release provenance.

## Evaluator normalization

The five previously reported review-normalization warnings are resolved. Review
malformed-output paths now use bounded `gl.vm.UserError` failures, while the
validator callback still fails closed. Direct and executable mutation probes
cover malformed review output and correlation failures.

## Release posture

- The preserved Stage 1 prototype remains owner-gated and retains its manual
  award method; it is not the current production deployment artifact.
- The v2.1 Core/Evaluator pair is the finalized and permanently bound production
  release. Its exact addresses, hashes, binding transaction, and readback are
  in `docs/RELEASE.md` and the v2.1 deployment manifest.
- The canonical five-bid E2E is `POST_SUBMISSION_OPTIONAL` and parked. It is not
  a release blocker or a claim that the production binding is unsafe.
- Historical pairs, funded historical tenders, and failed E2E children remain
  immutable provenance and must not receive new transactions.

No frontend is required for the contract release. Integrators should use Core's
public API and follow the finalized/reconcile-before-retry rules in
`docs/INTEGRATION.md`.
