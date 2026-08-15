"""Production-shaped glsim tests for bounded evaluator recovery and escrow exit."""

from datetime import datetime, timezone
import hashlib
import json
import os

import pytest
from glsim.engine import SimEngine
from glsim.state import StateStore


CORE = "contracts/tender_council_core.py"
FAKE = "tests/fixtures/split_fake_evaluator.py"
BUYER = "0x" + "11" * 20
BIDDER = "0x" + "22" * 20
EXECUTOR = "0x" + "33" * 20
HASH = "sha256:" + "a" * 64
BUDGET = 8_000_000_000_000_000_000
BID_PRICE = 6_200_000_000_000_000_000
DEADLINE = 1_798_761_600


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _warp_after(engine, timestamp: int):
    engine.vm.warp(
        datetime.fromtimestamp(timestamp + 1, timezone.utc).isoformat()
    )


def _new(request):
    original_stdin_fd = os.dup(0)
    engine = SimEngine(StateStore(chain_id=4221, seed="recovery-state-machine"))
    engine.activate()
    def cleanup():
        engine.deactivate()
        os.dup2(original_stdin_fd, 0)
        os.close(original_stdin_fd)
    request.addfinalizer(cleanup)
    engine.vm.warp("2026-01-01T00:00:00+00:00")
    core_address, core = engine.deploy(CORE, sender=BUYER)
    fake_address, _ = engine.deploy(FAKE, args=[core_address], sender=BUYER)
    engine.call_method(
        core_address, "bind_evaluator",
        [type(core.bootstrapper)(fake_address), "tendercouncil.evaluator.v2.1", HASH],
        sender=BUYER,
    )
    return engine, core_address, fake_address


def _create_closed(
    engine, core_address, tender_id="recovery", with_bid=False, price=BID_PRICE,
):
    engine.vm.value = BUDGET
    engine.call_method(
        core_address, "create_tender",
        [
            tender_id, "Recovery state-machine tender",
            "https://buyer.example/brief", HASH, BUDGET, 30, 90,
            DEADLINE, 7200,
            "authentication;CSV export;responsive/mobile;dashboard/chart",
            35, 20, 20, 15, 10,
            "capability:required;secondary:optional",
        ],
        sender=BUYER,
    )
    engine.vm.value = 0
    engine.vm._balances[bytes.fromhex(core_address[2:])] = BUDGET
    engine.call_method(core_address, "open_tender", [tender_id], sender=BUYER)
    if with_bid:
        engine.call_method(
            core_address, "submit_bid",
            [
                tender_id + "-bid-a", tender_id, price,
                26, 120, "https://bidder.example/proposal", HASH, "",
                "tendercouncil.bid.v1",
            ],
            sender=BIDDER,
        )
    engine.vm.warp("2027-02-01T00:00:00+00:00")
    engine.call_method(core_address, "close_tender", [tender_id], sender=BUYER)


def _start(engine, core_address, tender_id="recovery"):
    engine.call_method(core_address, "start_evaluation", [tender_id], sender=BUYER)
    return engine.call_method(core_address, "get_tender", [tender_id])


def _comparative_result(tender_id: str):
    bid_id = tender_id + "-bid-a"
    return json.dumps(
        {
            "status": "COMPARATIVE", "winner_bid_id": bid_id,
            "valid_bid_ids": [bid_id], "disqualified_bid_ids": [],
            "deterministic_disqualified_bid_ids": [],
            "integrity_disqualified_bid_ids": [],
            "semantic_candidate_ids": [bid_id],
            "semantic_disqualified_bid_ids": [],
            "semantic_classifications": [
                {"bid_id": bid_id, "mandatory_requirements_pass": True}
            ],
            "scores": [{
                "bid_id": bid_id, "technical": 35, "delivery": 20,
                "price": 20, "capability": 15, "support": 10,
                "total": 100,
            }],
            "winner_total_score": 100, "runner_up_bid_id": "",
            "runner_up_score": 0, "confidence": "HIGH",
            "rationale": "Authenticated production-shaped test result.",
        },
        sort_keys=True, separators=(",", ":"),
    )


