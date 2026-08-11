from pathlib import Path

from tools.challenge_integrity_trials import run as run_challenge_trials
from tools.equivalence_trials import run as run_equivalence_trials
from tools.review_lookup_trials import run as run_review_trials
from tools.semantic_policy_trials import run as run_semantic_trials
from tools.evaluator_no_valid_trial import run as run_no_valid_trial
from tools.financial_trials import run as run_financial_trials


ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = ROOT / "contracts" / "tender_council_evaluator.py"
CORE_FIXTURE = ROOT / "tests" / "fixtures" / "evaluator_core_fixture.py"
CORE = ROOT / "contracts" / "tender_council_core.py"
FAKE = ROOT / "tests" / "fixtures" / "split_fake_evaluator.py"


def test_equivalence_stability_matrix():
    observations = run_equivalence_trials(EVALUATOR)
    assert observations["rationale_only_change"] is True
    assert observations["score_delta_2"] is True
    assert observations["score_delta_3"] is False
    assert observations["winner_change"] is False
    assert observations["mandatory_classification_disagreement"] is False


def test_semantic_candidate_partition_and_canonical_fixture():
    run_semantic_trials(EVALUATOR)


def test_external_challenge_integrity_states():
    run_challenge_trials(EVALUATOR)


def test_review_uses_evaluator_owned_result_record():
    run_review_trials(EVALUATOR)


def test_real_evaluator_all_semantic_fail_path():
    run_no_valid_trial(EVALUATOR, CORE_FIXTURE)


def test_financial_wei_and_global_outflow_lock():
    run_financial_trials(CORE, FAKE)
