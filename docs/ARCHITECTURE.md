# TenderCouncil architecture

`contracts/tender_council.py` is the preserved Stage 1 prototype. The current
production foundation is `contracts/tender_council_production.py`; it now
supports public buyers, multiple tender records, exact payable award custody,
immutable commercial bid terms, and a bounded bid-manifest schema. Comparative
evaluation, challenges, finalized settlement, and Bradbury evaluator proof
remain behind the UI stop gate.

TenderCouncil separates the procurement record from the later judgment step.

```text
issuer -> TenderCouncil -> tender lifecycle
supplier -> TenderCouncil -> bid + evidence provenance
evaluator (later) -> evidence sources -> consensus-backed decision
frontend (gated) -> public views and authenticated writes
```

## Trust boundaries

- The caller address is the only identity used by the Stage 1 contract.
- The current Stage 1 prototype uses a deployer-owned tender creator; this is
  explicitly not the locked production model. Phase B must make tender buyers
  public creators and remove deployer-administered procurement.
- A tender issuer may open, close, award, or cancel that tender.
- A supplier may append evidence only to its own bid.
- A URI is only a locator. The current evaluator now hashes the exact fetched
  response bytes with the contract's pure-Python SHA-256 routine before UTF-8
  decoding or semantic exposure. A mismatch returns a bounded rejection and
  never reaches the LLM. The production manifest validator applies the same
  exact-byte commitment check before JSON decoding and schema validation.
  External evidence retrieval and required/optional evidence resolution remain
  later production gates. Rationale text is not an equivalence field.

## Production bid manifest (`tendercouncil.bid.v1`)

The proposal URL and `proposal_sha256` are committed in the bid record by the
authenticated transaction sender. After retrieval, the exact response bytes
must match that commitment before the manifest is decoded. The validator then
requires exactly these top-level fields:

```text
schema_version, tender_id, bidder, price, delivery_days, support_days,
proposal, evidence
```

`proposal` must contain exactly `technical_approach`, `delivery_plan`,
`support_plan`, and `requirements`. `requirements` is a bounded list of
bounded strings. `evidence` is a bounded list (maximum eight); each item must
contain exactly `evidence_id`, `kind`, `criterion`, `required`, `url`, and
`sha256`. Evidence IDs and URL/hash commitments must be unique, kinds and
criterion mappings are allowlisted, URLs must be HTTPS, and all hashes are
lowercase `sha256:<64 hex chars>` commitments. Manifest commercial fields must
equal the immutable onchain bid terms, and bidder/tender fields are bound to the
onchain record. Invalid, unavailable, hash-mismatched, or schema-invalid
manifests are recorded as non-authoritative states.

## Comparative evaluator

`evaluate_tender` snapshots every bid for one closed tender. Budget, delivery,
support, deadline, manifest integrity, and manifest-schema failures are removed
before semantic reasoning. It then retrieves each retained manifest's declared
evidence, verifies exact bytes and the bounded evidence schema, and exposes only
`VALID` evidence claims to the model. Required evidence failures disqualify a
bid; optional unavailable evidence is explicitly recorded and skipped.

The structured model result contains the winner, valid/disqualified sets,
criterion scores, winner total, runner-up, confidence enum, and informational
rationale. Deterministic normalization rejects impossible score arithmetic,
out-of-range criterion scores, non-partitioned bid sets, non-candidate winners,
and ties without a later bounded policy. The validator independently reruns the
same bounded snapshot and requires exact agreement on all consensus-critical
fields, including evidence states; rationale is excluded from equivalence.

## State machine

`DRAFT -> OPEN -> CLOSED -> AWARDED`

`DRAFT`, `OPEN`, or `CLOSED` may transition to `CANCELLED`. Bids are accepted
only in `OPEN`; awarding marks one submitted bid `AWARDED` and all sibling bids
`REJECTED`.

## Storage discipline

Persistent collections use GenLayer storage-compatible `TreeMap` and `DynArray`
types. Structured records use `@allow_storage` dataclasses. IDs are supplied by
callers so the records are addressable without relying on host time or a
non-deterministic counter.

## Nondeterministic boundary investigation

The original evaluator failed on Bradbury because its nondeterministic closures
called `json.loads()` inside the sub-VM to reconstruct a list of source metadata
dictionaries, then used those reconstructed objects to drive web and LLM calls.
The failure was isolated with a single Bradbury probe deployment: probes A-E
(constant, web, LLM, web+LLM, and captured immutable strings) were accepted;
the production-shaped F probe was the first failure and returned
`DETERMINISTIC_VIOLATION` for all five validators. Its trace recorded no web or
LLM calls. The installed Bradbury v0.2.11 and local v0.2.16 implementations of
`run_nondet_unsafe` and the storage boundary are byte-identical.

The smallest supported fix is to prepare immutable primitive tuples in the
deterministic context, iterate those tuples directly inside the nondeterministic
closure, and request structured LLM output with `response_format="json"`. No
storage object, JSON-decoded source-context container, or mutable closure state
crosses the boundary. The regression suite cloudpickle-tests both callbacks,
probes installed SHA-256 behavior, and retains the full probe evidence in
`artifacts/bradbury-evaluator-probes.json`.

The first post-fix production-shaped smoke reached an accepted bounded result,
but one of five validators still returned `DETERMINISTIC_VIOLATION`; its trace
does not identify a cause or report web/LLM calls. This is preserved in
`artifacts/bradbury-stage1-postfix-attempt.json` and blocks evaluator-enabled
Bradbury release proof and the UI gate until explained and fixed.