def test_evaluation_timeout_retry_preserves_snapshot_and_rejects_stale_callback(request):
    engine, core, fake = _new(request)
    _create_closed(engine, core)
    tender = _start(engine, core)
    snapshot_text = engine.call_method(core, "get_closed_snapshot", ["recovery"])
    snapshot_value = json.loads(snapshot_text)
    first_timeout = int(tender.evaluation_timeout_at)

    # Observable time is the only authority for an unresolved child. No caller
    # can accelerate the timeout.
    with pytest.raises(Exception):
        engine.call_method(
            core, "expire_evaluation_attempt", ["recovery"], sender=EXECUTOR
        )
    assert engine.call_method(core, "get_tender", ["recovery"]).status == "EVALUATING"
    _warp_after(engine, first_timeout)
    engine.call_method(core, "expire_evaluation_attempt", ["recovery"], sender=EXECUTOR)
    assert engine.call_method(core, "get_tender", ["recovery"]).status == "EVALUATION_RETRYABLE"

    engine.call_method(core, "retry_evaluation", ["recovery"], sender=EXECUTOR)
    second = engine.call_method(core, "get_tender", ["recovery"])
    assert second.closed_snapshot_digest == tender.closed_snapshot_digest
    assert int(second.evaluation_timeout_at) > first_timeout
    retried_snapshot_text = engine.call_method(
        core, "get_closed_snapshot", ["recovery"]
    )
    retried_snapshot = json.loads(retried_snapshot_text)
    assert retried_snapshot_text == snapshot_text
    assert retried_snapshot["bids"] == snapshot_value["bids"]
    assert retried_snapshot["rubric"] == snapshot_value["rubric"]
    assert retried_snapshot["evidence_policy"] == snapshot_value["evidence_policy"]

    # The old child may finish later, but nonce 1 can no longer advance nonce 2.
    fake_instance = engine._instances[fake.lower()]
    stale_digest = _digest(fake_instance.evaluation_result)
    engine.call_method(
        fake, "emit_evaluation",
        ["recovery", 1, tender.closed_snapshot_digest, stale_digest], sender=BUYER,
    )
    current = engine.call_method(core, "get_tender", ["recovery"])
    assert current.status == "EVALUATING"
    assert int(current.evaluation_nonce) == 2


def test_three_authenticated_model_failures_unlock_exact_full_refund(request):
    engine, core, fake = _new(request)
    _create_closed(engine, core)
    tender = _start(engine, core)
    snapshot = tender.closed_snapshot_digest

    for nonce in (1, 2, 3):
        engine.call_method(
            fake, "emit_evaluation_failure",
            ["recovery", nonce, snapshot, "MODEL_CANDIDATE_INVALID"],
            sender=BUYER,
        )
        tender = engine.call_method(core, "get_tender", ["recovery"])
        if nonce < 3:
            assert tender.status == "EVALUATION_RETRYABLE"
            engine.call_method(core, "retry_evaluation", ["recovery"], sender=EXECUTOR)
        else:
            assert tender.status == "EVALUATION_FAILED"

    # The executor cannot redirect funds; the locked buyer remains recipient.
    engine.call_method(core, "refund_failed_evaluation", ["recovery"], sender=EXECUTOR)
    accounting = json.loads(
        engine.call_method(core, "get_settlement_accounting", ["recovery"])
    )
    assert accounting["winner_payout_amount"] == 0
    assert accounting["buyer_refund_amount"] == BUDGET
    assert accounting["financial_outflow_kind"] == "EVALUATION_FAILED_REFUND"

    # Confirmation remains finalized-balance-delta gated.
    with pytest.raises(Exception):
        engine.call_method(core, "confirm_refund", ["recovery"], sender=EXECUTOR)
    assert engine.call_method(core, "get_tender", ["recovery"]).status == "REFUND_PENDING"
    before = accounting["financial_outflow_balance_before"]
    engine.vm._balances[bytes.fromhex(core[2:])] = before - BUDGET
    engine.call_method(core, "confirm_refund", ["recovery"], sender=EXECUTOR)
    final = engine.call_method(core, "get_tender", ["recovery"])
    assert final.status == "EVALUATION_FAILED"
    assert final.settlement_state == "SETTLED"


