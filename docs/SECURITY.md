# TenderCouncil security status

This document records the current security posture and is deliberately honest
about the Stage 1 prototype's missing production controls.

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
  fields; malformed validator data returns `False`.
- Direct regression probes exercise the nondeterministic boundary and changed
  content rejection.

## Not yet safe for production

- Tender creation is still owner-gated instead of public to any buyer.
- Commercial fields, manifest schema, evidence policy, and hard admissibility
  constraints are not yet complete.
- The current evaluator scores one bid at a time rather than comparing all
  admissible bids under one locked rubric.
- `award_bid` is still a Stage 1 manual award method and must be removed or
  made unreachable in the production contract.
- There is no funded escrow, response window, bounded challenge review, or
  finalized-safe settlement path yet.
- CI, release preflight, and repeatable deployment scripts are not complete.

The UI stop gate is therefore closed.
