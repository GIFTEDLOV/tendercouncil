# TenderCouncil Stage 1 architecture

This is the preserved Stage 1 prototype, not the final commercial
architecture. The production lifecycle, escrow, comparative evaluator, and
challenge protocol remain behind the UI stop gate.

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
  never reaches the LLM. Full proposal-manifest schema validation and required/
  optional evidence policy remain production gates. Rationale text is not an
  equivalence field; decision, score tolerance, and evidence count are.

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
`artifacts/bradbury-stage1-postfix-attempt.json` and blocks Phase B and the UI
gate until explained and fixed.
