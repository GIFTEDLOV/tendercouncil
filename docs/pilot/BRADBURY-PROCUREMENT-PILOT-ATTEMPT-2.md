# Bradbury procurement pilot — Attempt 2 Phase A

## Status

**IN PROGRESS — BID A FINALITY UNRESOLVED; PHASE A INCOMPLETE**

Pilot 2 was deliberately stopped before Bid B because the exact Bid A
transaction remained `ACCEPTED` rather than `FINALIZED` when the local bounded
session ended. A read-only check observed the Bid A record stored, but that
does not satisfy the required finalized-transaction gate. Bid B was not
broadcast.

No close, evaluation, response, award, settlement, refund, or Attempt-1
recovery write has been attempted.

## Production and actors

| Item | Value |
| --- | --- |
| Core | `0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd` |
| Evaluator | `0x023AB3434761715a531884Ca0852aC14beE03acE` |
| Network | GenLayer Bradbury, chain `4221` |
| Evaluator version | `tendercouncil.evaluator.v2.1` |
| Pilot 2 ID | `PILOT2_20260816T184818Z` |
| Fixture commit | `837565d9f0b4633f3ae111197d839f3790f164ca` |
| Expectation commit | `dbe77d6fff8215973a90dc0ac0df2414dc13cbac` |
| Buyer | `0xe0f17BEf0587c3b66D2eB4BBE705dFf821AbDde7` |
| Bidder A | `0xC8732D516AD35CB7A137548878358856dBD9D8f2` |
| Bidder B | `0x4cB46003f11755feCfFCfe119824C420d3dc059B` |

## Tender and deadline

| Item | Value |
| --- | --- |
| Tender ID | `TENDER_PILOT_V21_P2_20260816T184818Z` |
| Maximum escrow | `50000000000000000` wei |
| Stored bidding deadline | `1786992789` |
| Deadline UTC | `2026-08-17T18:53:09.000Z` |
| Resume-not-before target | `2026-08-17T18:58:09.000Z` |
| Response window | `600` seconds |
| Rubric | `technical=35;delivery=20;price=20;capability=15;support=10` |

The deadline was selected approximately 24 hours after creation. The
read-only stop observation recorded `80789` seconds remaining. The required
12-hour Bid-A and 10-hour Bid-B safety margins were not the blocker; Bid A
finality was unresolved first.

## Transaction record

| Action | Actor | Transaction | Final status | Core/readback result |
| --- | --- | --- | --- | --- |
| Create funded tender | Buyer | `0x191ead5b94459a222932212eb1f5fc10b70c8d266347c9338e8fb1e44f2b75a4` | FINALIZED / AGREE / FINISHED_WITH_RETURN | `DRAFT`, escrow stored |
| Open tender | Buyer | `0x7b109921eb8669966e39b172a903be53342a114a1f73a29fbbdba66dde4afb86` | FINALIZED / AGREE / FINISHED_WITH_RETURN | `OPEN` |
| Submit Bid A | Bidder A | `0x2e5d3752ad6523484118a6319a289c1902bec3508c16e9c44cc31a81eee1abe2` | ACCEPTED / AGREE / FINISHED_WITH_RETURN; not FINALIZED | Read-only check observed Bid A stored |
| Submit Bid B | Bidder B | NOT RUN | NOT RUN | No Bid B write |
| Close | Buyer | NOT RUN | NOT RUN | No snapshot |
| Evaluation onward | — | NOT RUN | NOT RUN | No comparative or settlement path |

Bid A was broadcast once and its hash is preserved in the durable operation
journal. The local command wrapper timed out after its bounded one-hour run
while the transaction was still `ACCEPTED`; this is not treated as failure.
The next action must reconcile this exact hash and require `FINALIZED` before
any Bid B write.

## Stored Bid A observation

The read-only observation after the stop found:

- tender: `TENDER_PILOT_V21_P2_20260816T184818Z`;
- bidder: Bidder A;
- quote: `32000000000000000` wei;
- delivery: `20` days;
- support: `180` days;
- proposal and evidence commitments: exact expected immutable values;
- tender state: `OPEN`;
- financial outflow pending: `false`;
- Core balance: `180000000000000000` wei.

The record is useful evidence, but the Pilot 2 Phase-A gate remains incomplete
until the exact Bid A transaction is finalized.

## Precommitted expectation

The expectation was committed before any Pilot 2 live write. Bid A and Bid B
were both expected to be valid, with Bid A the expected semantic winner under
the locked rubric. The expected escrow was `50000000000000000` wei; expected
Bid-A payout was `32000000000000000` wei; expected remainder was
`18000000000000000` wei. No Evaluator output exists.

## Journal

The append-only/reconciliation-oriented journal is
`artifacts/tender_council_bradbury_v21_pilot2_journal.json`. It preserves the
initial local reconciliation errors, exact create/open/Bid-A hashes, poll
observations, the unresolved stop, and the read-only Bid-A storage observation.

Attempt 1 remains separately preserved as
`TENDER_PILOT_V21_20260816T164802Z`, `OPEN`, with its original
`50000000000000000` wei escrow and no financial outflow pending. Its intended
later recovery is `close_tender` → zero-bid `NO_VALID_BID` evaluation →
`refund_no_valid_bid` → `confirm_refund`, but no Attempt-1 recovery write was
run in this session.
