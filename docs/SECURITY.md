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
  fields; malformed validator data returns `False`.
- Direct regression probes exercise the nondeterministic boundary and changed
  content rejection.
- Production tenders are public-buyer, sender-authenticated, exactly funded,
  and isolated by tender escrow accounting.
- Production evaluation ranks all deterministically admissible bids under one
  locked rubric; the buyer has no arbitrary winner-substitution method.
- Provisional awards require a separate non-zero response window. Challenges
  are bounded, sender-authenticated, and restricted to pre-close evidence
  commitments; one validator-agreed review round is allowed.
- `settle_award` uses an external `on="finalized"` transfer and records
  `TRANSFER_PENDING`; `confirm_settlement` requires the expected balance delta
  before recording `SETTLED`.

## Not yet safe for production

- The preserved Stage 1 prototype remains owner-gated and retains its manual
  award method; it is not the production deployment artifact.
- Production finalized-child transaction evidence has not yet been recorded
  on Bradbury, and direct mode reports an unsupported `EthSend` trace rather
  than simulating the external child transfer.
- CI, release preflight, and repeatable deployment scripts are not complete.

The UI stop gate is therefore closed.
