# TenderCouncil v2 Recovery Manifest

- Captured: `2026-08-14T13:43:06.6617750+01:00`
- HEAD: `911e1f47d45b24a3db24735f014f785b4decbf68`
- origin/main: `911e1f47d45b24a3db24735f014f785b4decbf68`
- Index: no staged changes
- Scope: pre-review snapshot of the recovered remediation worktree; this file is an audit record, not a deployable artifact.

## Git status (`--porcelain=v2`)

```text
1 .M N... 100644 100644 100644 da4aacdc4de3222d98e8bd5cba39a5693c597972 da4aacdc4de3222d98e8bd5cba39a5693c597972 artifacts/bradbury-split-deployment-probe.json
1 .M N... 100644 100644 100644 dc6ebc6c2591f69612a44cdf2327276cf2c55e4f dc6ebc6c2591f69612a44cdf2327276cf2c55e4f artifacts/tender_council_core_deployable.py
1 .M N... 100644 100644 100644 112a7fc9cfd84be76f1ffd713f6aa73395d9ebe5 112a7fc9cfd84be76f1ffd713f6aa73395d9ebe5 artifacts/tender_council_evaluator_deployable.py
1 .M N... 100644 100644 100644 d85c3f157cd3550e5c60175c20cc3cd76adc9fb5 d85c3f157cd3550e5c60175c20cc3cd76adc9fb5 artifacts/tender_council_split-deployment-dry-run.json
1 .M N... 100644 100644 100644 568d46ca6c1297c7ca5364eab234bfc536a1c4df 568d46ca6c1297c7ca5364eab234bfc536a1c4df artifacts/tender_council_split-size-budget.json
1 .M N... 100644 100644 100644 02c53ec0d8c0f98ae3709325941c142d719113a3 02c53ec0d8c0f98ae3709325941c142d719113a3 contracts/tender_council_core.py
1 .M N... 100644 100644 100644 c5336fd7a7b9df9e1e8d0ceba25c03b0c8bf2c98 c5336fd7a7b9df9e1e8d0ceba25c03b0c8bf2c98 contracts/tender_council_evaluator.py
1 .M N... 100644 100644 100644 15c8f30c204cdb5ca3520398fac102099e2028f3 15c8f30c204cdb5ca3520398fac102099e2028f3 deploy/deploy_split.py
1 .M N... 100644 100644 100644 4a43c732f93b581c42c85c6fffc0d31fc9bec534 4a43c732f93b581c42c85c6fffc0d31fc9bec534 docs/BRADBURY_E2E.md
1 .M N... 100644 100644 100644 f803b9824eba9a7e4383b778422d668ca7e5e891 f803b9824eba9a7e4383b778422d668ca7e5e891 docs/DEPLOYMENT.md
1 .M N... 100644 100644 100644 744ca2903788d44d71e5ed45b5b46f9e01fe9c86 744ca2903788d44d71e5ed45b5b46f9e01fe9c86 docs/PROVENANCE.md
1 .M N... 100644 100644 100644 3b7a197b11bc1147765134bb3d052cba382a7e8a 3b7a197b11bc1147765134bb3d052cba382a7e8a docs/STAGES.md
1 .M N... 100644 100644 100644 3be67e9ab12ce9070a790497c1e7b8b5665ce084 3be67e9ab12ce9070a790497c1e7b8b5665ce084 gltest.config.yaml
1 .M N... 100644 100644 100644 c50e94b2ccd87357f3737e5724a38bf5b57d950b c50e94b2ccd87357f3737e5724a38bf5b57d950b pyproject.toml
1 .M N... 100644 100644 100644 801ae2f65666eefc2bfacaad354881c75ad913dd 801ae2f65666eefc2bfacaad354881c75ad913dd tests/direct/test_split_contracts.py
1 .M N... 100644 100644 100644 7719e7d4262bab5831789653a089f341dcc0094a 7719e7d4262bab5831789653a089f341dcc0094a tests/fixtures/evaluator_core_fixture.py
1 .M N... 100644 100644 100644 90ecbc027d4d1576bccd136982265ab59062a856 90ecbc027d4d1576bccd136982265ab59062a856 tests/fixtures/split_fake_evaluator.py
1 .M N... 100644 100644 100644 eace7349b4216b8707360c867bca7d7b9a9f3db3 eace7349b4216b8707360c867bca7d7b9a9f3db3 tests/split_runtime_probe.py
1 .M N... 100644 100644 100644 dcd1dec5cfb9812215f7ce9e1f9d0fd222b2bf14 dcd1dec5cfb9812215f7ce9e1f9d0fd222b2bf14 tools/bradbury_e2e.mjs
1 .M N... 100644 100644 100644 153b868fdff33b2bde9f92f05123e4d2fbfe0afe 153b868fdff33b2bde9f92f05123e4d2fbfe0afe tools/bradbury_split_deployment_probe.mjs
1 .M N... 100644 100644 100644 0b02d999bce3101d396d0dc3ca3667804cf358a8 0b02d999bce3101d396d0dc3ca3667804cf358a8 tools/challenge_integrity_trials.py
1 .M N... 100644 100644 100644 687934bc2ca681c041fd616ccf57ccfd8e752257 687934bc2ca681c041fd616ccf57ccfd8e752257 tools/evaluator_live_shape_trial.py
1 .M N... 100644 100644 100644 fa3a3812df6614274f02eebd7875a767c448f671 fa3a3812df6614274f02eebd7875a767c448f671 tools/evaluator_no_valid_trial.py
1 .M N... 100644 100644 100644 c0350ec61d7d66d53f397937494da5eaaf29ec41 c0350ec61d7d66d53f397937494da5eaaf29ec41 tools/financial_trials.py
1 .M N... 100644 100644 100644 63376e1ab64a4caeb44c66760fbddd559cfba7b5 63376e1ab64a4caeb44c66760fbddd559cfba7b5 tools/make_deployable.py
1 .M N... 100644 100644 100644 e2b0114b1e9a6b0a3579bf7bf69e75ca1c993773 e2b0114b1e9a6b0a3579bf7bf69e75ca1c993773 tools/release_preflight_split.py
1 .M N... 100644 100644 100644 8a9b2ee31e4ec7ae0b36cd46e02b6c89dd425442 8a9b2ee31e4ec7ae0b36cd46e02b6c89dd425442 tools/semantic_policy_trials.py
1 .M N... 100644 100644 100644 2e370b614c9837a3fca53b9002d5364bff27f9cf 2e370b614c9837a3fca53b9002d5364bff27f9cf tools/split_deployment_size_check.mjs
? artifacts/tender_council_bradbury_e2e_failure_2026-08-13T150054150Z.json
? artifacts/tender_council_reconstructed_diagnostic_provenance.json
? artifacts/tender_council_v2_multi_validator_proof.json
? fixtures/live/final-v2/
? tests/conftest.py
? tests/direct/test_calldata_stability.py
? tests/runner/
? tests/test_recovery_state_machine.py
? tools/bradbury_e2e_runner.mjs
? tools/bradbury_runner_lib.mjs
```

