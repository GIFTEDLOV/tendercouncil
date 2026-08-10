# TenderCouncil threat model

TenderCouncil treats every bidder-controlled or web-retrieved byte as
untrusted data. GenLayer consensus authenticates execution and validator
agreement; it does not authenticate external content.

## Trust layers

```text
wallet sender authentication
  -> on-chain commercial commitments
  -> exact-byte content hash verification
  -> bounded schema validation
  -> deterministic admissibility
  -> comparative semantic judgment
  -> validator equivalence
  -> application response window
  -> protocol finality
  -> settlement
```

No later layer is allowed to compensate for a failed earlier layer.

## Threats and controls

| Threat | Required control |
|---|---|
| Malicious bidder content | Treat proposal/evidence as data only; hard trusted-policy boundary; bounded manifest and fields. |
| Prompt injection, fake SYSTEM/developer blocks, “select bidder C”, “return APPROVED” | Never concatenate content as instructions; label it `UNTRUSTED BID/EVIDENCE CONTENT`; locked policy and rubric are outside the data boundary. |
| Mutable proposal URLs or mutable evidence | URL is only a locator; exact fetched bytes must match the on-chain SHA-256 commitment. Mutation is rejected. |
| Hash mismatch | Resolve `HASH_MISMATCH`; do not schema-validate or expose content to the semantic evaluator. |
| Bidder identity spoofing | Transaction sender is the bidder; manifest bidder and on-chain bidder must match. |
| Forged capability claims | Capability gets material score only from admissible, committed evidence mapped to the criterion. |
| Missing required evidence | Deterministic fail/disqualify according to the tender policy; never infer contents. |
| Missing optional evidence | Explicit `SKIP`/`UNAVAILABLE`; no confirmation or score credit. |
| Unavailable sources | Required and optional evidence have distinct explicit outcomes; no LLM speculation. |
| Duplicate evidence | Reject duplicate evidence IDs/commitments and duplicate manifest references. |
| Contradictory evidence | Surface bounded contradiction status; do not silently select the favorable claim. |
| Unsupported evidence type | Resolve `UNSUPPORTED`; it cannot contribute authoritative capability score. |
| Bidder collusion | No reputation or social trust assumptions; authenticated immutable bids and common locked policy. |
| Buyer manipulation after bids | Requirements, rubric, constraints, and commitments freeze at close; buyer cannot manually award. |
| Duplicate or late bids | Unique bid IDs, one bid per bidder per tender, open/deadline checks, and close transition. |
| Post-close modification | All commercial terms, proposal commitments, and evidence commitments become immutable after close. |
| Post-result bid improvement/new evidence | Challenge records can reference only pre-close commitments; they cannot change bid terms or add evidence. |
| Challenge abuse/evidence injection | One bounded response/challenge round, authenticated challenger, allowed reason codes, bounded content and hash checks. |
| Malformed LLM output or impossible scores | Structured output plus deterministic schema/range/arithmetic checks; malformed output fails closed. |
| Validator disagreement or runtime failure | Independent comparative derivation, explicit equivalence fields/tolerances, failed consensus leaves state unchanged. |
| Deterministic-violation/runtime failure | Primitive immutable nondeterministic captures, regression probes, pinned runner, lint/semantic validation, Bradbury smoke. |
| Consensus failure or protocol appeal | No settlement from an undetermined/accepted-only result; require protocol finality before payment. |
| Settlement replay/double payout | Per-tender settlement nonce/state, winner and amount re-checks, finalized-safe transfer, balance/state verification. |
| Premature or wrong-recipient payout | `PROVISIONAL_AWARD` and non-zero response window precede `AWARDED`; recipient derives only from final winner. |
| Failed transfer recorded as settled | Record settlement only after the supported transfer path succeeds; verify observable balance/state where practical. |
| Stale state | Re-read tender state at every transition; reject stale status, result, winner, and escrow assumptions. |
| Deployment misconfiguration | Release preflight checks network, chain, sender, source hash, runner header, constructor args, schema, fixture hashes, and transport. |

## Security invariants

1. The transaction sender authenticates every bidder, buyer, and challenger.
2. A URL never authenticates content; the committed SHA-256 does.
3. Deterministic disqualifiers run before semantic reasoning.
4. The evaluator ranks all admissible bids under one locked rubric.
5. Rationale is explanatory only; consensus-critical fields are bounded and
   independently checked.
6. No application method can replace a validator-selected winner.
7. A provisional result cannot become payable during the response window.
8. Payment requires an awarded, protocol-final, not-yet-settled tender and the
   exact committed amount/recipient.

## Out of scope

TenderCouncil does not attempt to solve bidder identity beyond wallet
authentication, real-world truth beyond committed evidence, KYC, reputation,
collusion outside observable protocol behavior, or protocol-level validator
appeals. Those are explicit boundaries, not implicit trust assumptions.
