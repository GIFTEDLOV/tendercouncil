# TenderCouncil deployment

## Current network

- Target: GenLayer Bradbury testnet
- RPC: `https://rpc-bradbury.genlayer.com`
- Chain ID: `4221`
- CLI: `genlayer` 0.39.1 installed locally
- Active local CLI accounts were observed with `genlayer account list`; keys
  are not recorded in this repository.

## Preserved deployment evidence

Historical Stage 0/1 deployment and smoke transaction IDs are retained in:

- `artifacts/bradbury-evaluator-probes.json`
- `artifacts/bradbury-stage1-evaluator-attempt.json`
- `artifacts/bradbury-stage1-postfix-attempt.json`
- `artifacts/bradbury-stage1-smoke.json`

The evaluator-enabled attempts are not green: the preserved validator votes
include `DETERMINISTIC_VIOLATION`. They are provenance, not release evidence.

## Release rule

No production deployment is accepted as a release until a repeatable script
records the source hash, runner header, constructor arguments, network, sender,
deployment receipt, finality, and every smoke transaction/readback. Manual
PowerShell argument marshalling is not a release mechanism.

## Current status

Repeatable tooling now exists and has been exercised through failed
preflight-verified production deployment attempts:

- `tools/release_preflight.py` compares network, chain ID, sender, source hash,
  runner header, constructor arguments, schema version, fixture hashes,
  artifact/source parity, and deployment transport. Any mismatch fails closed.
- `deploy/deploy_production.py` invokes `genlayer deploy` with a list of
  arguments, records the exact source/artifact hash and raw transport result,
  and never performs implicit network or shell-string marshalling.

The first production source submission (`66,964` bytes) and the generated,
linted compact artifact (`56,272` bytes) were both rejected by Bradbury before
contract creation with `BlockPubdataLimitReached` / `intrinsic gas too low`.
The wrapper recorded both attempts under `artifacts/`; no production contract
address or evaluator transaction exists from these attempts. This is the
current deployment-size blocker, not a successful deployment.

The UI stop gate remains closed pending a production-shaped evaluator-enabled
Bradbury flow, protocol-finality evidence, and release-artifact verification.
