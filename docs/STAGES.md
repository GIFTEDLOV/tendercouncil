# TenderCouncil delivery stages

## Stage 0 — repository and operating baseline

Status: complete at `bf6b542`.

- Dedicated public repository: `GIFTEDLOV/tendercouncil`
- Independent `main` branch with a single intended `origin`
- GenLayer Bradbury is the target network
- Frontend work is held behind the UI stop gate

## Stage 1 — deterministic procurement foundation

Status: implementation in this change.

The Stage 1 contract is intentionally narrow and auditable. It provides:

- owner-authenticated tender creation;
- issuer-only lifecycle transitions;
- supplier-authenticated bid submission;
- evidence records that bind an HTTPS URI and content hash to a bid;
- explicit close, award, reject, and cancel transitions;
- read methods and stable identifier lists for a future client;
- direct-mode tests for authorization and invalid transitions.

Stage 1 does not claim that a submitted URL is truthful. It records the
provenance anchor so a later evaluator can independently retrieve and assess
evidence without treating leader output as trusted input.

## Next gated stages

1. Evidence evaluator: implement a leader/validator pair with explicit stable
   decision fields and adversarial prompt-injection tests.
2. Consensus and smoke proof: validate the evaluator in direct mode, then
   against Studio/GLSim as appropriate, and finally execute a Bradbury smoke
   flow with a recorded receipt.
3. UI stop gate: only after the contract, evidence model, evaluator, tests, and
   Bradbury smoke proof are all green should a frontend be started.

## UI stop gate checklist

- [ ] contract lint and semantic validation pass;
- [ ] direct tests pass, including unauthorized callers and bad transitions;
- [ ] evaluator validator independently checks evidence and stable decisions;
- [ ] integration/consensus test passes in a real GenLayer environment;
- [ ] Bradbury deployment and smoke receipt are recorded in-repository;
- [ ] no unresolved security or provenance exception remains.