## Diff stat

```text
28 files changed, 1872 insertions(+), 1359 deletions(-)
```

## Complete modified-file list (28)

```text
artifacts/bradbury-split-deployment-probe.json
artifacts/tender_council_core_deployable.py
artifacts/tender_council_evaluator_deployable.py
artifacts/tender_council_split-deployment-dry-run.json
artifacts/tender_council_split-size-budget.json
contracts/tender_council_core.py
contracts/tender_council_evaluator.py
deploy/deploy_split.py
docs/BRADBURY_E2E.md
docs/DEPLOYMENT.md
docs/PROVENANCE.md
docs/STAGES.md
gltest.config.yaml
pyproject.toml
tests/direct/test_split_contracts.py
tests/fixtures/evaluator_core_fixture.py
tests/fixtures/split_fake_evaluator.py
tests/split_runtime_probe.py
tools/bradbury_e2e.mjs
tools/bradbury_split_deployment_probe.mjs
tools/challenge_integrity_trials.py
tools/evaluator_live_shape_trial.py
tools/evaluator_no_valid_trial.py
tools/financial_trials.py
tools/make_deployable.py
tools/release_preflight_split.py
tools/semantic_policy_trials.py
tools/split_deployment_size_check.mjs
```

## Complete untracked-file list (15)

```text
artifacts/tender_council_bradbury_e2e_failure_2026-08-13T150054150Z.json
artifacts/tender_council_reconstructed_diagnostic_provenance.json
artifacts/tender_council_v2_multi_validator_proof.json
fixtures/live/final-v2/challenge_a.json
fixtures/live/final-v2/manifests/bid_a.json
fixtures/live/final-v2/manifests/bid_b.json
fixtures/live/final-v2/manifests/bid_c.json
fixtures/live/final-v2/manifests/bid_d.json
fixtures/live/final-v2/manifests/bid_e.json
tests/conftest.py
tests/direct/test_calldata_stability.py
tests/runner/bradbury_runner.test.mjs
tests/test_recovery_state_machine.py
tools/bradbury_e2e_runner.mjs
tools/bradbury_runner_lib.mjs
```

## Intended generated-artifact SHA-256 values at capture

```text
a3f84f5e28d164f237740989e0bc2d6dd98a0f85b21b5a24de95886cd1e01c50  artifacts/bradbury-split-deployment-probe.json
4b42ecd5e0ceb5da9f24cb31634b6ce36678bbd4267a47e01f2fc773a0a381e7  artifacts/tender_council_bradbury_e2e_failure_2026-08-13T150054150Z.json
0bcb4562865545b261d40e0a5a2af95ec55f7d33cb37c3669eab3483704ad65e  artifacts/tender_council_core_deployable.py
73af758e744b6c4c05c9e224d22f64723638af2474e3756e328327893eec62b9  artifacts/tender_council_evaluator_deployable.py
cd0927446fd4699a8ecd683905d48b0c09318e4acadcd89974d3736ebeba418b  artifacts/tender_council_reconstructed_diagnostic_provenance.json
dce9b389ae14910b399394923ac574ea42530ce222601062bac69e91217cab79  artifacts/tender_council_split-deployment-dry-run.json
dd0fcc63dbc336bfd9d824007f47c4b324bd110a09f6fd742804130dc87f5044  artifacts/tender_council_split-size-budget.json
dc4a5809d5abfdc807932431aeea78739caa57a132aa5f8f4b92fe6c6f5f924f  artifacts/tender_council_v2_multi_validator_proof.json
```
