# TenderCouncil release status

This is the authoritative status page for the submitted repository release.
Contract bytes and production addresses are unchanged by post-submission
repository polish.

## CURRENT RELEASE: v2.1

| Field | Value |
| --- | --- |
| Network | GenLayer Bradbury testnet |
| Chain | `4221` |
| Core | `0x5ADbA50CE6c6fFBA738f212ba12fC3C78B2664cd` |
| Evaluator | `0x023AB3434761715a531884Ca0852aC14beE03acE` |
| Core schema | `tendercouncil.core.v2.1` |
| Evaluator schema | `tendercouncil.evaluator.v2.1` |
| Snapshot schema | `tendercouncil.snapshot.v1` |
| Bid/manifest schema | `tendercouncil.bid.v1` |
| Evidence schema | `tendercouncil.evidence.v1` |
| Challenge schema | `tendercouncil.challenge.v1` |
| Core source SHA-256 | `54acb8815411c3bbc0623a6587cdb4a29bc77a0a8b91b3c7022c4d77c6dbfbd2` |
| Core deployable SHA-256 | `6228d9a14be5d8747ad7935795a86663ee5d599d741a07c6265b029f33eccb63` |
| Evaluator source SHA-256 | `1956b3c984ec6310c4a4d6532e8bd8f456532b9c4e171dae82aa9ae8d7194e5d` |
| Evaluator deployable SHA-256 | `e2042a0176068c471abb993ec7a588d0bfcc41f96226f14aa1ec6dd49d74831b` |
| Core deployment transaction | `0x2cee5c4cb68b3ee97092c127e4688f24b54ffef1db9e7fe9b432922a0f1ce6ff` |
| Evaluator deployment transaction | `0xdb7d159f7804f9626e61bf93ded39e8c1abdd3bf5c1f5ff1f6deb73a9862e261` |
| Binding transaction | `0x186e412e4132763dc5b437a23944b30a5bffa5cd751c872b6e25ad5631c4acbf` |
| Binding status | `FINALIZED` / `AGREE` / `FINISHED_WITH_RETURN` |
| `get_production_ready` readback | `true` |
| Core balance readback | `0` at the recorded readback |

The exact deployment and binding evidence is
[`artifacts/tender_council_bradbury_v21_deployment.json`](../artifacts/tender_council_bradbury_v21_deployment.json).
The binding commits the exact bytes of
`artifacts/tender_council_evaluator_v21_deployable.py`, not the readable source
hash.

## What is proven

- The production Core and Evaluator deployments in the manifest are finalized
  on Bradbury chain `4221`.
- The Evaluator constructor points to the production Core and uses
  `tendercouncil.evaluator.v2.1`.
- The one-time Core binding is finalized, points to the production Evaluator,
  commits its exact deployable artifact hash, and reads back
  `production_ready=true`.
- The repository contains generated Core/Evaluator artifacts with the recorded
  source/artifact parity and size evidence.
- Committed local verification evidence covers deterministic state behavior,
  finalized-only cross-contract messaging, semantic/equivalence paths,
  challenge/review handling, no-valid-bid and financial recovery paths, and
  security mutation tooling. The current CI workflow documents the commands.

These claims establish the release deployment and the repository's recorded
verification gates. They do not claim that every possible external URL, model
provider, or future tender will be available.

## Known limitations

- Proposal, evidence, and challenge URLs are external dependencies. Exact
  hashes and schemas protect integrity, but they cannot make an unavailable
  provider available.
- Semantic evaluation is deliberately bounded and depends on finalized
  GenLayer validator execution. Model-derived rationale and confidence are
  informational; winner identity, bid partitions, and financial outcomes are
  contract-checked.
- A live application frontend is not part of this release. Integrators use the
  public Core API and may use the no-broadcast examples.
- The canonical five-bid lifecycle E2E was not required for submission and is
  intentionally parked as post-submission optional validation. Its parked
  state is preserved and is not a release defect.

## Release gates

```text
RELEASE BLOCKERS = none
POST-SUBMISSION OPTIONAL VALIDATION = parked canonical E2E
E2E_STATUS = POST_SUBMISSION_OPTIONAL
```

The parked E2E is recorded in
[`artifacts/tender_council_bradbury_v21_e2e_parked.json`](../artifacts/tender_council_bradbury_v21_e2e_parked.json).
This repository completion does not resume it, modify its journal, create a
tender, or broadcast a transaction.

## Historical v2/v2.1 corrections

Earlier v2 and v2.1 deployment records, failed attempts, and diagnostic
artifacts remain preserved as historical provenance. The release line then
corrected the split snapshot/evaluator shape boundary, made result and review
correlation digest-checked, reduced the model-output surface, and finalized the
replacement Core/Evaluator binding. The first binding attempt's address
encoding failure and the later successful `CalldataAddress` binding are both
retained in the deployment manifest. Historical addresses are superseded and
must not be selected by an integration or deployment script.
