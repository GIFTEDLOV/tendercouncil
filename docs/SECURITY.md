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
- Core's one-time evaluator binding calls the commitment `evaluator_code_hash`.
  It is the SHA-256 digest of the exact generated Evaluator artifact bytes sent
  in deployment, not the readable canonical source digest.  Source and artifact
  digests are recorded separately in release provenance.

## Intentionally retained evaluator warnings

The Evaluator linter reports five non-fatal `ValueError` normalization warnings
in the two bounded structured-output normalizers.  These exceptions are inside
the nondeterministic leader callbacks only: malformed or impossible LLM output
is rejected, the validator callback catches the failed normalization, and the
consensus operation fails closed.  The production foundation's malformed-output
direct tests cover this behavior; the split runtime mutation probe also drives
the callback path.  These warnings are retained because replacing them with
generic user-facing exceptions inside nondeterministic callbacks would risk
changing validator semantics.

## Not yet safe for production

- The preserved Stage 1 prototype remains owner-gated and retains its manual
  award method; it is not the production deployment artifact.
- Production finalized-child transaction evidence has not yet been recorded
  on Bradbury, and direct mode reports an unsupported `EthSend` trace rather
  than simulating the external child transfer.
- The release preflight and deployment wrapper are present, but no production
  Bradbury deployment has yet been accepted as release evidence.
- Bradbury currently rejects both the full and generated compact production
  artifacts before contract creation at the network pubdata limit; this is an
  unresolved release blocker and no E2E settlement claim is made.

The UI stop gate is therefore closed.