def test_three_missing_callbacks_timeout_to_exact_full_refund(request):
    engine, core, _ = _new(request)
    _create_closed(engine, core, "absent")
    tender = _start(engine, core, "absent")

    for nonce in (1, 2, 3):
        _warp_after(engine, int(tender.evaluation_timeout_at))
        engine.call_method(
            core, "expire_evaluation_attempt", ["absent"], sender=EXECUTOR
        )
        tender = engine.call_method(core, "get_tender", ["absent"])
        if nonce < 3:
            assert tender.status == "EVALUATION_RETRYABLE"
            engine.call_method(
                core, "retry_evaluation", ["absent"], sender=EXECUTOR
            )
            tender = engine.call_method(core, "get_tender", ["absent"])
        else:
            assert tender.status == "EVALUATION_FAILED"

    engine.call_method(
        core, "refund_failed_evaluation", ["absent"], sender=EXECUTOR
    )
    accounting = json.loads(
        engine.call_method(core, "get_settlement_accounting", ["absent"])
    )
    assert accounting["winner_payout_amount"] == 0
    assert accounting["buyer_refund_amount"] == BUDGET
    assert accounting["financial_outflow_amount"] == BUDGET


def test_no_valid_bid_refund_is_exact_and_finalized_delta_gated(request):
    engine, core, fake = _new(request)
    _create_closed(engine, core, "no-valid")
    tender = _start(engine, core, "no-valid")
    payload = engine._instances[fake.lower()].evaluation_result
    engine.call_method(
        fake, "emit_evaluation",
        ["no-valid", 1, tender.closed_snapshot_digest, _digest(payload)],
        sender=BUYER,
    )
    assert engine.call_method(core, "get_tender", ["no-valid"]).status == "NO_VALID_BID"
    engine.call_method(core, "refund_no_valid_bid", ["no-valid"], sender=BUYER)
    accounting = json.loads(engine.call_method(
        core, "get_settlement_accounting", ["no-valid"]
    ))
    assert accounting["winner_payout_amount"] == 0
    assert accounting["buyer_refund_amount"] == BUDGET
    assert accounting["financial_outflow_amount"] == BUDGET
    with pytest.raises(Exception):
        engine.call_method(core, "confirm_refund", ["no-valid"], sender=EXECUTOR)
    engine.vm._balances[bytes.fromhex(core[2:])] = (
        accounting["financial_outflow_balance_before"] - BUDGET
    )
    engine.call_method(core, "confirm_refund", ["no-valid"], sender=EXECUTOR)
    final = engine.call_method(core, "get_tender", ["no-valid"])
    assert final.status == "NO_VALID_BID"
    assert final.settlement_state == "SETTLED"
    with pytest.raises(Exception):
        engine.call_method(core, "confirm_refund", ["no-valid"], sender=EXECUTOR)


def test_successful_current_callback_disables_timeout_and_duplicate_paths(request):
    engine, core, fake = _new(request)
    _create_closed(engine, core, "success", with_bid=True)
    tender = _start(engine, core, "success")
    payload = _comparative_result("success")
    engine._instances[fake.lower()].evaluation_result = payload
    engine.call_method(
        fake, "emit_evaluation",
        ["success", 1, tender.closed_snapshot_digest, _digest(payload)],
        sender=BUYER,
    )
    awarded = engine.call_method(core, "get_tender", ["success"])
    assert awarded.status == "PROVISIONAL_AWARD"
    _warp_after(engine, int(awarded.evaluation_timeout_at))
    with pytest.raises(Exception):
        engine.call_method(
            core, "expire_evaluation_attempt", ["success"], sender=EXECUTOR
        )
    engine.call_method(
        fake, "emit_evaluation",
        ["success", 1, tender.closed_snapshot_digest, _digest(payload)],
        sender=BUYER,
    )
    unchanged = engine.call_method(core, "get_tender", ["success"])
    assert unchanged.status == "PROVISIONAL_AWARD"
    assert unchanged.evaluation_result_digest == _digest(payload)


