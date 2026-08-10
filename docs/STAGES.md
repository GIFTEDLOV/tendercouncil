# TenderCouncil delivery stages

## Current inventory (2026-08-10)

| Area | Status | Evidence |
|---|---|---|
| Repository isolation and provenance | DONE | Dedicated `GIFTEDLOV/tendercouncil`, one `origin`, preserved Bradbury artifacts |
| Stage 1 deterministic record | DONE for prototype | `contracts/tender_council.py` |
| Public buyer / multiple independent tenders | DONE for foundation | `contracts/tender_council_production.py` allows any buyer and multiple tender records |
| Funded escrow and finalized-safe settlement | PARTIAL | Exact payable custody, finalized-only EOA transfer request, pending state, replay protection, and balance-delta confirmation exist; live child-finality proof remains |
| Authenticated bounded bid manifest | PARTIAL | Production bid stores sender-bound commercial terms and commitments; `tendercouncil.bid.v1` schema validation is enforced, while semantic evidence retrieval remains |
| Exact-byte SHA-256 verification | PARTIAL | Stage 1 evaluator and production manifest validator hash exact fetched bytes; evidence-object retrieval remains |
| Required/optional evidence policy | PARTIAL | Production evaluator records required failures and explicitly skips optional unavailable evidence; broader policy fixtures remain |
| Comparative multi-bid evaluator | PARTIAL | `evaluate_tender` ranks one tender snapshot with bounded structured output; Bradbury proof and tolerance trials remain |
| Provisional award / response window / bounded challenge | PARTIAL | Production contract has explicit provisional/window/review states, committed-evidence challenge restrictions, and 37 local tests; finalized settlement proof is still separate |
| Runtime boundary regression | PARTIAL/BLOCKED | Primitive-byte boundary passes locally; preserved old evaluator smoke has validator `DETERMINISTIC_VIOLATION`, and current production deployment is blocked before creation by Bradbury pubdata size |
| Threat model and runtime due diligence | DONE | `docs/THREAT_MODEL.md`, `docs/RUNTIME_DUE_DILIGENCE.md` |
| CI, release preflight, deployment script | PARTIAL | Pinned CI plus seven mutation checks are green; fail-closed preflight and list-based deployment wrapper exist, but production artifact proof remains |
| Direct test suite | DONE locally | 37 passed locally; Phase 7 CI run `31397768174` green, including seven mutation checks |
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

1. Add finalized-safe settlement and broaden mutation/security coverage around
   the comparative and challenge paths.
2. Use the release preflight/deployment wrapper for evaluator-enabled Bradbury
   proof, then verify protocol finality and the full funded settlement path.
3. Only after those gates are green may the UI stop gate be reviewed.

## UI stop gate checklist

- [x] contract lint and semantic validation pass;
- [x] direct tests pass, including unauthorized callers and bad transitions;
- [x] evaluator validator independently checks evidence and stable decisions;
- [ ] integration/consensus test passes unanimously in a real GenLayer environment;
- [x] deterministic Bradbury deployment and smoke receipt are recorded in-repository;
- [ ] evaluator-enabled Bradbury deployment and smoke receipt are green;
- [ ] no unresolved security or provenance exception remains.
