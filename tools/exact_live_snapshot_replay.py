"""Replay the exact live closed snapshot against the generated v2.1 Evaluator.

The snapshot and all proposal/evidence bodies are read-only exports from the
historical deployment. The model provider is deliberately mocked because this
environment has no configured external provider key; the result is therefore a
diagnostic replay, not production multi-validator evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

from glsim.engine import SimEngine
from glsim.state import StateStore

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = ROOT / "artifacts" / "tender_council_evaluator_v21_deployable.py"
CORE_FIXTURE = ROOT / "tests" / "fixtures" / "evaluator_core_fixture.py"
VERSION = "tendercouncil.evaluator.v2.1"
EXPECTED_SNAPSHOT = "sha256:85880585a3b1617aa8185b133ef79c9fb36082f68853126500d00fde1a9dfc19"
BUYER = "0x" + "10" * 20


def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def mock_web(engine, url: str, body: str) -> None:
    response = {"status": 200, "body": body}
    engine.vm.mock_web(url, response)
    engine.vm.mock_web(url.replace(".", "\\."), response)


def model(snapshot: dict) -> dict:
    candidates = [bid["bid_id"] for bid in snapshot["bids"] if bid["bid_id"].rsplit("-", 1)[-1] in ("a", "b", "c")]
    rows = []
    scores = {
        "a": [30, 17, 14, 8, 8],
        "b": [34, 19, 16, 15, 10],
        "c": [0, 0, 0, 0, 0],
    }
    for bid_id in candidates:
        suffix = bid_id.rsplit("-", 1)[-1]
        technical, delivery, price, capability, support = scores[suffix]
        rows.append({
            "bid_id": bid_id,
            "mandatory_requirements_pass": suffix != "c",
            "technical": technical,
            "delivery": delivery,
            "price": price,
            "capability": capability,
            "support": support,
        })
    return {"classifications": rows, "confidence": "HIGH"}


def one_replay(payload: dict, seed: str) -> dict:
    original_stdin_fd = os.dup(0)
    engine = SimEngine(StateStore(chain_id=4221, seed=seed))
    engine.activate()
    try:
        snapshot = json.loads(payload["snapshot_text"])
        snapshot_digest = payload["snapshot_sha256"]
        if snapshot_digest != EXPECTED_SNAPSHOT or digest(payload["snapshot_text"]) != EXPECTED_SNAPSHOT:
            raise RuntimeError("replay input snapshot digest mismatch")
        core_address, _ = engine.deploy(
            str(CORE_FIXTURE), args=[payload["snapshot_text"], snapshot_digest], sender=BUYER,
        )
        evaluator_address, _ = engine.deploy(
            str(EVALUATOR), args=[core_address, VERSION], sender=BUYER,
        )
        mock_web(engine, payload["brief"]["url"], payload["brief"]["body"])
        for bid in payload["bids"]:
            mock_web(engine, bid["proposal_url"], bid["proposal_body"])
            for item in bid["evidence"]:
                mock_web(engine, item["url"], item["body"])
        engine.vm.mock_llm(
            "Output exactly this JSON object shape",
            json.dumps(model(snapshot), separators=(",", ":")),
        )
        engine.call_method(
            evaluator_address, "start_evaluation_job",
            [snapshot["tender_id"], 1, snapshot_digest], sender=core_address,
        )
        raw = engine.call_method(evaluator_address, "get_evaluation_result", [snapshot["tender_id"], 1])
        result = json.loads(raw)
        winner = f"{snapshot['tender_id']}-bid-b"
        if result.get("status") != "COMPARATIVE" or result.get("winner_bid_id") != winner:
            raise RuntimeError(f"mocked replay result mismatch: {result}")
        return {
            "seed": seed,
            "status": "DIRECT_COMPLETED",
            "votes": "NOT_RUN_IN_EXACT_SNAPSHOT_REPLAY",
            "model_normalized": True,
            "result_status": result["status"],
            "winner_bid_id": result["winner_bid_id"],
            "winner_total_score": result["winner_total_score"],
            "semantic_disqualified_bid_ids": result["semantic_disqualified_bid_ids"],
            "deterministic_disqualified_bid_ids": result["deterministic_disqualified_bid_ids"],
            "dv_or_undetermined": False,
        }
    finally:
        engine.deactivate()
        os.dup2(original_stdin_fd, 0)
        os.close(original_stdin_fd)


def main() -> None:
    payload = json.load(sys.stdin)
    if not EVALUATOR.is_file():
        raise SystemExit(f"missing generated evaluator artifact: {EVALUATOR}")
    samples = [one_replay(payload, f"exact-live-snapshot-replay-{index}") for index in range(1, 6)]
    print(json.dumps({
        "replay_type": "EXACT_LIVE_SNAPSHOT_WITH_MOCKED_PROVIDER_AND_FIXTURE_CORE",
        "live_snapshot_sha": payload["snapshot_sha256"],
        "samples": samples,
        "valid_samples": len(samples),
        "provider": "mocked deterministic classification; no external model key configured",
        "multi_validator": "NOT_AVAILABLE_FOR_EXACT_SNAPSHOT_REPLAY; see full artifact proof",
        "live_transactions_issued": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
