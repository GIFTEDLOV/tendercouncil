# TenderCouncil

> **CURRENT PRODUCTION RELEASE — Bradbury v2.1 — FINALIZED**
> Bound Core/Evaluator pair, `production_ready=true`.

| Production contract | Address |
| --- | --- |
| Core (`TenderCouncilCore`) | [0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd](https://explorer-bradbury.genlayer.com/address/0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd) |
| Evaluator (`TenderCouncilEvaluator`) | [0x023AB3434761715a531884Ca0852aC14beE03acE](https://explorer-bradbury.genlayer.com/address/0x023AB3434761715a531884Ca0852aC14beE03acE) |

The release is on GenLayer Bradbury, chain `4221`. Core is permanently bound
to the v2.1 Evaluator (`tendercouncil.evaluator.v2.1`) using the exact deployed
Evaluator artifact hash. The finalized binding transaction is
`0x186e412e4132763dc5b437a23944b30a5bffa5cd751c872b6e25ad5631c4acbf`.

TenderCouncil is an Intelligent Contract system for authenticated,
evidence-backed procurement awards. Core owns policy, escrow, lifecycle,
challenge admission, and settlement. Evaluator authenticates committed content,
performs integrity/schema checks, and supplies the bounded comparative judgment.

## Architecture in 30 seconds

Core owns money and lifecycle. The permanently bound Evaluator owns no funds and
returns only a bounded comparative judgment over Core's frozen canonical bid
snapshot; Core independently validates the result before settlement.

```text
Buyer / Bidders
      |
      v
+-------------+
|    CORE     |  money + state
+------+------+
       | frozen canonical snapshot
       v
+-------------+
|  EVALUATOR  |  semantic comparison
+------+------+
       | bounded result + digest
       v
+-------------+
|    CORE     |  validates + settles
+-------------+
```

The four phases are **CREATE** (fund, open, bid), **FREEZE** (close the
canonical snapshot), **DECIDE** (evaluate, provisional award, response/review),
and **SETTLE** (final award, winner payment, buyer remainder).

## Verified live procurement

The single authorized post-submission Bradbury pilot attempt is preserved in
[`docs/pilot/FINALIZED-BRADBURY-PROCUREMENT.md`](docs/pilot/FINALIZED-BRADBURY-PROCUREMENT.md)
and its append-only reconciliation journal is
[`artifacts/tender_council_bradbury_v21_finalized_pilot_journal.json`](artifacts/tender_council_bradbury_v21_finalized_pilot_journal.json).
Creation and opening finalized, but Bradbury finality consumed the pilot's
one-hour deadline before the first bid could be accepted. It is therefore
explicitly **not** claimed as a completed `SETTLED` proof.

For a five-to-ten-minute explanation of the system, see the
[reviewer guide](docs/REVIEWER-GUIDE.md).

## Production status

| Item | Value |
| --- | --- |
| Network | `testnet-bradbury` |
| Chain | `4221` |
| Release | `v2.1` / **FINALIZED** |
| Relationship | Core permanently bound to the production Evaluator |
| `get_production_ready()` | `true` |
| Evaluator schema | `tendercouncil.evaluator.v2.1` |
| Evaluator deployable artifact hash | `sha256:e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b` |
| Binding result | `FINALIZED` / `AGREE` / `FINISHED_WITH_RETURN` / zero deterministic violations |

The authoritative deployment record and readback are in
[`artifacts/tender_council_bradbury_v21_deployment.json`](artifacts/tender_council_bradbury_v21_deployment.json).
Historical or superseded deployments remain in `artifacts/` as provenance only;
they are not current integration targets.

## Integration at a glance

Use the **Core address** for normal application integration. Read the Evaluator
directly only when an operator needs the persisted evaluation/review JSON or
the immutable Core/version constructor readbacks. Core is the financial and
lifecycle authority and revalidates every Evaluator result before recording a
provisional or final award.

The complete integration sequence, ABI-shaped calls, finality rules, recovery
policy, and settlement flow are in [docs/INTEGRATION.md](docs/INTEGRATION.md).
Small no-broadcast reference examples are in
[`examples/buyer_flow.mjs`](examples/buyer_flow.mjs) and
[`examples/bidder_flow.mjs`](examples/bidder_flow.mjs).

## Public API

The signatures below are the public methods in the current v2.1 source. The
GenLayer SDK call shape is `readContract({ address, functionName, args })` for
views and `writeContract({ account, address, functionName, args, value,
leaderOnly: false })` for writes. The evaluator callback methods are public for
cross-contract delivery but are not application entry points.

### Public API classification

**APPLICATION ENTRY POINTS** — `create_tender`, `open_tender`, `submit_bid`,
`close_tender`, `start_evaluation`, `start_response_window`,
`submit_challenge`, `advance_after_response`, `settle_award`,
`confirm_settlement`, and `confirm_refund` are the normal buyer, bidder, or
integrator calls.

**PROTOCOL CALLBACKS** — `receive_evaluation_result`,
`receive_evaluation_failure`, `receive_review_result`,
`receive_review_failure`, `start_evaluation_job`, and `start_review_job` are
cross-contract delivery methods, not ordinary application entry points.

**RECOVERY / TIMEOUT** — `expire_evaluation_attempt`, `retry_evaluation`,
`expire_review_attempt`, `retry_review`, `cancel_tender`,
`refund_no_valid_bid`, `confirm_no_valid_refund`, and
`refund_failed_evaluation` are bounded recovery or terminal refund calls.

**READ-ONLY INTEGRATION** — readiness, binding, balance, tender, bid, snapshot,
evaluation, review, settlement-accounting, and constructor readbacks are views.

The complete API tables below retain every public method and its exact
preconditions.

### READ-ONLY INTEGRATION — Core views

| Method | Type | Purpose, preconditions, and result/state behavior |
| --- | --- | --- |
| `get_production_ready()` | Core / view | Returns `bool`; `true` only after the one-time Evaluator binding is stored. |
| `get_evaluator_binding()` | Core / view | Returns canonical JSON with `bound`, `address`, `version`, and `evaluator_code_hash`; no state change. |
| `get_contract_balance()` | Core / view | Returns Core's current `u256` balance in GEN wei. |
| `get_settlement_accounting(tender_id)` | Core / view | Requires an existing tender; returns canonical JSON for escrow, payout/refund amounts, confirmation flags, settlement state, and the serialized financial outflow. |
| `get_tender(tender_id)` | Core / view | Requires an existing tender; returns the full `CoreTender` state record. |
| `get_bid(bid_id)` | Core / view | Requires an existing bid; returns the full immutable `CoreBid` record. |
| `get_challenge(challenge_id)` | Core / view | Requires an existing challenge; returns the `CoreChallenge` record and admission status. |
| `list_tender_ids()` | Core / view | Returns the persistent `DynArray[str]` of created tender IDs. |
| `get_evaluation_context(tender_id)` | Core / view | Requires a tender; returns canonical JSON containing status, evaluation nonce, closed-snapshot digest, bound Evaluator, and timeout. |
| `get_closed_snapshot(tender_id)` | Core / view | Requires a post-close lifecycle state; returns the canonical v1 snapshot or rejects while the tender is still draft/open. |
| `get_review_context(tender_id, review_nonce)` | Core / view | Requires the current `REVIEWING_CHALLENGES` state and nonce; returns correlated immutable review inputs and admitted challenges. |

### Core writes

| Method | Type | Important preconditions and state behavior |
| --- | --- | --- |
| `bind_evaluator(evaluator_address, evaluator_version, evaluator_code_hash)` | Core / write | Bootstrapper only, once, non-zero address, exact `tendercouncil.evaluator.v2.1`, and a valid `sha256:` hash; permanently sets readiness. Already finalized in production; do not call again. |
| `create_tender(tender_id, title, brief_url, brief_sha256, max_budget_wei, max_delivery_days, min_support_days, bidding_deadline, response_window_seconds, requirements, technical_weight, delivery_weight, price_weight, capability_weight, support_weight, evidence_policy)` | Core / payable write | Buyer creates a unique funded draft. URLs must be HTTPS, hashes valid, deadline future, response window at least 600 seconds, rubric totals 100, and `msg.value == max_budget_wei`. Stores exact escrow and immutable policy. |
| `open_tender(tender_id)` | Core / write | Bound Evaluator required; buyer only; draft status, funded Core balance, and future deadline required. Changes `DRAFT -> OPEN`. |
| `submit_bid(bid_id, tender_id, price_wei, delivery_days, support_days, proposal_url, proposal_sha256, evidence_commitments, schema_version="tendercouncil.bid.v1")` | Core / write | Bound Evaluator required; unique bid ID, open tender before deadline, positive price, HTTPS proposal URL, valid hash/commitment string, supported schema, and one bid per wallet per tender. Stores immutable bid data and sender as bidder. |
| `close_tender(tender_id)` | Core / write | Buyer only; open tender and deadline elapsed. Canonicalizes all bids ordered by ID, stores its SHA-256, and changes to `CLOSED`. |
| `start_evaluation(tender_id)` | Core / write | Bound Evaluator and buyer required; only `CLOSED`; increments the bounded evaluation nonce, sets a 6-hour timeout, changes to `EVALUATING`, and emits a finalized-only Evaluator job. |
| `expire_evaluation_attempt(tender_id)` | Core / write | Permissionless timeout transition; only `EVALUATING` after its timeout. Moves to `EVALUATION_RETRYABLE`, or after three attempts to `EVALUATION_FAILED`. |
| `retry_evaluation(tender_id)` | Core / write | Bound Evaluator required; only retryable and unchanged snapshot digest; starts the next bounded evaluation attempt. |
| `receive_evaluation_result(tender_id, nonce, snapshot_digest, evaluator_schema_version, result_type, winner_bid_id, result_digest)` | Core / callback write | Bound Evaluator only; current nonce/status, snapshot/schema/result type, persisted result digest, partition, scores, unique winner, and arithmetic must all match. Changes to `PROVISIONAL_AWARD` for `COMPARATIVE`, or `NO_VALID_BID` for that result type. |
| `receive_evaluation_failure(tender_id, nonce, snapshot_digest, failure_code, failure_digest)` | Core / callback write | Bound Evaluator only; correlated current attempt and `MODEL_CANDIDATE_INVALID` or `MODEL_PROVIDER_UNAVAILABLE` payload required. Applies the same bounded retry/failure transition as timeout. |
| `start_response_window(tender_id)` | Core / write | Requires `PROVISIONAL_AWARD`; records start/end using the stored response-window duration and changes to `RESPONSE_WINDOW`. |
| `submit_challenge(challenge_id, tender_id, reason_code, target_bid_id, referenced_evidence_id, challenge_url, challenge_sha256)` | Core / write | Current response window, unique ID, allowed reason, valid tender bid target, and sender must be a bidder. At most one challenge per bidder and 16 per tender; evidence references must be pre-close commitments. Stores `ADMITTED` deterministically. |
| `advance_after_response(tender_id)` | Core / write | Permissionless after the response window ends. With no admitted challenges, sets the provisional winner as final and changes to `AWARDED`; otherwise digests the challenge set and starts bounded review. |
| `receive_review_result(tender_id, evaluation_nonce, review_nonce, snapshot_digest, original_result_digest, challenge_set_digest, decision, winner_bid_id, result_digest)` | Core / callback write | Bound Evaluator only; all review correlations and digest checks must match. `UPHOLD` or `REPLACE_WINNER` selects an original valid bid and changes to `AWARDED`; `NO_VALID_BID` changes to the refundable terminal path. |
| `receive_review_failure(tender_id, evaluation_nonce, review_nonce, snapshot_digest, original_result_digest, challenge_set_digest, failure_code, failure_digest)` | Core / callback write | Bound Evaluator only; correlated failure payload and one of the two model failure codes required. Retries up to three times, then falls back to the provisional winner. |
| `expire_review_attempt(tender_id)` | Core / write | Permissionless after the current 6-hour review timeout; retryable before three attempts, otherwise awards the provisional winner. |
| `retry_review(tender_id)` | Core / write | Bound Evaluator required; only retryable and unchanged snapshot/challenge-set digests; starts the next review attempt. |
| `settle_award(tender_id)` | Core / write | Only an unsettled `AWARDED` tender; verifies winner and quote, computes exact payout plus buyer remainder, serializes the outflow, and emits finalized-only winner payment. Changes to `SETTLEMENT_PENDING`. |
| `confirm_settlement(tender_id)` | Core / write | After a pending payout, verifies the observed balance delta. Marks payout confirmed and either starts the unused-escrow refund or completes `SETTLED` when the remainder is zero. |
| `cancel_tender(tender_id)` | Core / write | Buyer only; draft/unopened tender and no other financial outflow. Starts a full finalized-only buyer refund and changes to `REFUND_PENDING`. |
| `confirm_refund(tender_id)` | Core / write | After a pending cancellation, no-valid, failed-evaluation, or remainder refund; verifies the balance delta, clears the lock, and marks the appropriate terminal state. |
| `refund_no_valid_bid(tender_id)` | Core / write | Buyer only; `NO_VALID_BID` with unsettled escrow. Starts the exact full refund. |
| `confirm_no_valid_refund(tender_id)` | Core / write | Alias that invokes the same refund confirmation logic as `confirm_refund`. |
| `refund_failed_evaluation(tender_id)` | Core / write | After three bounded evaluation attempts reach `EVALUATION_FAILED`; starts the exact full buyer refund. |

### Evaluator views and writes

| Method | Type | Important preconditions and result/state behavior |
| --- | --- | --- |
| `get_evaluation_result(tender_id, nonce)` | Evaluator / view | Requires a persisted result for that key; returns canonical evaluation JSON or a model-failure envelope. |
| `get_core_address()` | Evaluator / view | Returns the immutable Core constructor address. |
| `get_evaluator_version()` | Evaluator / view | Returns the immutable `tendercouncil.evaluator.v2.1` constructor version. |
| `get_review_result(tender_id, nonce)` | Evaluator / view | Requires a persisted review result for that key; returns canonical review JSON or a model-failure envelope. |
| `start_evaluation_job(tender_id, nonce, snapshot_digest)` | Evaluator / finalized callback write | Core only; requires a correlated `EVALUATING` context and no duplicate result. Reads the immutable snapshot, validates it, performs evaluation, persists the result, and emits one finalized-only Core callback. |
| `start_review_job(tender_id, evaluation_nonce, review_nonce, snapshot_digest, original_result_digest, challenge_set_digest)` | Evaluator / finalized callback write | Core only; requires a correlated `REVIEWING_CHALLENGES` context and no duplicate review. Revalidates challenge bodies, performs bounded review or deterministic uphold, persists the result, and emits one finalized-only Core callback. |

## Verification

The committed CI workflow is the source of truth for verification. It runs
dependency diagnostics, GenVM lint and validation for the historical reference,
production foundation, and v2.1 Core/Evaluator sources; finalized-message
checks; semantic/equivalence/challenge/review/financial probes; generated
source/deployable parity and split size checks; the direct pytest suite; and
original, split, and reduced-model mutation checks. No new full campaign is
required for documentation changes.

The release evidence and tools also preserve the pinned direct GenVM header,
artifact hashes, finalized deployment/binding readback, exact-result
regressions, and five-validator local production-artifact proof. See
[docs/CI.md](docs/CI.md), [docs/RELEASE.md](docs/RELEASE.md), and
[MANIFEST.sha256](MANIFEST.sha256).

## Architecture and consensus

Core is the deterministic financial source of truth. At close it freezes a
canonical snapshot; deterministic budget, delivery, support, deadline, and
schema admissibility runs before the Evaluator's exact-byte integrity checks
and bounded semantic comparison. Validator agreement compares decision-critical
sets and identities exactly, with only the deployed two-point score tolerance.
See [docs/CONSENSUS-NOTES.md](docs/CONSENSUS-NOTES.md) and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
For ecosystem positioning and overlap analysis, see
[docs/OVERLAP-RESEARCH.md](docs/OVERLAP-RESEARCH.md).

## Provenance and historical records

- [docs/PROVENANCE.md](docs/PROVENANCE.md) explains the append-only evidence
  history and superseded deployments.
- [SUBMISSION.md](SUBMISSION.md) is the original submission record.
- The canonical v2.1 E2E is `E2E_STATUS = POST_SUBMISSION_OPTIONAL`; its parked
  state and journal are preserved in
  [`artifacts/tender_council_bradbury_v21_e2e_parked.json`](artifacts/tender_council_bradbury_v21_e2e_parked.json).
  It is not required for this release, and this repository polish does not
  resume or modify it.

Historical v1/v2 deployment records remain clearly labeled in `artifacts/` and
must not be used as current addresses or release evidence.

## Development

```text
python -m pip install -r requirements-dev.txt
genvm-lint check contracts/tender_council_core.py
genvm-lint validate contracts/tender_council_core.py
genvm-lint check contracts/tender_council_evaluator.py
genvm-lint validate contracts/tender_council_evaluator.py
python tools/check_manifest.py
python -m pytest
```

The deployable artifacts are generated by `tools/make_deployable.py`. Do not
regenerate or deploy them as part of a documentation-only change.
