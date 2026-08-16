# TenderCouncil CI and verification

The authoritative CI definition is
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml). It runs on pushes to
`main` and pull requests. It uses Ubuntu, Python `3.12`, and installs the
committed `requirements.txt` without an unrequested dependency upgrade.

## Current job

The workflow has one `contract` job with these stages.

### Toolchain and static contract checks

```text
python -m pip install -r requirements.txt
python tools/ci_diagnostics.py --resolve
genvm-lint check contracts/tender_council.py
genvm-lint validate contracts/tender_council.py
genvm-lint check contracts/tender_council_production.py
genvm-lint validate contracts/tender_council_production.py
genvm-lint check contracts/tender_council_core.py
genvm-lint validate contracts/tender_council_core.py
genvm-lint check contracts/tender_council_evaluator.py
genvm-lint validate contracts/tender_council_evaluator.py
```

`ci_diagnostics.py --resolve` resolves the direct GenVM runtime requested by
`TENDERCOUNCIL_DIRECT_GENVM_VERSION`, which the workflow sets to `v0.2.16`.
The contracts themselves retain their pinned `py-genlayer` header.

### Finalized-message and semantic/security probes

```text
python tools/check_finalized_messages.py contracts/tender_council_core.py
python tools/check_finalized_messages.py contracts/tender_council_evaluator.py
python tools/equivalence_trials.py
python tools/semantic_policy_trials.py
python tools/diagnostic_evaluation_replay.py --source contracts/tender_council_evaluator.py
python tools/challenge_integrity_trials.py
python tools/review_lookup_trials.py
python tools/evaluator_no_valid_trial.py
python tools/financial_trials.py
```

The finalized-message checker fails closed if a contract emit site is not
explicitly `on="finalized"`. The remaining probes cover validator equivalence,
semantic policy boundaries, exact evaluator replay, challenge integrity,
review lookup, no-valid-bid behavior, and financial settlement/recovery.

### Generated artifacts and size gate

```text
python tools/make_deployable.py contracts/tender_council_core.py artifacts/tender_council_core_v21_deployable.py
python tools/make_deployable.py contracts/tender_council_evaluator.py artifacts/tender_council_evaluator_v21_deployable.py
python tools/split_size_check.py
```

`split_size_check.py` fails if either generated artifact differs from the
mechanical source transformation or exceeds the conservative 42,000-byte outer
target. The preferred engineering target is 40,000 bytes. The committed
deployment manifest and size artifacts record the production bytes and hashes.

### Direct tests and mutation tests

```text
python tools/ci_diagnostics.py
python -m pytest
python tools/mutation_test.py
python tools/split_mutation_test.py
python tools/reduced_model_mutation_test.py
```

The pytest suite covers direct contract behavior, calldata stability,
production foundation, split contracts, time determinism, recovery state
machines, and security trials. The three mutation commands are the original
security mutations, split-contract security mutations, and v2.1 reduced-model
mutation checks.

## What CI does not do

This workflow is local/repository verification. It does not deploy, bind,
create a tender, submit a bid, resume the parked Bradbury E2E, or broadcast a
transaction. The read-only deployment probes and finalized deployment evidence
are separate provenance artifacts. Do not add an expensive campaign merely to
populate documentation; update this page only when `.github/workflows/ci.yml`
changes or committed evidence establishes a new verification category.
