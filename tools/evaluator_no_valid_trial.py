"""Execute the real Evaluator snapshot path for all-semantic-fail NO_VALID_BID."""

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


BUYER = "0x" + "aa" * 20
ZERO_HASH = "sha256:" + "0" * 64


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def run(evaluator_path: Path, core_fixture_path: Path) -> None:
    bids = []
    web = {}
    for index in range(3):
        bidder = "0x" + format(index + 1, "02x") * 20
        url = "https://fixture.example/proposal-" + str(index)
        manifest = {
            "schema_version": "tendercouncil.bid.v1", "tender_id": "semantic-all-fail",
            "bidder": bidder, "price_wei": 7_000_000_000_000_000_000 + index,
            "delivery_days": 20, "support_days": 90, "evidence": [],
            "proposal": {
                "technical_approach": "A bounded implementation.",
                "delivery_plan": "Deliver in twenty days.",
                "support_plan": "Provide ninety days of support.",
                "requirements": ["CSV export"],
            },
        }
        raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        web[url] = {"status": 200, "body": raw.decode()}
        bids.append({
            "bid_id": "B" + str(index), "bidder": bidder,
            "price_wei": manifest["price_wei"], "delivery_days": 20, "support_days": 90,
            "proposal_url": url, "proposal_sha256": digest(raw), "evidence_commitments": "",
            "schema_version": "tendercouncil.bid.v1", "submitted_at": 1700000000 + index,
        })
    snapshot = {
        "schema_version": "tendercouncil.snapshot.v1", "tender_id": "semantic-all-fail",
        "buyer": BUYER, "title": "Semantic failure fixture", "brief_url": "https://fixture.example/brief",
        "brief_sha256": ZERO_HASH, "max_budget_wei": 8_000_000_000_000_000_000,
        "max_delivery_days": 30, "min_support_days": 90, "bidding_deadline": 1800000000,
        "response_window_seconds": 7200, "requirements": "authentication;CSV export",
        "rubric": "technical=35;delivery=20;price=20;capability=15;support=10",
        "evidence_policy": "capability:optional;delivery:optional;support:optional;technical:optional",
        "bids": bids,
    }
    snapshot_raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    snapshot_digest = digest(snapshot_raw)
    result = {
        "classifications": [
            {"bid_id": bid, "mandatory_requirements_pass": False,
             "technical": 0, "delivery": 0, "price": 0,
             "capability": 0, "support": 0}
            for bid in ("B0", "B1", "B2")
        ],
        "confidence": "LOW",
    }
    result_text = json.dumps(result, sort_keys=True, separators=(",", ":"))
    engine = SimEngine(StateStore(chain_id=4221, seed="semantic-all-fail"))
    engine.activate()
    for url, response in web.items():
        engine.vm.mock_web(url, response)
    engine.vm.mock_llm("Output exactly this JSON object shape", result_text)
    core_address, _ = engine.deploy(str(core_fixture_path), args=[snapshot_raw.decode(), snapshot_digest], sender=BUYER)
    evaluator_address, _ = engine.deploy(str(evaluator_path), args=[core_address, "tendercouncil.evaluator.v2.1"], sender=BUYER)
    engine.call_method(evaluator_address, "start_evaluation_job", ["semantic-all-fail", 1, snapshot_digest], sender=core_address)
    record = json.loads(engine.call_method(evaluator_address, "get_evaluation_result", ["semantic-all-fail", 1]))
    if record["status"] != "NO_VALID_BID" or record["semantic_candidate_ids"] != ["B0", "B1", "B2"] or record["semantic_disqualified_bid_ids"] != ["B0", "B1", "B2"] or record["valid_bid_ids"]:
        raise SystemExit("real evaluator all-semantic-fail path did not preserve NO_VALID_BID categories")
    print("real evaluator all-semantic-fail trial: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluator", type=Path, default=Path("contracts/tender_council_evaluator.py"))
    parser.add_argument("--core-fixture", type=Path, default=Path("tests/fixtures/evaluator_core_fixture.py"))
    args = parser.parse_args()
    run(args.evaluator, args.core_fixture)


if __name__ == "__main__":
    main()
