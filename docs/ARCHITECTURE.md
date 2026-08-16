# TenderCouncil architecture

TenderCouncil production is a two-contract system:

```text
buyer/bidders -> TenderCouncilCore <- finalized compact callbacks <- TenderCouncilEvaluator
                      |
                 escrow + lifecycle + settlement
```

`contracts/tender_council_production.py` remains a readable behavioral and
historical reference only. It is superseded and must never be selected by a
production deployment script.

## Core authority

`TenderCouncilCore` is the only financial and lifecycle authority. It owns
public buyer creation, exact award escrow, tender policy, deadlines, immutable
commercial bids, proposal/evidence commitments, closed snapshots, evaluation
nonces, provisional/final winners, the response window, challenge records,
refunds, and finalized-only settlement. It contains no web access, LLM call,
or semantic judgment.

Core starts unconfigured. The deployment bootstrapper may bind exactly one
evaluator address, version, and `sha256:` deployable-code commitment. Rebinding is
impossible. Opening a tender and all evaluator-dependent operations are blocked
until binding is complete. The bootstrapper is not a procurement administrator.

## Evaluator authority

`TenderCouncilEvaluator` is deployed with an immutable Core address and schema
version. It has no payable methods, escrow, custody, settlement, or winner
substitution capability. It reads Core snapshots through a typed
`@gl.contract_interface`, performs deterministic admissibility and exact-byte
evidence checks, comparatively evaluates remaining bids under the locked
rubric, persists bounded results, and emits only compact `on="finalized"`
callbacks.

The evaluator authenticates `gl.message.sender_address == core_address`; it
does not trust `origin_address`. Core applies the inverse check against its
bound evaluator address.

## Closed snapshot

At close, Core creates a canonical JSON snapshot using:

```text
schema_version=tendercouncil.snapshot.v1
json.dumps(value, sort_keys=True, separators=(",", ":"))
UTF-8 SHA-256 with the pinned GenVM hashlib implementation
```

The snapshot binds tender ID, buyer, title and brief commitments, the
maximum budget in GEN wei and all other commercial constraints, deadline, response window, requirements, rubric,
evidence policy, and every bid ordered by `bid_id`. Each bid includes bidder,
`price_wei`, delivery, support, proposal URL/hash, schema version, submission time,
and the complete pre-committed evidence commitment string. Core stores the
resulting `closed_snapshot_digest`; bids and policy have no post-close write
path.

## Evaluation and callback correlation

```text
CLOSED
  -> Core.start_evaluation()
  -> finalized Core -> Evaluator.start_evaluation_job()
  -> Evaluator reads/verifies snapshot and evaluates
  -> finalized Evaluator -> Core.receive_evaluation_result()
  -> PROVISIONAL_AWARD -> RESPONSE_WINDOW
```

Every result binds tender ID, evaluation nonce, snapshot digest, evaluator
schema, result type, winner ID, and result digest. Core reads the persisted
bounded result from Evaluator and independently checks set partitioning, winner
membership, disqualification, rubric bounds, arithmetic, runner-up, and nonce
invariants. Duplicate, stale, wrong-state, wrong-snapshot, wrong-schema,
wrong-caller, malformed, or replayed callbacks fail closed.

`NO_VALID_BID` is terminal for that tender's award path and has an explicit
finalized refund path; it never creates a winner.

## Evidence and semantic boundary

The proposal and evidence manifests use `tendercouncil.bid.v1` and
`tendercouncil.evidence.v1`. URLs are locators only. The evaluator retrieves
the exact response bytes, compares SHA-256 before decoding, then applies
bounded schema validation. Required unavailable, missing, hash-mismatched, or
invalid evidence disqualifies according to policy. Optional unavailable
evidence is recorded and skipped; it is never treated as confirmation.

Only deterministic admissible candidates and valid evidence claims enter the
semantic prompt. Every proposal, claim, challenge, fake system block, and
instruction-like string is explicitly untrusted data. Validators independently
derive the same comparative result. Stable classifications, bid sets, winner,
runner-up identity, and arithmetic invariants are exact; subjective criterion
scores use the measured two-point tolerance and a winner change is always
rejected. Rationale and confidence are informational and are not consensus
critical.

## Response and challenge boundary

An accepted result is non-payable `PROVISIONAL_AWARD`. Core then starts a
minimum 600-second `RESPONSE_WINDOW`; the Bradbury demo uses 7200 seconds.
Only eligible bidders may submit one bounded challenge using one of the four
locked reason codes. Admission is deterministic and authenticated; there is no
buyer validity oracle. Evidence references must have been committed before
close. External challenge bodies are URL/hash bound and exact-byte verified by
Evaluator before review, with explicit `VALID`, `UNAVAILABLE`,
`HASH_MISMATCH`, or `SCHEMA_INVALID` states.

After the window, no valid challenges advance directly to `AWARDED`. Valid
challenges create exactly one finalized review request bound to the original
result digest, snapshot digest, challenge-set digest, evaluation nonce, and
review nonce. Review may uphold, replace with an original valid bid, or produce
`NO_VALID_BID`; it cannot add evidence or change commercial terms.

## Settlement and refunds

Only Core can settle. Commercial money is integer GEN wei: `max_budget_wei` is
escrowed exactly, each immutable bid stores `price_wei`, and the winner receives
exactly that quoted price. `AWARDED -> SETTLEMENT_PENDING` emits the winner
transfer with `on="finalized"`; Core then verifies the ghost-contract balance
delta before emitting the buyer's unused remainder refund. The accounting
invariant is `escrow_deposited = winner_payout_amount + buyer_refund_amount`.
Neither transfer is considered complete when merely requested.

Core serializes all external outflows with one global lock containing the
tender, kind, amount, and pre-transfer balance. This permits many simultaneous
open/evaluating tenders while preventing concurrent payout, refund, or
cancellation transfers from invalidating balance-delta verification.
DRAFT-cancellation and `NO_VALID_BID` refunds use the same finalized transfer,
lock, and replay guards.

## State machine

```text
DRAFT -> OPEN -> CLOSED -> EVALUATING -> PROVISIONAL_AWARD
       -> RESPONSE_WINDOW -> REVIEWING_CHALLENGES -> AWARDED
       -> SETTLEMENT_PENDING -> SETTLED
```

`RESPONSE_WINDOW` may skip review when no valid challenge exists. Terminal
alternatives are `NO_VALID_BID` and finalized `CANCELLED`.

## Deployment size

Generated artifacts are mechanically derived from canonical sources. The v2.1
size evidence is recorded in `artifacts/tender_council_v21_size-budget.json`:
Core is 40,262 artifact bytes plus a conservative 1,024-byte outer bound, and
Evaluator is 30,524 artifact bytes plus the same bound. The 40,000 outer-byte
value remains the preferred engineering target; the fail-closed local fallback
is 42,000 conservative outer bytes. The prior monolith is not a deployment
fallback.
