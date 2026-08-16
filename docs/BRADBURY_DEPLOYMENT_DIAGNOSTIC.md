# Bradbury deployment-envelope diagnostic

> **Historical checkpoint (2026-08-10).** This diagnostic predates the
> finalized v2.1 production deployment. Its no-deployment findings describe
> that checkpoint only; current release status is in `docs/RELEASE.md`.

Checked 2026-08-10 from TenderCouncil main at
230ecd0fd2df0249f3b251d8f489bf225129210c. No transaction was signed or
broadcast. Full request records are in:
- artifacts/bradbury-deployment-envelope-probe.json
- artifacts/bradbury-deployment-envelope-probe-chain-rpc.json

## Finding

Bradbury rejects the deployment envelope at the underlying chain pubdata
limit, before GenLayer contract creation.

| source UTF-8 bytes | outer addTransaction data bytes | result |
|---:|---:|---|
| 53,077 | 53,316 | estimated successfully |
| 53,085 | 53,348 | BlockPubdataLimitReached |

The probe uses the installed genlayer-js calldata/transaction encoders and the
live Bradbury ConsensusMain.addTransaction ABI. The compact TenderCouncil
artifact is 54,555 source bytes and 54,820 encoded call-data bytes, which is
1,472 encoded bytes above the last successful boundary. The readable source is
64,069 bytes and encodes to 64,324 bytes.

The observed block gas limit was 0x5f5e100 (100,000,000). The error is
specifically BlockPubdataLimitReached, so increasing gas cannot make an
oversized pubdata payload valid.

## Exact deployment path and versions

The installed versions are:

| component | version |
|---|---|
| Python | 3.14.3 |
| genlayer CLI | 0.39.1 |
| genlayer-js | 1.1.8 |
| genlayer-test | 0.29.2 |
| genlayer-py | 0.16.3 |
| genvm-linter | 0.11.0 |
| Bradbury chain ID | 4221 |

The CLI reads UTF-8 source, builds the constructor calldata object, encodes
the transaction as RLP of source, constructor bytes, and leaderOnly=false,
then ABI-encodes ConsensusMain.addTransaction(sender, zeroAddress, 5, 3,
txData, validUntil). It calls eth_estimateGas on
0x0112Bf6e83497965A5fdD6Dad1E447a6E004271D.

The CLI catches a failed estimate and substitutes hard-coded gas 200000 before
continuing toward submission. Therefore the observed intrinsic gas too low is
a secondary consequence of the failed estimate.

## Attribution

The exact error string is absent from the installed CLI, genlayer-js,
linter, direct-test runner, and TenderCouncil source. It is returned by
eth_estimateGas from both the Bradbury GenLayer RPC and the underlying GenLayer
Chain RPC at https://rpc.testnet-chain.genlayer.com. The rejection is therefore
below the CLI/SDK and below the GenLayer contract ABI.

GenLayer documents GenLayer RPC and the underlying zkSync Elastic Chain as
separate layers. The public zkSync fee-model source defines
max_pubdata_per_batch as the maximum pubdata accepted by a batch. The public
clients do not expose Bradbury's configured maximum or the server's exact Rust
error enum, so the 53,077-53,085 boundary is measured evidence.

The live block response exposed gasLimit, gasUsed, timestamp, and ordinary
fields, but no pubdata-limit field. zks_gasPerPubdata, zks_getBlockDetails, and
zks_L1BatchNumber were unavailable on the Bradbury endpoints used.

References:
- https://docs.genlayer.com/developers/networks
- https://raw.githubusercontent.com/matter-labs/zksync-era/main/core/lib/types/src/fee_model.rs
- https://docs.zksync.io/zksync-protocol/api/zks-rpc
- https://docs.genlayer.com/developers/intelligent-contracts/deploying

## Size budget

tools/size_budget.py produces artifacts/tender_council-size-budget.json.

| component | bytes |
|---|---:|
| protocol/schema constants | 2,715 |
| rubric parsing | 593 |
| native SHA-256 commitment | 155 |
| web fetch/evidence integrity | 2,630 |
| comparative evaluator helpers | 5,657 |
| manifest/schema validation | 5,598 |
| challenge schema/review helpers | 3,176 |
| storage dataclasses | 1,693 |
| contract views/validation | 4,055 |
| tender/bid/policy writes | 7,659 |
| comparative evaluation write | 12,100 |
| provisional award/challenge flow | 13,529 |
| settlement/lifecycle | 3,908 |

The lexical report records 83 comment-token bytes, 1,974 docstring-token bytes,
11,883 whitespace bytes outside token text, and 5,491 prompt-bearing AST
string-line bytes. Lexical categories may overlap semantic regions; the table
of exclusive regions does not.

## Native SHA-256

The pinned direct GenVM accepted hashlib.sha256 in leader and validator
callbacks. Eight direct probe tests pass, covering empty, short, UTF-8, binary,
and multi-block vectors. The former pure-Python production routine matches
hashlib.sha256 byte-for-byte across five vectors; the evidence is in
artifacts/sha256-equivalence.json and is anchored to the prior production
commit.

The readable and generated contracts now use hashlib.sha256. Hashing still
covers exact response bytes before decoding or schema/semantic processing.
Current checks are 38 direct tests, production and artifact lint/semantic
validation, 7/7 mutation checks, release preflight, and source/artifact parity.
A live Bradbury contract has not yet exercised native hashing because the
deployment envelope is blocked.

## Architecture decision

The secure monolith does not fit with a meaningful margin. The recommended
next architecture is a two-contract split, not implemented or deployed in this
checkpoint.

TenderCouncilCore holds buyer identity, tender policy, immutable commercial
terms and commitments, escrow, lifecycle, provisional/final winner, response
window, challenges, and finalized-only settlement. It has no manual winner
substitution method.

TenderCouncilEvaluator reads one immutable closed snapshot; performs
deterministic admissibility, exact-byte retrieval and hashing, bounded manifest
and evidence validation, required/optional resolution, comparative semantic
evaluation, and the one bounded challenge review. It has no payable methods,
escrow, settlement authority, or winner-substitution authority.

The core binds one evaluator address plus evaluator version and exact deployed
Evaluator artifact code hash exactly
once during bootstrap before public tenders. It accepts callbacks only from
that address and only when tender ID, evaluation nonce, closed-state snapshot
digest, result schema, and lifecycle state match. Duplicate, stale,
wrong-tender, or malformed callbacks fail closed. The evaluator uses a
finalized-safe asynchronous message. The core records one result, creates
PROVISIONAL_AWARD, opens the non-zero response window, and retains all
settlement authority.

Projected sizes from the current exclusive regions are approximately 34-35 KB
readable and 29-31 KB deployable for Core, and 29-30 KB readable and 25-27 KB
deployable for Evaluator. Each generated component must be measured
independently before any Bradbury attempt.

## Decision at this historical checkpoint

No new Bradbury deployment was broadcast at this checkpoint. The monolith gate
was closed and the split design was left subject to callback/finality tests and
independent size probes. The later v2.1 finalized deployment supersedes this
checkpoint; the canonical E2E is now separately parked as post-submission
optional validation.
