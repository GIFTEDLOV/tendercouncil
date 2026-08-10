# TenderCouncil Stage 1 architecture

TenderCouncil separates the procurement record from the later judgment step.

```text
issuer -> TenderCouncil -> tender lifecycle
supplier -> TenderCouncil -> bid + evidence provenance
evaluator (later) -> evidence sources -> consensus-backed decision
frontend (gated) -> public views and authenticated writes
```

## Trust boundaries

- The caller address is the only identity used by the Stage 1 contract.
- The owner is the deployer and is allowed to create tenders.
- A tender issuer may open, close, award, or cancel that tender.
- A supplier may append evidence only to its own bid.
- A URI and hash are claims about provenance, not proof of the underlying
  document. The evaluator fetches each evidence URI inside a nondeterministic
  block, treats fetched content as untrusted data, constrains the output
  schema, and independently reruns the task before a decision is stored.
  Rationale text is not an equivalence field; decision, score tolerance, and
  evidence count are.

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
storage object, JSON-decoded container, or mutable closure state crosses the
boundary. The regression suite cloudpickle-tests both callbacks and retains the
full probe evidence in `artifacts/bradbury-evaluator-probes.json`.
