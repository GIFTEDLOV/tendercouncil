# Canonical finalized pilot expectation

This file is the pre-evaluation expectation for the one canonical Bradbury
pilot. It is committed before `start_evaluation` and must not be edited after
the Evaluator output is known.

- Pilot ID: `TENDER_PILOT_V21_20260816T164802Z`
- Tender ID: `TENDER_PILOT_V21_20260816T164802Z`
- Bid A ID: `TENDER_PILOT_V21_20260816T164802Z-bid-a`
- Bid B ID: `TENDER_PILOT_V21_20260816T164802Z-bid-b`
- Fixture bytes commit: `81b5656a311cf0eb83b651422c848d11b5bde47e`
- Buyer: `0xe0f17BEf0587c3b66D2eB4BBE705dFf821AbDde7`
- Bidder A: `0xC8732D516AD35CB7A137548878358856dBD9D8f2`
- Bidder B: `0x4cB46003f11755feCfFCfe119824C420d3dc059B`

## Expected deterministic admissibility

Both bids are expected to be admissible: each is submitted by a distinct
bidder during `OPEN`, has a positive quote below the `50,000,000,000,000,000`
wei escrow, delivery within 30 days, support of at least 90 days, the locked
`tendercouncil.bid.v1` schema, valid HTTPS proposal commitments, and one valid
required capability evidence commitment. Neither bid is expected in the
deterministic or integrity-disqualified sets.

## Expected semantic winner

Expected winner: **Bid A** (`TENDER_PILOT_V21_20260816T164802Z-bid-a`).

Bid A is expected to win clearly under the locked rubric
`technical=35;delivery=20;price=20;capability=15;support=10`: it offers the
lower quote (32e15 wei versus 39e15 wei), faster delivery (20 versus 25 days),
longer support (180 versus 120 days), and the more specific security,
acceptance, and operational approach. Bid B remains a valid and meaningfully
comparable proposal, so this is intended as a straightforward comparative
decision rather than an invalid-bid or borderline-score test.

- Expected maximum escrow: `50000000000000000` wei
- Expected winning quote: `32000000000000000` wei
- Expected buyer remainder: `18000000000000000` wei
- Expected accounting: `50000000000000000 = 32000000000000000 + 18000000000000000`

The expectation above was recorded before evaluator output was available.
