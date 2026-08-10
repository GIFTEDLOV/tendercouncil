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
python -m pytest
```

The current Stage 1 direct suite passes locally. Bradbury evaluator smoke is
still a release blocker because the preserved production-shaped attempt has a
validator `DETERMINISTIC_VIOLATION`; see [docs/PROVENANCE.md](docs/PROVENANCE.md).

The frontend remains behind the UI stop gate.

See [docs/STAGES.md](docs/STAGES.md) for the master delivery gates and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the Stage 1 trust model.
