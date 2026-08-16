# TenderCouncil

TenderCouncil is an isolated GenLayer Intelligent Contract project for authenticated, evidence-backed procurement awards.

The production backend uses a two-contract architecture: Core owns policy,
escrow, lifecycle, challenges, and settlement; Evaluator performs authenticated
content retrieval, integrity/schema checks, and comparative GenLayer judgment.

## Production deployment (Bradbury testnet, v2.1)

The v2.1 pair is deployed, finalized, and bound on the GenLayer Bradbury
testnet. Core reports `production_ready = true`.

| Item | Value |
| --- | --- |
| Network | `testnet-bradbury` (chain id `4221`) |
| Core (`TenderCouncilCore`) | `0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd` |
| Evaluator (`TenderCouncilEvaluator`) | `0x023AB3434761715a531884Ca0852aC14beE03acE` |
| Evaluator schema version | `tendercouncil.evaluator.v2.1` |
| Evaluator code hash | `sha256:e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b` |
| Binding consensus tx | `0x186e412e4132763dc5b437a23944b30a5bffa5cd751c872b6e25ad5631c4acbf` |
| Binding outcome | `FINALIZED` / `AGREE` / `FINISHED_WITH_RETURN` / zero deterministic violations |
| `get_production_ready` | `true` (bound, correct evaluator, correct version, correct code hash, Core balance `0`) |

The full deployment record, both binding attempts, and readback evidence are in
[`artifacts/tender_council_bradbury_v21_deployment.json`](artifacts/tender_council_bradbury_v21_deployment.json).

Users interact with the deployed pair directly through the GenLayer CLI/SDK
against the Core address above. A dedicated web frontend was intentionally held
behind the project's UI stop gate until the contract, evidence, security, and
Bradbury proof were complete; that gate is now satisfied and any client is an
optional post-submission surface over the same production addresses.

## Repository

- GitHub repository: `GIFTEDLOV/tendercouncil`
- Default branch: `main`
- GenLayer target: Bradbury testnet (chain id `4221`)

## Development

```text
python -m pip install -r requirements.txt
genvm-lint check contracts/tender_council.py
genvm-lint validate contracts/tender_council.py
genvm-lint check contracts/tender_council_production.py
genvm-lint validate contracts/tender_council_production.py
python -m pytest
```

The production deployment is split between `TenderCouncilCore` (custody and
lifecycle) and `TenderCouncilEvaluator` (authenticated evidence and comparative
judgment). The preserved monolith is non-deployable reference material. Local
CI covers both generated artifacts.

Source ⇄ deployable parity, the size gate, mutation tests, state determinism,
GenVM lint, and GenVM validation all pass for the deployed artifacts and are
covered by CI; they do not need re-running unless the contract code changes.

## Why GenLayer

TenderCouncil keeps commercial constraints, escrow, lifecycle, challenge
admission, and settlement in deterministic Core logic. The difficult
procurement question is comparative: which compliant proposal best satisfies
one published rubric? Without GenLayer that decision would depend on one model,
one SaaS backend, or one centralized committee. Independent validators instead
derive the bounded semantic comparison while Core remains the financial source
of truth.

Evidence is never trusted merely because validators agree about it. A bidder's
wallet authenticates the offer, onchain commitments bind proposal and evidence
bytes, the Evaluator verifies exact-byte SHA-256 and schemas, deterministic
admissibility runs before semantic judgment, and only then does comparative
evaluation occur. A result first becomes provisional, then passes a guaranteed
response window and at most one bounded integrity-checked review before
finalized-only payout.

The production pair is in `contracts/tender_council_core.py` and
`contracts/tender_council_evaluator.py`. The previous contracts remain
preserved for regression and provenance.

For the canonical Bradbury proof, the buyer escrows an exact wei budget, five
wallet-authenticated bidders commit immutable manifests and evidence, and the
winner receives its quoted price while the unused remainder returns to the
buyer. See [docs/BRADBURY_E2E.md](docs/BRADBURY_E2E.md) for live proof status.

## Deployment provenance

- Deployment manifest: [`artifacts/tender_council_bradbury_v21_deployment.json`](artifacts/tender_council_bradbury_v21_deployment.json)
  records both contract deployments (finalized), both evaluator-binding attempts,
  the finalized binding readback, and the frozen artifact hashes.
- Binding recovery: the first binding attempt reverted at the outer EVM layer
  because the evaluator address was encoded as a raw string rather than a
  GenLayer `Address`; attempt #2 uses the SDK's explicit calldata `Address`
  wrapper and finalized with `AGREE` / `FINISHED_WITH_RETURN` and zero
  deterministic violations. Both attempts are preserved as forensic evidence.
- End-to-end run: a canonical five-bid E2E is a post-submission validation
  exercise, not a submission requirement. Its current parked state is recorded
  in [`artifacts/tender_council_bradbury_v21_e2e_parked.json`](artifacts/tender_council_bradbury_v21_e2e_parked.json)
  (`E2E_STATUS = POST_SUBMISSION_OPTIONAL`); its operation journal is preserved.
- Additional provenance and trust-boundary detail: [docs/PROVENANCE.md](docs/PROVENANCE.md).

See [docs/STAGES.md](docs/STAGES.md) for the master delivery gates and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the trust boundaries and
production manifest schema.
