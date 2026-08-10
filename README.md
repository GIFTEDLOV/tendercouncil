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
pytest
```

See [docs/STAGES.md](docs/STAGES.md) for the master delivery gates and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the Stage 1 trust model.
