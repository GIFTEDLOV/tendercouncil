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

The repository has no repeatable deploy script yet. Local lint and semantic
validation pass, and the direct suite is green, but the UI stop gate remains
closed pending the production contract, preflight, and a green evaluator-enabled
Bradbury flow.
