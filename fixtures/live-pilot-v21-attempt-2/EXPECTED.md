# Pilot 2 pre-live expectation

This is the pre-live expectation for the second Bradbury procurement pilot.
It must not be edited after the first Pilot 2 live write or after any
Evaluator output.

- Pilot 2 ID: `PILOT2_20260816T184818Z`
- Tender ID: `TENDER_PILOT_V21_P2_20260816T184818Z`
- Bid A ID: `TENDER_PILOT_V21_P2_20260816T184818Z-bid-a`
- Bid B ID: `TENDER_PILOT_V21_P2_20260816T184818Z-bid-b`
- Fixture bytes commit: `837565d9f0b4633f3ae111197d839f3790f164ca`
- Buyer: `0xe0f17BEf0587c3b66D2eB4BBE705dFf821AbDde7`
- Bidder A: `0xC8732D516AD35CB7A137548878358856dBD9D8f2`
- Bidder B: `0x4cB46003f11755feCfFCfe119824C420d3dc059B`

## Locked rubric

`technical=35;delivery=20;price=20;capability=15;support=10` (total 100).

## Expected deterministic eligibility

Bid A is expected to be valid and Bid B is expected to be valid. Both use the
current `tendercouncil.bid.v1` schema, distinct funded bidder identities,
positive quotes below the maximum escrow, delivery within 30 days, support of
at least 90 days, commit-pinned HTTPS proposal commitments, and one required
capability evidence commitment. Neither bid is intended to be invalid or
disqualified.

## Expected semantic winner

Expected winner: **Bid A** (`TENDER_PILOT_V21_P2_20260816T184818Z-bid-a`).

Bid A is expected to win clearly under the locked rubric: it offers the lower
quote (`32000000000000000` wei versus `39000000000000000` wei), faster delivery
(20 versus 25 days), longer support (180 versus 120 days), and the more
specific security, acceptance, and operational approach. Bid B remains valid
and meaningfully comparable.

- Expected maximum escrow: `50000000000000000` wei
- Expected Bid A quote: `32000000000000000` wei
- Expected Bid B quote: `39000000000000000` wei
- Expected winner payout: `32000000000000000` wei
- Expected buyer remainder: `18000000000000000` wei
- Expected accounting: `50000000000000000 = 32000000000000000 + 18000000000000000`
- Bidding deadline policy: approximately 24 hours after tender creation;
  at least 12 hours must remain before Bid A and at least 10 hours before Bid B.

This expectation was committed before any Pilot-2 live write and before any
Evaluator output.
