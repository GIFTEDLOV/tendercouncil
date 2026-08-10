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
