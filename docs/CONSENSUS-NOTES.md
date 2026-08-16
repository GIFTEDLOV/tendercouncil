# TenderCouncil v2.1 consensus notes

These notes describe the deployed v2.1 Core and Evaluator sources and their
generated artifacts. They are not a proposal for a new contract version.

## Trust and decision pipeline

TenderCouncil separates procurement facts from semantic judgment:

```text
wallet authentication
  -> on-chain integrity commitments
  -> exact-byte integrity checks
  -> bounded schema checks
  -> deterministic admissibility
  -> semantic evaluation
  -> Core result validation and settlement state
```

Authentication is the transaction sender. Core stores the buyer, bidder, and
challenger addresses from `gl.message.sender_address`; the Evaluator checks that
the caller of its job methods is the immutable Core address. A URL is only a
locator. Proposal, evidence, and challenge bytes are accepted as authoritative
only when their exact fetched bytes match the committed lowercase SHA-256.

The implementation performs Core's cheap bid admissibility checks before the
Evaluator fetches content. For each fetched object, exact-byte hashing still
precedes decoding and schema validation. The resulting security boundary is
the same: uncommitted, malformed, or ineligible material cannot enter the
semantic candidate set.

## What Core decides deterministically

Core is the source of truth for all commercial and lifecycle facts. It
deterministically:

- authenticates buyer, bidder, and challenger senders;
- requires exact escrow equal to `max_budget_wei`;
- validates HTTPS locators, `sha256:` format, unique IDs, bid schema, and
  commitment-string grammar at write time;
- freezes the `tendercouncil.snapshot.v1` close snapshot using sorted compact
  JSON and SHA-256;
- excludes bids whose price exceeds budget, delivery exceeds the limit,
  support is below the minimum, submission is after the deadline, or schema is
  not `tendercouncil.bid.v1`;
- rechecks the Evaluator's deterministic/integrity/semantic partition;
- requires complete semantic classification coverage and a valid-bid winner;
- recomputes each weighted score total and orders candidates by descending total
  with `bid_id` as the deterministic secondary key;
- rejects an unresolved top-score tie;
- allows only the original valid bid set during review;
- controls `DRAFT` through settlement/refund states, exact payout/refund
  accounting, finalized-only transfers, and balance-delta confirmation.

The Core never calls a web source, invokes a model, or chooses a winner by
manual administrator substitution. `COMPARATIVE` creates only a provisional
award until the response window and any bounded review have completed.

## What Evaluator decides semantically

The bound Evaluator reads the immutable closed snapshot through its Core
interface. It retrieves each admissible bid's committed
`tendercouncil.bid.v1` manifest and its evidence. The current v2.1 schemas are:

```text
tendercouncil.core.v2.1
tendercouncil.evaluator.v2.1
tendercouncil.snapshot.v1
tendercouncil.bid.v1
tendercouncil.evidence.v1
tendercouncil.challenge.v1
```

After deterministic and integrity/schema filtering, the model boundary is
small. The model supplies one row per semantic candidate containing only:

```json
{
  "bid_id": "...",
  "mandatory_requirements_pass": true,
  "technical": 0,
  "delivery": 0,
  "price": 0,
  "capability": 0,
  "support": 0
}
```

and a confidence value. The contract—not the model—derives valid and
disqualified sets, totals, winner, runner-up, status, and the rationale-bearing
result envelope. Proposal, evidence, and challenge text is explicitly
untrusted data; it cannot rewrite the trusted rubric or introduce instructions.

## Independent validators and comparison

Each Evaluator job uses `gl.vm.run_nondet_unsafe` with a leader function and a
validator function that independently reruns the same bounded derivation.
Validator agreement is not a trust assumption about web content. It is a
check that the same authenticated snapshot, committed bytes, schema outcomes,
candidate IDs, classifications, and decision-critical result were derived.

The v2.1 `_comparative_equivalent` comparison is exact for:

- `status`;
- winner and runner-up identity;
- deterministic, integrity, semantic-candidate, semantic-disqualified,
  valid, and disqualified bid ID sets; and
- every `semantic_classifications` row, including its boolean mandatory-
  requirements decision.

For a comparative result, winner identity and runner-up identity must still
match exactly. Every criterion score and computed total may differ by at most
the deployed `SCORE_TOLERANCE = 2`; the winner and runner-up totals also have a
two-point bound. Both sides must satisfy score arithmetic and invariant checks,
and Core independently recomputes the ordering and rejects a tie.

This is why winner identity cannot drift: the winner ID is an exact comparison
field, the result must cover the same bid partition, the winner must be in the
original valid set, Core checks the callback winner against the persisted
Evaluator payload, and Core derives/validates the unique highest total. A
validator cannot replace a winner merely because its subjective score moved
within tolerance.

## Failure states

The following are distinct from a successful `COMPARATIVE` or `NO_VALID_BID`
business result:

`MODEL_CANDIDATE_INVALID` means the model returned a response that could not be
normalized to the exact v2.1 shape/ranges/coverage, or normalization could not
produce a valid derived result. The Evaluator persists
`{"state":"MODEL_CANDIDATE_INVALID","result":{}}` and Core accepts it only as
a correlated failure callback.

`MODEL_PROVIDER_UNAVAILABLE` means `gl.nondet.exec_prompt` raised or the model
provider was unavailable. The same empty-result failure envelope is persisted
and correlated by digest; no winner is invented.

`DISAGREE` is a consensus outcome, not an Evaluator business result. It means
the protocol did not obtain the required validator agreement for the operation.
There is no valid callback payload for Core to consume from that operation.

`DETERMINISTIC_VIOLATION` indicates a deterministic execution boundary did not
produce the same result across validators. It is also a protocol/runtime
failure, not a bid classification and not a license to apply a local winner.
The finalized v2.1 binding evidence records zero deterministic violations.

`NO_VALID_BID` is different: it is a valid, consensus-agreed Evaluator result
whose deterministic, integrity, and semantic filters leave no winner. Core
records it as a terminal award-path state with a full refund path.

## Retry and failure policy

Evaluation and review use immutable correlation inputs and bounded nonces.
Core retries a correlated `MODEL_*` failure or an expired callback while the
attempt count is below three. Evaluation exhaustion reaches
`EVALUATION_FAILED` and exposes `refund_failed_evaluation`; review exhaustion
falls back to the stored provisional winner. A stale callback, changed
snapshot, changed challenge-set digest, wrong caller, duplicate job, or digest
mismatch is rejected and cannot mutate state.

For `DISAGREE`, `DETERMINISTIC_VIOLATION`, or an RPC timeout, the client must
reconcile the transaction and Core state first. It must not locally assume a
failure and must never blindly rebroadcast. Only an observed retryable Core
state, or an elapsed on-chain timeout followed by the appropriate permissionless
expiry method, authorizes a retry. Application settlement remains blocked until
the corresponding operation is `FINALIZED` and read back.
