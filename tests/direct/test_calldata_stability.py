"""Pinned-runtime regressions for GenVM nondeterministic calldata boundaries."""

from pathlib import Path
import copy
import sys

import pytest


EVALUATOR = "contracts/tender_council_evaluator.py"
PINNED_DEPENDENCY = "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"
FETCH_URL = "https://fixture.example/calldata-stability.bin"


def _pinned_calldata(evaluator):
    # direct_deploy has resolved the contract's Depends header and placed that
    # exact SDK on sys.path. Importing here deliberately tests that runtime's
    # codec rather than the host genlayer-py package.
    from genlayer.py import calldata

    source = Path(EVALUATOR).read_text(encoding="utf-8")
    assert PINNED_DEPENDENCY in source.splitlines()[0]
    assert "gltest-direct" in str(Path(calldata.__file__).resolve())
    assert evaluator.get_evaluator_version() == "tendercouncil.evaluator.v2"
    return calldata


def test_historical_tuple_roundtrip_decodes_as_list(direct_deploy):
    evaluator = direct_deploy(
        EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2"
    )
    calldata = _pinned_calldata(evaluator)

    produced = ("OK", b"abc")
    decoded = calldata.decode(calldata.encode(produced))

    assert produced == ("OK", b"abc")
    assert decoded == ["OK", b"abc"]
    assert type(decoded) is list
    assert produced != decoded


def test_real_fetch_equivalence_survives_pinned_calldata_roundtrip(
    direct_vm, direct_deploy
):
    direct_vm.mock_web(FETCH_URL, {"status": 200, "body": b"abc"})
    evaluator = direct_deploy(
        EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2"
    )
    calldata = _pinned_calldata(evaluator)
    module = sys.modules[evaluator._instance.__class__.__module__]

    leader_value = module._fetch(FETCH_URL, 32)
    decoded = calldata.decode(calldata.encode(leader_value))

    # This is the production-shaped validator input. Direct Mode's ordinary
    # run_validator() bypasses this encode/decode and therefore missed the bug.
    assert direct_vm.run_validator(leader_result=decoded)


def _evaluation_result():
    return {
        "status": "COMPARATIVE",
        "deterministic_disqualified_bid_ids": ["t-bid-d"],
        "integrity_disqualified_bid_ids": ["t-bid-e"],
        "semantic_candidate_ids": ["t-bid-a", "t-bid-b", "t-bid-c"],
        "semantic_disqualified_bid_ids": ["t-bid-c"],
        "semantic_classifications": [
            {"bid_id": "t-bid-a", "mandatory_requirements_pass": True},
            {"bid_id": "t-bid-b", "mandatory_requirements_pass": True},
            {"bid_id": "t-bid-c", "mandatory_requirements_pass": False},
        ],
        "valid_bid_ids": ["t-bid-a", "t-bid-b"],
        "disqualified_bid_ids": ["t-bid-c", "t-bid-d", "t-bid-e"],
        "winner_bid_id": "t-bid-b",
        "winner_total_score": 94,
        "runner_up_bid_id": "t-bid-a",
        "runner_up_score": 77,
        "scores": [
            {
                "bid_id": "t-bid-a", "technical": 30, "delivery": 17,
                "price": 14, "capability": 8, "support": 8, "total": 77,
            },
            {
                "bid_id": "t-bid-b", "technical": 34, "delivery": 19,
                "price": 16, "capability": 15, "support": 10, "total": 94,
            },
        ],
        "confidence": "HIGH",
        "rationale": "Bounded authenticated comparison.",
    }


def test_pinned_calldata_roundtrip_matrix(direct_deploy):
    evaluator = direct_deploy(
        EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2"
    )
    calldata = _pinned_calldata(evaluator)
    evaluation = _evaluation_result()
    review = {
        "decision": "UPHOLD", "winner_bid_id": "t-bid-b",
        "rationale": "Original result stands.",
        "challenge_states": ["t-challenge-a:VALID"],
    }
    matrix = {
        "int": 7,
        "bool": True,
        "str": "TenderCouncil UTF-8 \u2713",
        "bytes": b"\x00abc\xff",
        "none": None,
        "flat_list": [1, "two", False, b"three", None],
        "nested_list": [["a", "b"], [1, 2], []],
        "dict": {"state": "OK", "body": b"abc"},
        "nested_dict_list": {
            "bids": [{"bid_id": "t-bid-a", "categories": ["VALID"]}],
            "optional": None,
        },
        "evaluation_result": evaluation,
        "evaluation_envelope": {"state": "VALID", "result": evaluation},
        "review_result": review,
        "review_envelope": {"state": "VALID", "result": review},
        "evidence_fetch_result": {"state": "OK", "body": b"abc"},
        "scoring_payload": evaluation["scores"],
        "evaluation_callback_payload": {
            "tender_id": "t", "nonce": 2,
            "snapshot_digest": "sha256:" + "a" * 64,
            "result_type": "COMPARATIVE", "winner_bid_id": "t-bid-b",
            "result_digest": "sha256:" + "b" * 64,
        },
        "review_callback_payload": {
            "tender_id": "t", "evaluation_nonce": 2, "review_nonce": 1,
            "decision": "UPHOLD", "winner_bid_id": "t-bid-b",
            "result_digest": "sha256:" + "c" * 64,
        },
        "category_arrays": [
            evaluation["deterministic_disqualified_bid_ids"],
            evaluation["integrity_disqualified_bid_ids"],
            evaluation["semantic_disqualified_bid_ids"],
            evaluation["valid_bid_ids"],
        ],
        "score_arrays": [77, 94],
        "winner_runner_up": {
            "winner_bid_id": "t-bid-b", "runner_up_bid_id": "t-bid-a",
        },
    }
    for name, produced in matrix.items():
        decoded = calldata.decode(calldata.encode(produced))
        assert decoded == produced, name
        assert type(decoded) is type(produced), name


