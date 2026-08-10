# TenderCouncil delivery stages

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