def test_review_retry_rejects_stale_callback_then_upholds_valid_winner(request):
    engine, core, fake = _new(request)
    _create_closed(engine, core, "review", with_bid=True)
    tender = _start(engine, core, "review")
    payload = _comparative_result("review")
    engine._instances[fake.lower()].evaluation_result = payload
    engine.call_method(
        fake, "emit_evaluation",
        ["review", 1, tender.closed_snapshot_digest, _digest(payload)],
        sender=BUYER,
    )
    engine.call_method(core, "start_response_window", ["review"], sender=BUYER)
    engine.call_method(
        core, "submit_challenge",
        [
            "review-challenge-a", "review", "MANDATORY_REQUIREMENT_MISAPPLIED",
            "review-bid-a", "", "", "",
        ],
        sender=BIDDER,
    )
    response = engine.call_method(core, "get_tender", ["review"])
    _warp_after(engine, int(response.response_window_end))
    engine.call_method(core, "advance_after_response", ["review"], sender=BUYER)
    review = engine.call_method(core, "get_tender", ["review"])

    for nonce in (1, 2, 3):
        engine.call_method(
            fake, "emit_review_failure",
            [
                "review", 1, nonce, review.closed_snapshot_digest,
                review.evaluation_result_digest, review.challenge_set_digest,
                "MODEL_PROVIDER_UNAVAILABLE",
            ],
            sender=BUYER,
        )
        review = engine.call_method(core, "get_tender", ["review"])
        if nonce < 3:
            assert review.status == "REVIEW_RETRYABLE"
            engine.call_method(core, "retry_review", ["review"], sender=EXECUTOR)
            review = engine.call_method(core, "get_tender", ["review"])
            if nonce == 1:
                stale_payload = json.dumps(
                    {
                        "decision": "UPHOLD",
                        "winner_bid_id": "review-bid-a",
                        "rationale": "stale review",
                    },
                    sort_keys=True, separators=(",", ":"),
                )
                engine._instances[fake.lower()].review_result = stale_payload
                with pytest.raises(Exception):
                    engine.call_method(
                        core, "receive_review_result",
                        [
                            "review", 1, 1, review.closed_snapshot_digest,
                            review.evaluation_result_digest,
                            review.challenge_set_digest, "UPHOLD",
                            "review-bid-a", _digest(stale_payload),
                        ],
                        sender=fake,
                    )
                unchanged = engine.call_method(core, "get_tender", ["review"])
                assert unchanged.status == "REVIEWING_CHALLENGES"
                assert int(unchanged.review_nonce) == 2
        else:
            assert review.status == "AWARDED"
            assert review.final_winner == "review-bid-a"

    # Review failure cannot convert a valid evaluation into a buyer-only exit.
    engine.call_method(core, "settle_award", ["review"], sender=EXECUTOR)
    accounting = json.loads(engine.call_method(
        core, "get_settlement_accounting", ["review"]
    ))
    assert accounting["winner_payout_amount"] == 6_200_000_000_000_000_000
    assert accounting["buyer_refund_amount"] == BUDGET - 6_200_000_000_000_000_000


def test_review_timeout_is_permissionless_and_late_callback_is_stale(request):
    engine, core, fake = _new(request)
    _create_closed(engine, core, "review-timeout", with_bid=True)
    tender = _start(engine, core, "review-timeout")
    payload = _comparative_result("review-timeout")
    engine._instances[fake.lower()].evaluation_result = payload
    engine.call_method(
        fake, "emit_evaluation",
        ["review-timeout", 1, tender.closed_snapshot_digest, _digest(payload)],
        sender=BUYER,
    )
    engine.call_method(
        core, "start_response_window", ["review-timeout"], sender=EXECUTOR
    )
    engine.call_method(
        core, "submit_challenge",
        [
            "review-timeout-challenge", "review-timeout",
            "MANDATORY_REQUIREMENT_MISAPPLIED", "review-timeout-bid-a",
            "", "", "",
        ],
        sender=BIDDER,
    )
    response = engine.call_method(core, "get_tender", ["review-timeout"])
    _warp_after(engine, int(response.response_window_end))
    engine.call_method(
        core, "advance_after_response", ["review-timeout"], sender=EXECUTOR
    )
    first = engine.call_method(core, "get_tender", ["review-timeout"])
    _warp_after(engine, int(first.review_timeout_at))
    engine.call_method(
        core, "expire_review_attempt", ["review-timeout"], sender=EXECUTOR
    )
    engine.call_method(core, "retry_review", ["review-timeout"], sender=EXECUTOR)
    current = engine.call_method(core, "get_tender", ["review-timeout"])
    stale_payload = json.dumps(
        {
            "decision": "UPHOLD",
            "winner_bid_id": "review-timeout-bid-a",
            "rationale": "late callback",
        },
        sort_keys=True, separators=(",", ":"),
    )
    engine._instances[fake.lower()].review_result = stale_payload
    with pytest.raises(Exception):
        engine.call_method(
            core, "receive_review_result",
            [
                "review-timeout", 1, 1, current.closed_snapshot_digest,
                current.evaluation_result_digest, current.challenge_set_digest,
                "UPHOLD", "review-timeout-bid-a", _digest(stale_payload),
            ],
            sender=fake,
        )
    unchanged = engine.call_method(core, "get_tender", ["review-timeout"])
    assert unchanged.status == "REVIEWING_CHALLENGES"
    assert int(unchanged.review_nonce) == 2

    accepted_payload = json.dumps(
        {
            "decision": "UPHOLD",
            "winner_bid_id": "review-timeout-bid-a",
            "rationale": "current callback",
        },
        sort_keys=True, separators=(",", ":"),
    )
    engine._instances[fake.lower()].review_result = accepted_payload
    callback_args = [
        "review-timeout", 1, 2, current.closed_snapshot_digest,
        current.evaluation_result_digest, current.challenge_set_digest,
        "UPHOLD", "review-timeout-bid-a", _digest(accepted_payload),
    ]
    engine.call_method(
        core, "receive_review_result", callback_args, sender=fake
    )
    assert engine.call_method(
        core, "get_tender", ["review-timeout"]
    ).status == "AWARDED"
    with pytest.raises(Exception):
        engine.call_method(
            core, "receive_review_result", callback_args, sender=fake
        )


