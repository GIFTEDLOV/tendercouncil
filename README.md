# TenderCouncil

TenderCouncil is an isolated GenLayer Intelligent Contract project for authenticated, evidence-backed procurement awards.

The contract and test corpus are being built in stages. Stage 1 establishes the
deterministic procurement record and provenance model. The frontend is
intentionally held at the UI stop gate until the contract, evidence model,
evaluator, tests, and Bradbury smoke proof are ready.

## Repository

- Expected GitHub repository: `GIFTEDLOV/tendercouncil`
- Default branch: `main`
- GenLayer target: Bradbury testnet

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
CI covers both generated artifacts, and the exact Bradbury pair estimate is
read-only until deployment review.

The frontend remains behind the UI stop gate.

The production pair is in `contracts/tender_council_core.py` and
`contracts/tender_council_evaluator.py`. The previous contracts remain
preserved for regression and provenance.

See [docs/STAGES.md](docs/STAGES.md) for the master delivery gates and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the trust boundaries and
production manifest schema.
