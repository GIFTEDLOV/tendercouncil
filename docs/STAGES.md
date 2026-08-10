# TenderCouncil delivery stages

## Current inventory (2026-08-10)

| Area | Status | Evidence |
|---|---|---|
| Repository isolation and provenance | DONE | Dedicated `GIFTEDLOV/tendercouncil`, one `origin`, preserved Bradbury artifacts |
| Stage 1 deterministic record | DONE for prototype | `contracts/tender_council.py` |
| Public buyer / multiple independent tenders | PARTIAL | `contracts/tender_council_production.py` allows any buyer and multiple tender records |
| Funded escrow and finalized-safe settlement | PARTIAL | Exact payable award funding and aggregate locked-escrow accounting exist; refund/settlement remain |
| Authenticated bounded bid manifest | PARTIAL | Production bid stores sender-bound commercial terms and SHA-256 commitments; manifest schema remains |
| Exact-byte SHA-256 verification | PARTIAL | Stage 1 evaluator verifies exact fetched bytes; production bid-manifest integration remains |
| Required/optional evidence policy | MISSING | Current evaluator requires at least one evidence item and has no policy states |
| Comparative multi-bid evaluator | MISSING | Current evaluator scores one bid independently |
| Provisional award / response window / bounded challenge | MISSING | Current lifecycle has direct issuer `award_bid` bypass |
| Runtime boundary regression | PARTIAL/BLOCKED | Local probes pass; preserved Bradbury production-shaped smoke has validator `DETERMINISTIC_VIOLATION` |
| Threat model and runtime due diligence | DONE | `docs/THREAT_MODEL.md`, `docs/RUNTIME_DUE_DILIGENCE.md` |
| CI, release preflight, deployment script | PARTIAL | Pinned CI/runtime diagnostics are green; release preflight/deployment script remain |
| Direct test suite | DONE locally | 25 passed; GitHub CI was green on `1dbd0b4` before Phase 2 changes |
| Final UI | STOPPED | UI stop gate remains closed by design |

## Stage 0 — repository and operating baseline

Status: complete at `bf6b542`.

- Dedicated public repository: `GIFTEDLOV/tendercouncil`
- Independent `main` branch with a single intended `origin`
- GenLayer Bradbury is the target network
- Frontend work is held behind the UI stop gate

## Stage 1 — deterministic procurement foundation

Status: deterministic foundation complete locally; the evaluator boundary root
cause is isolated and recorded in `artifacts/bradbury-evaluator-probes.json`.
The post-fix evaluator smoke is not green: four validators agreed and one
reported `DETERMINISTIC_VIOLATION`, with no trace cause. It is preserved in
`artifacts/bradbury-stage1-postfix-attempt.json`; the failed pre-fix attempt
remains in `artifacts/bradbury-stage1-evaluator-attempt.json`.

The Stage 1 contract is intentionally narrow and auditable. It provides:

- owner-authenticated tender creation;
- issuer-only lifecycle transitions;
- supplier-authenticated bid submission;
- evidence records that bind an HTTPS URI and content hash to a bid;
- explicit close, award, reject, and cancel transitions;
- read methods and stable identifier lists for a future client;
- direct-mode tests for authorization and invalid transitions.
- consensus-backed evidence evaluator with prompt-injection boundaries and
  stable-field comparison tests.

Stage 1 does not claim that a submitted URL is truthful. It records the
provenance anchor so a later evaluator can independently retrieve and assess
evidence without treating leader output as trusted input.

## Next gated stages

1. Consensus and smoke proof: explain and fix the remaining validator failure,
   then execute one green evaluator smoke flow from the isolated boundary fix
   before implementing the locked commercial architecture.
2. UI stop gate: only after the contract, evidence model, evaluator, tests, and
   Bradbury smoke proof are all green should a frontend be started.

## UI stop gate checklist

- [x] contract lint and semantic validation pass;
- [x] direct tests pass, including unauthorized callers and bad transitions;
- [x] evaluator validator independently checks evidence and stable decisions;
- [ ] integration/consensus test passes unanimously in a real GenLayer environment;
- [x] deterministic Bradbury deployment and smoke receipt are recorded in-repository;
- [ ] evaluator-enabled Bradbury deployment and smoke receipt are green;
- [ ] no unresolved security or provenance exception remains.
