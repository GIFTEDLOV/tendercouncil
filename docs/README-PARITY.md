# README parity audit

This is a static release-facing documentation audit. It protects the
README/release prose from drifting away from the v2.1 source, deployment
manifest, generated artifacts, and verification configuration. Re-run it when
release-controlled source, deployment evidence, or public method names change.

Audit basis:

- `contracts/tender_council_core.py`
- `contracts/tender_council_evaluator.py`
- `artifacts/tender_council_bradbury_v21_deployment.json`
- `artifacts/tender_council_v21_split-deployment-dry-run.json`
- `artifacts/tender_council_v21_size-budget.json`
- `README.md`, `SUBMISSION.md`, and `docs/RELEASE.md`
- `.github/workflows/ci.yml`

## Release identity checklist

| Check | Expected current value | Status |
| --- | --- | --- |
| Network | `testnet-bradbury` | PASS |
| Chain | `4221` | PASS |
| Core address | `0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd` | PASS |
| Evaluator address | `0x023AB3434761715a531884Ca0852aC14beE03acE` | PASS |
| Release line | `v2.1`, finalized, bound | PASS |
| Evaluator version | `tendercouncil.evaluator.v2.1` | PASS |
| `get_production_ready` readback | `true` | PASS |
| Binding transaction | `0x186e412e4132763dc5b437a23944b30a5bffa5cd751c872b6e25ad5631c4acbf` | PASS |
| Evaluator deployable hash | `sha256:e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b` | PASS |
| Historical addresses | Labeled historical/superseded, never current | PASS |
| Parked E2E | `POST_SUBMISSION_OPTIONAL`, not a release blocker | PASS |

## Source and artifact parity checklist

| Check | Evidence/expected value | Status |
| --- | --- | --- |
| Core source hash | `54acb8815411c3bbc0623a6587cdb4a29bc77a0a8b91b3c7022c4d77c6dbfbd2` | PASS |
| Core deployable hash | `6228d9a14be5d8747ad7935795a86663ee5d599d741a07c6265b029f33eccb63` | PASS |
| Evaluator source hash | `1956b3c984ec6310c4a4d6532e8bd8f456532b9c4e171dae82aa9ae8d7194e5d` | PASS |
| Evaluator deployable hash | `e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b` | PASS |
| Mechanical generator | `tools/make_deployable.py`; split checker compares exact bytes | PASS |
| Size gate | v2.1 split artifacts under the conservative 42 KB target | PASS |
| Manifest inclusion | `MANIFEST.sha256` covers production artifacts, manifest, docs, fixtures, and verification tools | PASS |

## Schema checklist

The README and release docs must use these exact source literals:

```text
tendercouncil.core.v2.1
tendercouncil.evaluator.v2.1
tendercouncil.snapshot.v1
tendercouncil.bid.v1
tendercouncil.evidence.v1
tendercouncil.challenge.v1
```

The Core challenge digest wrapper is the internal
`tendercouncil.challenges.v1` value. It is not a replacement for the external
challenge body schema. Status: **PASS**.

## Public method-name checklist

The current source contains these `@gl.public` methods. Any README API change
must be checked against the decorators and signatures, not inferred from an
older monolith.

### Core views

`get_production_ready`, `get_evaluator_binding`, `get_contract_balance`,
`get_settlement_accounting`, `get_tender`, `get_bid`, `get_challenge`,
`list_tender_ids`, `get_evaluation_context`, `get_closed_snapshot`,
`get_review_context`.

### Core writes

`bind_evaluator`, `create_tender`, `open_tender`, `submit_bid`, `close_tender`,
`start_evaluation`, `expire_evaluation_attempt`, `retry_evaluation`,
`receive_evaluation_result`, `receive_evaluation_failure`,
`start_response_window`, `submit_challenge`, `advance_after_response`,
`receive_review_result`, `receive_review_failure`, `expire_review_attempt`,
`retry_review`, `settle_award`, `confirm_settlement`, `cancel_tender`,
`confirm_refund`, `refund_no_valid_bid`, `confirm_no_valid_refund`,
`refund_failed_evaluation`.

### Evaluator views and writes

Views: `get_evaluation_result`, `get_core_address`, `get_evaluator_version`,
`get_review_result`.

Writes: `start_evaluation_job`, `start_review_job`.

Status: **PASS**. The README describes the callback writes as callback-only
and presents Core as the normal integration entry point.

## Security and consensus claims

The release-facing documentation must agree with the current code on these
claims:

- Core owns escrow, lifecycle, callback correlation, and settlement.
- Evaluator is constructor-bound to Core, has no payable method, and emits only
  finalized callbacks.
- Authentication, exact-byte SHA-256, schema validation, deterministic
  admissibility, and semantic evaluation are separate layers.
- Result partitions and winner identity are exact; deployed score tolerance is
  exactly `SCORE_TOLERANCE = 2`.
- Core derives score totals and rejects unresolved top-score ties.
- Model failure states are `MODEL_CANDIDATE_INVALID` and
  `MODEL_PROVIDER_UNAVAILABLE`; `DISAGREE` and
  `DETERMINISTIC_VIOLATION` are consensus/runtime outcomes, not local winners.
- A provisional award is non-payable until the response/challenge lifecycle
  completes and settlement requires finalized transfer readback.
- RPC timeout recovery requires reconcile-before-retry and never blind
  rebroadcast.

Status: **PASS** against `docs/CONSENSUS-NOTES.md`, `docs/INTEGRATION.md`,
`docs/SECURITY.md`, and `docs/THREAT_MODEL.md`.

## Maintenance rule

If this audit fails, correct release-facing documentation and evidence links
first. Do not change contract code merely to make stale prose true. Do not
rewrite or delete historical artifacts; label them and retain their provenance.
