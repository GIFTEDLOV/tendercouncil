# TenderCouncil integration guide

This guide targets the finalized Bradbury v2.1 release. Normal application
traffic goes to Core:

```text
Core      0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd
Evaluator 0x023AB3434761715a531884Ca0852aC14beE03acE
chain     4221 (testnet-bradbury)
```

The [Bradbury Core explorer page](https://explorer-bradbury.genlayer.com/address/0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd)
is the normal starting point. The Evaluator is a bound service, not a second
financial entry point. Read it directly only to inspect its persisted
evaluation/review JSON or its immutable `get_core_address()` and
`get_evaluator_version()` values.

## Verify the production pair

Read all three values before relying on the release:

```js
const ready = await client.readContract({
  address: CORE,
  functionName: "get_production_ready",
  args: [],
});
const binding = JSON.parse(await client.readContract({
  address: CORE,
  functionName: "get_evaluator_binding",
  args: [],
}));
const evaluatorCore = await client.readContract({
  address: EVALUATOR,
  functionName: "get_core_address",
  args: [],
});
const evaluatorVersion = await client.readContract({
  address: EVALUATOR,
  functionName: "get_evaluator_version",
  args: [],
});

if (ready !== true
    || binding.bound !== true
    || binding.address.toLowerCase() !== EVALUATOR.toLowerCase()
    || binding.version !== "tendercouncil.evaluator.v2.1"
    || evaluatorCore.toLowerCase() !== CORE.toLowerCase()
    || evaluatorVersion !== "tendercouncil.evaluator.v2.1") {
  throw new Error("unexpected TenderCouncil production binding");
}
```

The bound artifact hash must also match the release record:

```text
sha256:e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b
```

`get_production_ready()` is a Core readiness flag. It does not claim that a
particular tender has bids, has been evaluated, or has been settled.

## Buyer flow

The buyer controls tender policy and pays exact escrow in GEN wei. The Core
write call has the following actual v2.1 argument order:

```js
const budget = 80_000_000_000_000_000n;
const createArgs = [
  "analytics-dashboard-2026",
  "Analytics dashboard procurement",
  "https://buyer.example/tenders/analytics-dashboard-2026/brief.json",
  "sha256:<sha256-of-the-exact-brief-response>",
  budget,
  90n,                 // max_delivery_days
  365n,                // min_support_days
  1_800_000_000n,     // bidding_deadline: Unix seconds, future on chain
  7_200n,              // response_window_seconds; minimum is 600
  "The dashboard must support the published requirements.",
  35, 20, 20, 15, 10, // technical, delivery, price, capability, support = 100
  "technical:required;delivery:required;capability:required;support:required",
];

// This is the SDK write shape. It broadcasts only if the caller invokes it.
const txHash = await client.writeContract({
  account: buyerAccount,
  address: CORE,
  functionName: "create_tender",
  args: createArgs,
  value: budget,
  leaderOnly: false,
});
```

The brief URL and hash are a commitment: the URL must serve the exact bytes
whose UTF-8 SHA-256 is supplied. The buyer must fund exactly `max_budget_wei`;
partial or excess value is rejected. After the create transaction is finalized,
the buyer calls `open_tender(tender_id)`. Core requires the permanent binding,
the buyer sender, a funded balance, and a deadline that has not elapsed.

```js
await client.writeContract({
  account: buyerAccount,
  address: CORE,
  functionName: "open_tender",
  args: ["analytics-dashboard-2026"],
  value: 0n,
  leaderOnly: false,
});
```

The buyer later calls `close_tender(tender_id)` only after the bidding deadline.
Core creates `tendercouncil.snapshot.v1`, sorts included bids by `bid_id`, and
stores the snapshot digest. The buyer then calls `start_evaluation(tender_id)`.
That call does not perform model work in the buyer process: Core increments the
evaluation nonce and emits a finalized-only message to the bound Evaluator.

## Bidder flow

Each bidder has one immutable bid per tender. The bidder submits commercial
fields and a commitment string to Core:

```js
const bidArgs = [
  "bid-amber-001",
  "analytics-dashboard-2026",
  62_000_000_000_000_000n, // price_wei
  75n,                      // delivery_days
  730n,                     // support_days
  "https://bidder.example/tenders/analytics-dashboard-2026/bid-amber-001.json",
  "sha256:<sha256-of-the-exact-proposal-manifest>",
  [
    // Core's actual transport is one semicolon-separated string. Each entry:
    // evidence_id|kind|criterion|required(0/1)|https-url|sha256-hash
    "amber-capability|CAPABILITY|capability|1|https://bidder.example/evidence/amber-capability.json|sha256:<hash>",
    "amber-delivery|DELIVERY|delivery|1|https://bidder.example/evidence/amber-delivery.json|sha256:<hash>",
  ].join(";"),
  "tendercouncil.bid.v1",
];

await client.writeContract({
  account: bidderAccount,
  address: CORE,
  functionName: "submit_bid",
  args: bidArgs,
  value: 0n,
  leaderOnly: false,
});
```

The proposal manifest served at `proposal_url` must be the exact
`tendercouncil.bid.v1` object that Evaluator expects. It repeats the bidder,
tender ID, price, delivery/support values, and the evidence list. Evidence
bodies must be `tendercouncil.evidence.v1` objects with exactly `schema_version`,
`kind`, and non-empty `claims`. A URL alone authenticates nothing; the
committed bytes and lowercase `sha256:` digest do.

Before and after submitting, use Core views:

```js
const tender = await client.readContract({
  address: CORE, functionName: "get_tender", args: [tenderId],
});
const bid = await client.readContract({
  address: CORE, functionName: "get_bid", args: [bidId],
});
```

## Admissibility and evaluation orchestration

At close, Core freezes the commercial snapshot. Both Core's callback validator
and Evaluator's snapshot path derive deterministic exclusions from the same
facts:

- `price_wei > max_budget_wei`;
- `delivery_days > max_delivery_days`;
- `support_days < min_support_days`;
- `submitted_at > bidding_deadline`; or
- a schema other than `tendercouncil.bid.v1`.

The Evaluator then fetches the committed proposal manifest and evidence, checks
exact bytes and schemas, and excludes integrity failures. Only remaining
semantic candidates enter the bounded comparative evaluation. Core independently
rechecks the returned partition, classification coverage, score bounds,
arithmetic, winner membership, and unique top score.

Read orchestration state with `get_tender(tender_id)`,
`get_evaluation_context(tender_id)`, and after close
`get_closed_snapshot(tender_id)`. `get_evaluation_result(tender_id, nonce)` on
Evaluator is useful for inspecting persisted JSON after the callback, but Core
is the source of truth for the lifecycle transition.

Evaluation attempts have a six-hour timeout and at most three attempts. If the
Evaluator returns `MODEL_CANDIDATE_INVALID` or
`MODEL_PROVIDER_UNAVAILABLE`, or no callback arrives by the timeout, Core moves
to `EVALUATION_RETRYABLE` while attempts remain. After the bound is exhausted,
Core reaches `EVALUATION_FAILED` and exposes a full escrow refund path.

## Provisional award, response, and challenge

A valid comparative result changes Core to `PROVISIONAL_AWARD`; it is not yet
payable. The buyer calls `start_response_window(tender_id)`, which records the
window and changes state to `RESPONSE_WINDOW`. The deployed protocol minimum is
600 seconds; the canonical Bradbury demo policy uses 7200 seconds.

Any bidder in that tender may submit one challenge during the window. The four
allowed reason codes are:

```text
MANDATORY_REQUIREMENT_MISAPPLIED
COMMITTED_EVIDENCE_OVERLOOKED
RUBRIC_MISAPPLIED
EVIDENCE_INTEGRITY_ERROR
```

The actual Core call is:

```js
await client.writeContract({
  account: bidderAccount,
  address: CORE,
  functionName: "submit_challenge",
  args: [
    "challenge-amber-001",
    tenderId,
    "COMMITTED_EVIDENCE_OVERLOOKED",
    "bid-other-001",
    "other-capability",
    "https://bidder.example/challenges/challenge-amber-001.json",
    "sha256:<sha256-of-the-exact-challenge-body>",
  ],
  value: 0n,
  leaderOnly: false,
});
```

The evidence reference must already be present in the target bid's committed
string. Challenge bodies, when supplied, use
`tendercouncil.challenge.v1` and are exact-byte checked by Evaluator. After the
window ends, anyone may call `advance_after_response(tender_id)`. With no
admitted challenges it sets the provisional winner as final and changes to
`AWARDED`. With an admitted challenge it creates a correlated bounded review.

Review is bound to the immutable snapshot digest, original result digest,
challenge-set digest, evaluation nonce, and review nonce. It can `UPHOLD`,
`REPLACE_WINNER` with an original valid bid, or produce `NO_VALID_BID`; it
cannot add a bid, change commercial terms, or introduce post-close evidence.
Use `get_review_context(tender_id, review_nonce)` on Core and
`get_review_result(tender_id, review_nonce)` on Evaluator for inspection.
Review has at most three six-hour attempts. Exhausted review falls back to the
provisional winner; a review failure before that is retryable.

## Settlement and refunds

Only `AWARDED` is eligible for payout. The buyer or an operator calls
`settle_award(tender_id)`. Core derives the winner's exact immutable `price_wei`,
sets `buyer_refund_amount = escrow_deposited - price_wei`, and emits the winner
transfer with `on="finalized"`. It then enters `SETTLEMENT_PENDING`.

After the payout transfer is finalized and the balance delta is observable,
call `confirm_settlement(tender_id)`. If a remainder exists, Core emits the
finalized-only buyer refund and remains pending until `confirm_refund(tender_id)`
verifies that second delta. If there is no remainder, the tender becomes
`SETTLED` immediately after payout confirmation. Inspect
`get_settlement_accounting(tender_id)` before and after each settlement write.

`NO_VALID_BID` uses `refund_no_valid_bid` followed by `confirm_refund` (or its
alias `confirm_no_valid_refund`). A bounded `EVALUATION_FAILED` uses
`refund_failed_evaluation` followed by `confirm_refund`. A draft can be
cancelled by its buyer with `cancel_tender` and then confirmed. All financial
outflows are globally serialized in Core, so an unrelated pending outflow is a
reason to reconcile and wait, not to submit a second payout/refund.

## Finality and safe retry policy

GenLayer transaction handling has two important observations:

- `ACCEPTED` means the transaction has an accepted consensus result. It is an
  intermediate observation for asynchronous lifecycle work.
- `FINALIZED` means the protocol finality/readback phase completed. Use it as
  the release boundary before treating a Core state transition, callback, or
  transfer as durable application state.

The SDK shape used by the repository is:

```js
const hash = await client.writeContract({
  account, address: CORE, functionName, args, value: 0n, leaderOnly: false,
});
const accepted = await client.waitForTransactionReceipt({
  hash, status: "ACCEPTED", fullTransaction: true,
});
const finalized = await client.waitForTransactionReceipt({
  hash, status: "FINALIZED", fullTransaction: true,
});
```

An RPC timeout is not proof that a transaction was not broadcast. Never
blindly rebroadcast after a timeout. First reconcile by transaction hash and
then by the authoritative Core views (`get_tender`, binding/readiness,
settlement accounting, or the relevant result context). If the transaction is
accepted/finalized, resume from observed state. If it is absent and a retry is
necessary, re-read the state and verify the operation's idempotency conditions
before issuing one new write. Persist the operation hash and lifecycle object
ID in the caller's journal.

This rule is especially important for evaluation, review, payout, and refund:
the child message may still be finalizing after the outer RPC call returns.
The parked canonical E2E is post-submission optional and is not a prerequisite
for production integration.
