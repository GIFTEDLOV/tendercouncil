"""Executable cross-contract security probes used by split mutation tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from glsim.engine import SimEngine
from glsim.state import StateStore

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


BUYER = "0x" + "11" * 20
ATTACKER = "0x" + "22" * 20
DEADLINE = 1798761600
HASH = "sha256:" + "a" * 64
BUDGET_WEI = 8_000_000_000_000_000_000


def digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_engine(core_path: Path, fake_path: Path):
    engine = SimEngine(StateStore(chain_id=4221, seed="split-security-probe"))
    engine.activate()
    core_address, core = engine.deploy(str(core_path), sender=BUYER)
    fake_address, fake = engine.deploy(str(fake_path), args=[core_address], sender=BUYER)
    engine.call_method(core_address, "bind_evaluator", [type(core.bootstrapper)(fake_address), "tendercouncil.evaluator.v2.1", HASH], sender=BUYER)
    return engine, core_address, fake_address


def fund(engine, address: str, amount: int = BUDGET_WEI):
    engine.vm._balances[bytes.fromhex(address[2:])] = amount


def create_open_close(engine, core_address: str, tender_id: str = "probe"):
    engine.vm.value = BUDGET_WEI
    engine.call_method(core_address, "create_tender", [
        tender_id, "Probe tender", "https://buyer.example/brief", HASH,
        BUDGET_WEI, 30, 90, DEADLINE, 7200,
        "authentication;CSV export;responsive/mobile;dashboard/chart",
        35, 20, 20, 15, 10, "capability:required;secondary:optional",
    ], sender=BUYER)
    engine.vm.value = 0
    fund(engine, core_address, BUDGET_WEI)
    engine.call_method(core_address, "open_tender", [tender_id], sender=BUYER)
    engine.vm.warp("2027-02-01T00:00:00Z")
    engine.call_method(core_address, "close_tender", [tender_id], sender=BUYER)


def enter_evaluating(engine, core_address: str, fake_address: str):
    create_open_close(engine, core_address)
    engine.call_method(core_address, "start_evaluation", ["probe"], sender=BUYER)
    snapshot = engine.call_method(core_address, "get_tender", ["probe"])
    return snapshot.closed_snapshot_digest


def no_valid_result_digest(fake_instance) -> str:
    return digest(fake_instance.evaluation_result)


def evaluation_control(core_path: Path, fake_path: Path, control: str):
    engine, core, fake = new_engine(core_path, fake_path)
    snapshot = enter_evaluating(engine, core, fake)
    fake_instance = engine._instances[fake.lower()]
    correct_digest = no_valid_result_digest(fake_instance)
    nonce = 1
    callback_snapshot = snapshot if control != "snapshot" else HASH
    callback_nonce = nonce if control != "nonce" else 2
    callback_digest = correct_digest if control != "result-digest" else HASH

    if control == "caller":
        try:
            engine.call_method(core, "receive_evaluation_result", [
                "probe", nonce, snapshot, "tendercouncil.evaluator.v2.1", "NO_VALID_BID", "", correct_digest,
            ], sender=ATTACKER)
        except Exception:
            return True
        return False

    if control == "duplicate" or control == "lifecycle":
        engine.call_method(fake, "emit_evaluation", ["probe", nonce, snapshot, correct_digest], sender=BUYER)
        first = engine.call_method(core, "get_tender", ["probe"])
        first_digest = str(first.evaluation_result_digest)
        changed = json.dumps({
            "status": "NO_VALID_BID", "winner_bid_id": "", "valid_bid_ids": [],
            "disqualified_bid_ids": [], "scores": [], "winner_total_score": 0,
            "deterministic_disqualified_bid_ids": [], "integrity_disqualified_bid_ids": [],
            "semantic_candidate_ids": [], "semantic_disqualified_bid_ids": [],
            "semantic_classifications": [],
            "runner_up_bid_id": "", "runner_up_score": 0, "confidence": "LOW",
            "rationale": "changed duplicate callback",
        }, sort_keys=True, separators=(",", ":"))
        fake_instance.evaluation_result = changed
        engine.call_method(fake, "emit_evaluation", ["probe", nonce, snapshot, digest(changed)], sender=BUYER)
        second = engine.call_method(core, "get_tender", ["probe"])
        return first_digest == str(second.evaluation_result_digest)

    engine.call_method(fake, "emit_evaluation", ["probe", callback_nonce, callback_snapshot, callback_digest], sender=BUYER)
    return engine.call_method(core, "get_tender", ["probe"]).status == "EVALUATING"


def review_correlation(core_path: Path, fake_path: Path):
    engine, core, fake = new_engine(core_path, fake_path)
    engine.vm.value = BUDGET_WEI
    engine.call_method(core, "create_tender", [
        "review", "Probe tender", "https://buyer.example/brief", HASH,
        BUDGET_WEI, 30, 90, DEADLINE, 7200,
        "authentication;CSV export;responsive/mobile;dashboard/chart",
        35, 20, 20, 15, 10, "capability:required;secondary:optional",
    ], sender=BUYER)
    engine.vm.value = 0
    fund(engine, core, BUDGET_WEI)
    engine.call_method(core, "open_tender", ["review"], sender=BUYER)
    engine.call_method(core, "submit_bid", [
        "bid", "review", 7_400_000_000_000_000_000, 27, 120, "https://bidder.example/proposal", HASH, "", "tendercouncil.bid.v1",
    ], sender=ATTACKER)
    engine.vm.warp("2027-02-01T00:00:00Z")
    engine.call_method(core, "close_tender", ["review"], sender=BUYER)
    engine.call_method(core, "start_evaluation", ["review"], sender=BUYER)
    fake_instance = engine._instances[fake.lower()]
    result = json.dumps({
        "status": "COMPARATIVE", "winner_bid_id": "bid", "valid_bid_ids": ["bid"],
        "disqualified_bid_ids": [], "scores": [{"bid_id": "bid", "technical": 35,
        "delivery": 20, "price": 20, "capability": 15, "support": 10, "total": 100}],
        "deterministic_disqualified_bid_ids": [], "integrity_disqualified_bid_ids": [],
        "semantic_candidate_ids": ["bid"], "semantic_disqualified_bid_ids": [],
        "semantic_classifications": [{"bid_id": "bid", "mandatory_requirements_pass": True}],
        "winner_total_score": 100, "runner_up_bid_id": "", "runner_up_score": 0,
        "confidence": "HIGH", "rationale": "test result",
    }, sort_keys=True, separators=(",", ":"))
    fake_instance.evaluation_result = result
    tender = engine.call_method(core, "get_tender", ["review"])
    engine.call_method(fake, "emit_evaluation", ["review", 1, tender.closed_snapshot_digest, digest(result)], sender=BUYER)
    engine.call_method(core, "start_response_window", ["review"], sender=BUYER)
    engine.call_method(core, "submit_challenge", ["challenge", "review", "MANDATORY_REQUIREMENT_MISAPPLIED", "bid", "", "", ""], sender=ATTACKER)
    try:
        engine.call_method(core, "resolve_challenge", ["challenge", True, "buyer censorship"], sender=BUYER)
    except Exception:
        pass
    else:
        return False
    engine.vm.warp("2027-02-02T00:00:00Z")
    engine.call_method(core, "advance_after_response", ["review"], sender=BUYER)
    tender = engine.call_method(core, "get_tender", ["review"])
    original = tender.evaluation_result_digest
    fake_instance.review_result = json.dumps({"decision": "UPHOLD", "winner_bid_id": "bid", "rationale": "test review"}, sort_keys=True, separators=(",", ":"))
    challenge_digest = tender.challenge_set_digest
    try:
        engine.call_method(fake, "emit_review", ["review", 1, 1, tender.closed_snapshot_digest, original, HASH, digest(fake_instance.review_result)], sender=BUYER)
    except Exception:
        return True
    return engine.call_method(core, "get_tender", ["review"]).status == "REVIEWING_CHALLENGES"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--fake", type=Path, required=True)
    parser.add_argument("--control", choices=["caller", "snapshot", "nonce", "result-digest", "duplicate", "lifecycle", "review-correlation"], required=True)
    args = parser.parse_args()
    if args.control == "review-correlation":
        caught = review_correlation(args.core, args.fake)
    else:
        caught = evaluation_control(args.core, args.fake, args.control)
    if not caught:
        raise SystemExit(f"security control survived: {args.control}")
    print(f"caught executable split control: {args.control}")


if __name__ == "__main__":
    main()