def test_review_no_valid_bid_unlocks_exact_finalized_refund(request):
    engine, core, fake = _new(request)
    _create_closed(engine, core, "review-no-valid", with_bid=True)
    tender = _start(engine, core, "review-no-valid")
    evaluation = _comparative_result("review-no-valid")
    engine._instances[fake.lower()].evaluation_result = evaluation
    engine.call_method(
        fake, "emit_evaluation",
        [
            "review-no-valid", 1, tender.closed_snapshot_digest,
            _digest(evaluation),
        ],
        sender=BUYER,
    )
    engine.call_method(
        core, "start_response_window", ["review-no-valid"], sender=EXECUTOR
    )
    engine.call_method(
        core, "submit_challenge",
        [
            "review-no-valid-challenge", "review-no-valid",
            "MANDATORY_REQUIREMENT_MISAPPLIED", "review-no-valid-bid-a",
            "", "", "",
        ],
        sender=BIDDER,
    )
    response = engine.call_method(core, "get_tender", ["review-no-valid"])
    _warp_after(engine, int(response.response_window_end))
    engine.call_method(
        core, "advance_after_response", ["review-no-valid"], sender=EXECUTOR
    )
    reviewing = engine.call_method(core, "get_tender", ["review-no-valid"])
    review_payload = json.dumps(
        {
            "decision": "NO_VALID_BID", "winner_bid_id": "",
            "rationale": "Authenticated challenge invalidated every bid.",
        },
        sort_keys=True, separators=(",", ":"),
    )
    engine._instances[fake.lower()].review_result = review_payload
    engine.call_method(
        core, "receive_review_result",
        [
            "review-no-valid", 1, 1, reviewing.closed_snapshot_digest,
            reviewing.evaluation_result_digest, reviewing.challenge_set_digest,
            "NO_VALID_BID", "", _digest(review_payload),
        ],
        sender=fake,
    )
    no_valid = engine.call_method(core, "get_tender", ["review-no-valid"])
    assert no_valid.status == "NO_VALID_BID"
    assert no_valid.settlement_state == "UNSETTLED"
    engine.call_method(
        core, "refund_no_valid_bid", ["review-no-valid"], sender=BUYER
    )
    accounting = json.loads(engine.call_method(
        core, "get_settlement_accounting", ["review-no-valid"]
    ))
    assert accounting["winner_payout_amount"] == 0
    assert accounting["buyer_refund_amount"] == BUDGET
    assert accounting["financial_outflow_amount"] == BUDGET
    with pytest.raises(Exception):
        engine.call_method(
            core, "confirm_refund", ["review-no-valid"], sender=EXECUTOR
        )
    engine.vm._balances[bytes.fromhex(core[2:])] = (
        accounting["financial_outflow_balance_before"] - BUDGET
    )
    engine.call_method(
        core, "confirm_refund", ["review-no-valid"], sender=EXECUTOR
    )
    final = engine.call_method(core, "get_tender", ["review-no-valid"])
    assert final.status == "NO_VALID_BID"
    assert final.settlement_state == "SETTLED"


