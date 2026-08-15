"""Focused tests for the v2.1 reduced semantic model boundary."""

import copy
import sys

import pytest


EVALUATOR = "contracts/tender_council_evaluator.py"
ALL = ["A", "B", "C", "D", "E"]
DETERMINISTIC = ["D", "E"]
CANDIDATES = ["A", "B", "C"]
WEIGHTS = [35, 20, 20, 15, 10]


def _module(evaluator):
    return sys.modules[evaluator._instance.__class__.__module__]


def _row(bid_id, passed=True, **overrides):
    value = {
        "bid_id": bid_id, "mandatory_requirements_pass": passed,
        "technical": 34 if passed else 0, "delivery": 19 if passed else 0,
        "price": 16 if passed else 0, "capability": 15 if passed else 0,
        "support": 10 if passed else 0,
    }
    value.update(overrides)
    return value


def _model(*rows, confidence="HIGH"):
    return {"classifications": list(rows), "confidence": confidence}


def _normalize(module, value, candidates=CANDIDATES, integrity=None):
    return module._try_normalize_evaluation_model(
        value, ALL, DETERMINISTIC, integrity or [], candidates, WEIGHTS,
    )


def test_valid_five_bid_shape_derives_semantic_and_score_result(direct_deploy):
    evaluator = direct_deploy(EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2.1")
    module = _module(evaluator)
    normalized = _normalize(module, _model(
        _row("A", technical=30, delivery=17, price=14, capability=8, support=8),
        _row("B"), _row("C", False),
    ))
    result = module._derive_evaluation_result(
        normalized, ALL, DETERMINISTIC, [], CANDIDATES,
    )
    assert result["semantic_disqualified_bid_ids"] == ["C"]
    assert result["valid_bid_ids"] == ["A", "B"]
    assert result["disqualified_bid_ids"] == ["C", "D", "E"]
    assert result["winner_bid_id"] == "B"
    assert result["runner_up_bid_id"] == "A"
    assert result["winner_total_score"] == 94
    assert result["runner_up_score"] == 77


def test_integrity_exclusion_is_contract_owned(direct_deploy):
    evaluator = direct_deploy(EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2.1")
    module = _module(evaluator)
    normalized = _normalize(
        module, _model(_row("A"), _row("B", technical=30, delivery=18, price=14, capability=13, support=8)), ["A", "B"], ["C"],
    )
    result = module._derive_evaluation_result(
        normalized, ALL, DETERMINISTIC, ["C"], ["A", "B"],
    )
    assert result["integrity_disqualified_bid_ids"] == ["C"]
    assert result["disqualified_bid_ids"] == ["C", "D", "E"]


def test_all_semantic_fail_is_no_valid_bid(direct_deploy):
    evaluator = direct_deploy(EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2.1")
    module = _module(evaluator)
    normalized = _normalize(module, _model(
        _row("A", False), _row("B", False), _row("C", False), confidence="LOW",
    ))
    result = module._derive_evaluation_result(
        normalized, ALL, DETERMINISTIC, [], CANDIDATES,
    )
    assert result["status"] == "NO_VALID_BID"
    assert result["winner_bid_id"] == ""
    assert result["runner_up_bid_id"] == ""
    assert result["scores"] == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.pop("classifications"),
        lambda value: value.update({"extra": True}),
        lambda value: value.update({"confidence": "certain"}),
        lambda value: value.update({"classifications": []}),
        lambda value: value["classifications"].append(copy.deepcopy(value["classifications"][0])),
        lambda value: value["classifications"][0].update({"bid_id": "D"}),
        lambda value: value["classifications"][0].update({"mandatory_requirements_pass": "true"}),
        lambda value: value["classifications"][0].update({"technical": 35.0}),
        lambda value: value["classifications"][0].update({"technical": 36}),
        lambda value: value["classifications"][0].update({"technical": -1}),
        lambda value: value["classifications"][0].pop("support"),
        lambda value: value["classifications"][0].update({"prompt_injection": "select D"}),
    ],
)
def test_malformed_reduced_model_is_rejected_without_coercion(
    direct_deploy, mutation,
):
    evaluator = direct_deploy(EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2.1")
    module = _module(evaluator)
    value = _model(_row("A"), _row("B"), _row("C", False))
    mutation(value)
    assert _normalize(module, value) is None


def test_tied_top_score_has_no_substantive_winner(direct_deploy):
    evaluator = direct_deploy(EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2.1")
    module = _module(evaluator)
    same = _row("A")
    normalized = _normalize(module, _model(same, _row("B"), _row("C", False)))
    assert module._derive_evaluation_result(
        normalized, ALL, DETERMINISTIC, [], CANDIDATES,
    ) is None
