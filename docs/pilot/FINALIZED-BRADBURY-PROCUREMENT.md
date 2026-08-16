# Verified Bradbury procurement pilot

## Scope

This record is the canonical post-submission pilot attempt for the already
deployed v2.1 Core/Evaluator pair. The intended scope was one funded,
two-bid, no-challenge procurement through `SETTLED`. The attempt is preserved
here honestly: create and open finalized, but the first bid was submitted after
the immutable bidding deadline because Bradbury finality consumed the pilot's
one-hour deadline. No second tender was started.

**Pilot status: BLOCKED before comparative evaluation.** This document must
not be read as proof of a finalized procurement lifecycle.

## Production deployment

| Item | Value |
| --- | --- |
| Core | `0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd` |
| Evaluator | `0x023AB3434761715a531884Ca0852aC14beE03acE` |
| Network | GenLayer Bradbury testnet |
| Chain | `4221` |
| Evaluator version | `tendercouncil.evaluator.v2.1` |
| Binding transaction | `0x186e412e4132763dc5b437a23944b30a5bffa5cd751c872b6e25ad5631c4acbf` |
| `production_ready` readback | `true` |
| Binding readback | bound, requested address/version/code hash |

The frozen production source hashes were unchanged during the attempt: Core
SHA-256 `54acb8815411c3bbc0623a6587cdb4a29bc77a0a8b91b3c7022c4d77c6dbfbd2`
and Evaluator SHA-256
`1956b3c984ec6310c4a4d6532e8bd8f456532b9c4e171dae82aa9ae8d7194e5d`.

## Actors

| Role | Public address |
| --- | --- |
| Buyer | `0xe0f17BEf0587c3b66D2eB4BBE705dFf821AbDde7` |
| Bidder A | `0xC8732D516AD35CB7A137548878358856dBD9D8f2` |
| Bidder B | `0x4cB46003f11755feCfFCfe119824C420d3dc059B` |

No private keys are included in this repository record.

## Precommitted expectation

The immutable fixture bytes were committed at
`81b5656a311cf0eb83b651422c848d11b5bde47e`; `EXPECTED.md` was committed and
pushed before the attempted evaluation in `d18f1e9`. It expected both bids to
be admissible and Bid A (`TENDER_PILOT_V21_20260816T164802Z-bid-a`) to win the
locked `35/20/20/15/10` rubric. The expected escrow was `50000000000000000`
wei, expected quote `32000000000000000` wei, and expected remainder
`18000000000000000` wei.

No evaluator output was produced, so there is no actual-winner comparison.

## Transaction record

| # | Action | Actor | Full transaction hash / observation | Final status | Consensus | Execution | Resulting Core state |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | create funded tender | Buyer | `0xb4088b5c36548f01fe448c5fbbda209502ab1ad2ec8561f59b9f264694615f5d` | FINALIZED | AGREE | FINISHED_WITH_RETURN | DRAFT |
| 2 | open tender | Buyer | `0xe547cb66a561cefacfeb6ee324d53d19d23cabae62a82c1d08ca69787e7fb38b` | FINALIZED | AGREE | FINISHED_WITH_RETURN | OPEN |
| 3 | Bid A attempt | Bidder A | `0xae04522d89d09e8405312358e6add93b31ac902e29d236e6a4bee26f63405ed3` | FINALIZED | validator split DISAGREE | FINISHED_WITH_ERROR | OPEN; no bid stored |
| 4 | Bid B | Bidder B | NOT RUN | — | — | — | OPEN |
| 5 | close / frozen snapshot | Buyer | NOT RUN | — | — | — | OPEN |
| 6 | start evaluation | Buyer | NOT RUN | — | — | — | OPEN |
| 7 | evaluator callback | Evaluator | NOT OBSERVED | — | — | — | OPEN |
| 8 | start response window | Buyer | NOT RUN | — | — | — | OPEN |
| 9 | advance after response | Buyer | NOT RUN | — | — | — | OPEN |
| 10 | settle award | Buyer | NOT RUN | — | — | — | OPEN |
| 11 | confirm settlement | Buyer | NOT RUN | — | — | — | OPEN |
| 12 | confirm refund | Buyer | NOT RUN | — | — | — | OPEN |

The finalized Bid A trace is preserved in the journal-linked observation. Its
contract return data decodes to `bidding is closed`. The transaction was not
resent; the journal records the original hash and the post-finality state read.
The immutable deadline was `1786902835`; after the create/open finality delay,
the bid attempt was no longer eligible. This was a pilot scheduling failure,
not evidence of a production contract change.

## Evaluation

No close snapshot, evaluation nonce, Evaluator job, callback, or evaluation
result digest exists for this attempt. Therefore:

- expected winner: Bid A;
- actual winner: not produced;
- expected-winner match: NOT APPLICABLE;
- semantic comparative evaluation: not live-proven.

## Settlement

The tender accounting read immediately before the failed Bid A verification
was:

| Field | Observation |
| --- | ---: |
| Initial escrow for this tender | `50000000000000000` wei |
| Winner payout | `0` wei |
| Buyer remainder | `0` wei |
| Tender state | `OPEN` |
| Financial outflow pending | `false` |
| Core balance observation | `130000000000000000` wei |

The Core balance includes `80000000000000000` wei of historical escrow from
preserved prior evidence plus this pilot's escrow. It is not a per-tender
settlement result and must not be interpreted as a zero-balance assertion.

## What this proves

- the requested production binding readback still passes;
- the production Core accepted and finalized a fresh funded tender;
- the production Core accepted and finalized opening that tender;
- the transaction journal persisted hashes and prevented blind rebroadcast;
- Bradbury finality latency is material to deadline selection.

## What this does not prove

- two valid bids entering one tender;
- a closed canonical snapshot;
- semantic comparative evaluation;
- provisional or final award;
- response-window completion;
- winner payment, buyer remainder refund, or `SETTLED`;
- challenge/review or retry branches;
- mainnet behavior or third-party audit certification.

The canonical journal is
`artifacts/tender_council_bradbury_v21_finalized_pilot_journal.json`.