def _award(engine, core, fake, tender_id, price=BID_PRICE):
    """Drive an unchallenged comparative evaluation through to AWARDED."""
    _create_closed(engine, core, tender_id, with_bid=True, price=price)
    tender = _start(engine, core, tender_id)
    payload = _comparative_result(tender_id)
    engine._instances[fake.lower()].evaluation_result = payload
    engine.call_method(
        fake, "emit_evaluation",
        [tender_id, 1, tender.closed_snapshot_digest, _digest(payload)],
        sender=BUYER,
    )
    engine.call_method(core, "start_response_window", [tender_id], sender=EXECUTOR)
    response = engine.call_method(core, "get_tender", [tender_id])
    _warp_after(engine, int(response.response_window_end))
    engine.call_method(core, "advance_after_response", [tender_id], sender=EXECUTOR)
    return engine.call_method(core, "get_tender", [tender_id])


def _accounting(engine, core, tender_id):
    return json.loads(
        engine.call_method(core, "get_settlement_accounting", [tender_id])
    )


def _credit_finalized_transfer(engine, core, accounting):
    """Model the finalized outflow the balance-delta gate requires."""
    engine.vm._balances[bytes.fromhex(core[2:])] = (
        accounting["financial_outflow_balance_before"]
        - accounting["financial_outflow_amount"]
    )


def test_award_with_remainder_refund_reaches_terminal_settled(request):
    """Both settlement legs must land the tender in the SETTLED terminal state.

    Regression: confirm_refund previously restored a terminal status only on
    the zero-payout refund paths, so an ordinary award whose winning price was
    below the escrowed budget settled its money correctly but was left
    permanently reporting SETTLEMENT_PENDING.
    """
    engine, core, fake = _new(request)
    awarded = _award(engine, core, fake, "award-remainder")
    assert awarded.status == "AWARDED"
    assert awarded.final_winner == "award-remainder-bid-a"

    engine.call_method(core, "settle_award", ["award-remainder"], sender=EXECUTOR)
    payout = _accounting(engine, core, "award-remainder")
    assert payout["winner_payout_amount"] == BID_PRICE
    assert payout["buyer_refund_amount"] == BUDGET - BID_PRICE
    assert payout["escrow_deposited"] == (
        payout["winner_payout_amount"] + payout["buyer_refund_amount"]
    )
    assert payout["financial_outflow_kind"] == "PAYOUT"
    assert payout["financial_outflow_amount"] == BID_PRICE

    _credit_finalized_transfer(engine, core, payout)
    engine.call_method(core, "confirm_settlement", ["award-remainder"], sender=EXECUTOR)
    refund = _accounting(engine, core, "award-remainder")
    assert refund["payout_confirmed"] is True
    assert refund["settlement_state"] == "REFUND_PENDING"
    assert refund["financial_outflow_kind"] == "REFUND"
    assert refund["financial_outflow_amount"] == BUDGET - BID_PRICE

    _credit_finalized_transfer(engine, core, refund)
    engine.call_method(core, "confirm_refund", ["award-remainder"], sender=EXECUTOR)
    final = engine.call_method(core, "get_tender", ["award-remainder"])
    assert final.status == "SETTLED"
    assert final.settlement_state == "SETTLED"
    settled = _accounting(engine, core, "award-remainder")
    assert settled["payout_confirmed"] is True
    assert settled["refund_confirmed"] is True
    assert settled["financial_outflow_pending"] is False

    # A terminal tender may never move funds a second time.
    with pytest.raises(Exception):
        engine.call_method(core, "confirm_refund", ["award-remainder"], sender=EXECUTOR)
    with pytest.raises(Exception):
        engine.call_method(core, "settle_award", ["award-remainder"], sender=EXECUTOR)


def test_award_without_remainder_reaches_terminal_settled(request):
    """A winning price equal to the escrowed budget settles in one leg."""
    engine, core, fake = _new(request)
    _award(engine, core, fake, "award-exact", price=BUDGET)
    engine.call_method(core, "settle_award", ["award-exact"], sender=EXECUTOR)
    payout = _accounting(engine, core, "award-exact")
    assert payout["winner_payout_amount"] == BUDGET
    assert payout["buyer_refund_amount"] == 0

    _credit_finalized_transfer(engine, core, payout)
    engine.call_method(core, "confirm_settlement", ["award-exact"], sender=EXECUTOR)
    final = engine.call_method(core, "get_tender", ["award-exact"])
    assert final.status == "SETTLED"
    assert final.settlement_state == "SETTLED"
    settled = _accounting(engine, core, "award-exact")
    assert settled["payout_confirmed"] is True
    assert settled["refund_confirmed"] is True
    assert settled["financial_outflow_pending"] is False
    with pytest.raises(Exception):
        engine.call_method(core, "confirm_refund", ["award-exact"], sender=EXECUTOR)
