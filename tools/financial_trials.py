"""Execute wei accounting and serialized Core outflow trials in glsim."""

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
BIDDER_A = "0x" + "22" * 20
BIDDER_B = "0x" + "33" * 20
DEADLINE = 1798761600
HASH = "sha256:" + "a" * 64
BUDGET_WEI = 8_000_000_000_000_000_000
PRICE_A_WEI = 6_200_000_000_000_000_000
PRICE_B_WEI = 7_400_000_000_000_000_000


def digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_result(bid_id: str) -> str:
    value = {
        "status": "COMPARATIVE", "winner_bid_id": bid_id, "valid_bid_ids": [bid_id],
        "disqualified_bid_ids": [], "scores": [{
            "bid_id": bid_id, "technical": 35, "delivery": 20, "price": 20,
            "capability": 15, "support": 10, "total": 100,
        }], "winner_total_score": 100, "runner_up_bid_id": "", "runner_up_score": 0,
        "deterministic_disqualified_bid_ids": [], "integrity_disqualified_bid_ids": [],
        "semantic_candidate_ids": [bid_id], "semantic_disqualified_bid_ids": [],
        "semantic_classifications": [{"bid_id": bid_id, "mandatory_requirements_pass": True}],
        "confidence": "HIGH", "rationale": "financial accounting trial",
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def call(engine, address, method, args, sender=BUYER):
    return engine.call_method(address, method, args, sender=sender)


def accounting(engine, address, tender_id):
    return json.loads(call(engine, address, "get_settlement_accounting", [tender_id]))


def run(core_path: Path, fake_path: Path) -> None:
    engine = SimEngine(StateStore(chain_id=4221, seed="financial-trials"))
    engine.activate()
    core_address, core = engine.deploy(str(core_path), sender=BUYER)
    fake_address, _ = engine.deploy(str(fake_path), args=[core_address], sender=BUYER)
    call(engine, core_address, "bind_evaluator", [type(core.bootstrapper)(fake_address), "tendercouncil.evaluator.v1", HASH])
    total_budget = BUDGET_WEI * 3
    for tender_id in ("A", "B", "C"):
        engine.vm.value = BUDGET_WEI
        call(engine, core_address, "create_tender", [
            tender_id, "Financial trial", "https://buyer.example/brief", HASH,
            BUDGET_WEI, 30, 90, DEADLINE, 7200,
            "authentication;CSV export;responsive/mobile;dashboard/chart",
            35, 20, 20, 15, 10, "capability:optional;secondary:optional",
        ])
    engine.vm.value = 0
    engine.vm._balances[bytes.fromhex(core_address[2:])] = total_budget
    for tender_id, bid_id, bidder, price in (("A", "bid-a", BIDDER_A, PRICE_A_WEI), ("B", "bid-b", BIDDER_B, PRICE_B_WEI)):
        call(engine, core_address, "open_tender", [tender_id])
        call(engine, core_address, "submit_bid", [
            bid_id, tender_id, price, 26, 90, "https://bidder.example/" + bid_id,
            HASH, "", "tendercouncil.bid.v1",
        ], sender=bidder)
    engine.vm.warp("2027-02-01T00:00:00Z")
    for tender_id in ("A", "B"):
        call(engine, core_address, "close_tender", [tender_id])
        call(engine, core_address, "start_evaluation", [tender_id])
    fake = engine._instances[fake_address.lower()]
    for tender_id, bid_id in (("A", "bid-a"), ("B", "bid-b")):
        payload = make_result(bid_id)
        fake.evaluation_result = payload
        tender = call(engine, core_address, "get_tender", [tender_id])
        call(engine, fake_address, "emit_evaluation", [tender_id, 1, tender.closed_snapshot_digest, digest(payload)])
        call(engine, core_address, "start_response_window", [tender_id])
    engine.vm.warp("2027-02-01T03:00:01Z")
    for tender_id in ("A", "B"):
        call(engine, core_address, "advance_after_response", [tender_id])
    call(engine, core_address, "settle_award", ["A"])
    outflow = accounting(engine, core_address, "A")
    if not outflow["financial_outflow_pending"] or outflow["financial_outflow_tender_id"] != "A" or outflow["financial_outflow_kind"] != "PAYOUT" or outflow["financial_outflow_amount"] != PRICE_A_WEI:
        raise SystemExit("winner-price payout was not locked as a global outflow")
    settlement = accounting(engine, core_address, "A")
    if settlement["winner_payout_amount"] != PRICE_A_WEI or settlement["buyer_refund_amount"] != BUDGET_WEI - PRICE_A_WEI:
        raise SystemExit("successful settlement accounting used the wrong commercial amounts")
    try:
        call(engine, core_address, "settle_award", ["B"])
    except Exception:
        pass
    else:
        raise SystemExit("Tender B payout bypassed the global financial outflow lock")
    try:
        call(engine, core_address, "cancel_tender", ["C"])
    except Exception:
        pass
    else:
        raise SystemExit("unrelated refund bypassed the global financial outflow lock")
    for method, tender_id in (("confirm_settlement", "B"), ("confirm_refund", "A")):
        try:
            call(engine, core_address, method, [tender_id])
        except Exception:
            pass
        else:
            raise SystemExit("wrong tender or outflow kind cleared the global lock")
    before = outflow["financial_outflow_balance_before"]
    engine.vm._balances[bytes.fromhex(core_address[2:])] = before - PRICE_A_WEI
    call(engine, core_address, "confirm_settlement", ["A"])
    outflow = accounting(engine, core_address, "A")
    if not outflow["financial_outflow_pending"] or outflow["financial_outflow_kind"] != "REFUND" or outflow["financial_outflow_amount"] != BUDGET_WEI - PRICE_A_WEI:
        raise SystemExit("payout confirmation did not begin the exact buyer remainder refund")
    before = outflow["financial_outflow_balance_before"]
    engine.vm._balances[bytes.fromhex(core_address[2:])] = before - (BUDGET_WEI - PRICE_A_WEI)
    call(engine, core_address, "confirm_refund", ["A"])
    final = json.loads(call(engine, core_address, "get_settlement_accounting", ["A"]))
    if final["settlement_state"] != "SETTLED" or not final["payout_confirmed"] or not final["refund_confirmed"]:
        raise SystemExit("settlement confirmations did not close accounting")
    if accounting(engine, core_address, "A")["financial_outflow_pending"]:
        raise SystemExit("financial outflow lock was not cleared after refund confirmation")
    try:
        call(engine, core_address, "confirm_refund", ["A"])
    except Exception:
        pass
    else:
        raise SystemExit("refund confirmation replay was accepted")
    call(engine, core_address, "settle_award", ["B"])
    print("financial trials: PASS (wei payout, remainder refund, global serialized outflow lock)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", type=Path, default=Path("contracts/tender_council_core.py"))
    parser.add_argument("--fake", type=Path, default=Path("tests/fixtures/split_fake_evaluator.py"))
    args = parser.parse_args()
    run(args.core, args.fake)


if __name__ == "__main__":
    main()