def _parser_module(evaluator):
    return sys.modules[evaluator._instance.__class__.__module__]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.pop("status"),
        lambda value: value.update({"extra": "field"}),
        lambda value: value.update({"status": "INVENTED"}),
        lambda value: value.update({"winner_total_score": "94"}),
        lambda value: value.update({"scores": None}),
        lambda value: value.update({"scores": {}}),
        lambda value: value.update({"semantic_classifications": []}),
        lambda value: value.update({"valid_bid_ids": None}),
        lambda value: value.update({"confidence": None}),
        lambda value: value.update({"runner_up_score": True}),
    ],
)
def test_evaluation_model_parser_is_nonthrowing_and_rejects_malformed_shapes(
    direct_deploy, mutation
):
    evaluator = direct_deploy(
        EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2"
    )
    module = _parser_module(evaluator)
    value = copy.deepcopy(_evaluation_result())
    mutation(value)
    assert module._try_normalize_evaluation_model(
        value,
        ["t-bid-a", "t-bid-b", "t-bid-c", "t-bid-d", "t-bid-e"],
        ["t-bid-d"], ["t-bid-e"],
        ["t-bid-a", "t-bid-b", "t-bid-c"],
        [35, 20, 20, 15, 10],
    ) is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        "UPHOLD",
        {},
        {"decision": "INVENTED", "winner_bid_id": "t-bid-b", "rationale": "x"},
        {"decision": "UPHOLD", "winner_bid_id": "wrong", "rationale": "x"},
        {"decision": "REPLACE_WINNER", "winner_bid_id": "wrong", "rationale": "x"},
        {"decision": "UPHOLD", "winner_bid_id": "t-bid-b", "rationale": 7},
        {
            "decision": "UPHOLD", "winner_bid_id": "t-bid-b",
            "rationale": "x", "extra": True,
        },
    ],
)
def test_review_model_parser_is_nonthrowing_and_rejects_malformed_shapes(
    direct_deploy, value
):
    evaluator = direct_deploy(
        EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2"
    )
    module = _parser_module(evaluator)
    assert module._try_normalize_review_model(
        copy.deepcopy(value), "t-bid-b", ["t-bid-a", "t-bid-b"],
        ["t-challenge-a:VALID"],
    ) is None


def test_malformed_and_unavailable_model_envelopes_never_throw(
    direct_deploy, monkeypatch
):
    evaluator = direct_deploy(
        EVALUATOR, "0x" + "12" * 20, "tendercouncil.evaluator.v2"
    )
    module = _parser_module(evaluator)

    monkeypatch.setattr(module.gl.nondet, "exec_prompt", lambda *args, **kwargs: [])
    assert module._evaluation_model_envelope(
        "prompt", ["t-bid-a"], [], [], ["t-bid-a"], [35, 20, 20, 15, 10]
    ) == {"state": "MODEL_CANDIDATE_INVALID", "result": {}}
    assert module._review_model_envelope(
        "prompt", "t-bid-a", ["t-bid-a"], ["challenge:VALID"]
    ) == {"state": "MODEL_CANDIDATE_INVALID", "result": {}}

    def unavailable(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(module.gl.nondet, "exec_prompt", unavailable)
    assert module._evaluation_model_envelope(
        "prompt", ["t-bid-a"], [], [], ["t-bid-a"], [35, 20, 20, 15, 10]
    ) == {"state": "MODEL_PROVIDER_UNAVAILABLE", "result": {}}
    assert module._review_model_envelope(
        "prompt", "t-bid-a", ["t-bid-a"], ["challenge:VALID"]
    ) == {"state": "MODEL_PROVIDER_UNAVAILABLE", "result": {}}
