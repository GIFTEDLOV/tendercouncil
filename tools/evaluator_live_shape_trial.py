"""Run the exact five-bid/evidence evaluator shape in the pinned simulator."""

from __future__ import annotations

import hashlib
import json
import ast
from pathlib import Path

from glsim.engine import SimEngine
from glsim.state import StateStore


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ARTIFACT = ROOT / "artifacts" / "tender_council_bradbury_e2e_failure_2026-08-12T174123184Z.json"
EVALUATOR = ROOT / "contracts" / "tender_council_evaluator.py"
CORE_FIXTURE = ROOT / "tests" / "fixtures" / "evaluator_core_fixture.py"


def digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def check_manifests(snapshot: dict) -> None:
    tree = ast.parse(EVALUATOR.read_text(encoding="utf-8"))
    wanted = {"_hash_bytes", "_commitment_set", "_validate_manifest"}
    nodes = [node for node in tree.body if isinstance(node, ast.Import) and any(alias.name != "genlayer" for alias in node.names)]
    nodes += [node for node in tree.body if isinstance(node, ast.Assign)]
    nodes += [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    nodes += [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {"_hash_bytes", "_commitment_set"}]
    nodes += [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_validate_manifest"]
    nodes += [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_validate_evidence"]
    namespace = {
        "hashlib": hashlib, "json": json, "MAX_MANIFEST_BYTES": 32768,
        "MAX_FIELD": 6000, "MANIFEST_SCHEMA_VERSION": "tendercouncil.bid.v1",
    }
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, str(EVALUATOR), "exec"), namespace)
    for bid in snapshot["bids"]:
        raw = (ROOT / "fixtures" / "live" / "manifests" / (bid["bid_id"].replace("bid-", "bid_") + ".json")).read_bytes()
        result = namespace["_validate_manifest"](raw, bid, snapshot["tender_id"])
        if result is None:
            raise SystemExit(f"manifest validator rejected {bid['bid_id']}")
        for item in result["evidence"]:
            raw_evidence = (ROOT / "fixtures" / "live" / "blobs" / item["url"].rsplit("/", 1)[1]).read_bytes()
            if "sha256:" + hashlib.sha256(raw_evidence).hexdigest() != item["sha256"]:
                raise SystemExit(f"evidence fixture digest mismatch: {bid['bid_id']}")


def main() -> None:
    manifest = json.loads(SNAPSHOT_ARTIFACT.read_text(encoding="utf-8"))
    snapshot = json.loads(manifest["snapshot"]["canonical_json"])
    snapshot["tender_id"] = "analytics-dashboard-2026-recovery"
    web = {}
    for bid in snapshot["bids"]:
        proposal_url = "https://fixture.example/recovery/" + bid["bid_id"] + ".json"
        proposal_path = ROOT / "fixtures" / "live" / "recovery" / "manifests" / (bid["bid_id"].replace("bid-", "bid_") + ".json")
        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        proposal["tender_id"] = snapshot["tender_id"]
        for evidence in proposal["evidence"]:
            evidence_path = ROOT / "fixtures" / "live" / "blobs" / evidence["url"].rsplit("/", 1)[1]
            evidence_raw = evidence_path.read_bytes()
            evidence["sha256"] = digest(evidence_raw)
            web[evidence["url"]] = {"status": 200, "body": evidence_raw.decode("utf-8")}
        proposal_raw = json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode("utf-8")
        bid["proposal_sha256"] = digest(proposal_raw)
        bid["proposal_url"] = proposal_url
        bid["evidence_commitments"] = ";".join(
            item["evidence_id"] + "|" + item["kind"] + "|" + item["criterion"] + "|"
            + ("1" if item["required"] else "0") + "|" + item["url"] + "|" + item["sha256"]
            for item in proposal["evidence"]
        )
        web[proposal_url] = {"status": 200, "body": proposal_raw.decode("utf-8")}
    snapshot_raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    snapshot_text = snapshot_raw.decode("utf-8")
    snapshot_digest = digest(snapshot_raw)
    result = {
        "confidence": "HIGH",
        "deterministic_disqualified_bid_ids": ["bid-d", "bid-e"],
        "integrity_disqualified_bid_ids": [],
        "semantic_candidate_ids": ["bid-a", "bid-b", "bid-c"],
        "semantic_disqualified_bid_ids": ["bid-c"],
        "semantic_classifications": [
            {"bid_id": "bid-a", "mandatory_requirements_pass": True},
            {"bid_id": "bid-b", "mandatory_requirements_pass": True},
            {"bid_id": "bid-c", "mandatory_requirements_pass": False},
        ],
        "disqualified_bid_ids": ["bid-c", "bid-d", "bid-e"],
        "rationale": "B best satisfies the locked policy.",
        "runner_up_bid_id": "bid-a",
        "runner_up_score": 77,
        "scores": [
            {"bid_id": "bid-a", "technical": 30, "delivery": 17, "price": 14, "capability": 8, "support": 8, "total": 77},
            {"bid_id": "bid-b", "technical": 34, "delivery": 19, "price": 16, "capability": 15, "support": 10, "total": 94},
        ],
        "status": "COMPARATIVE",
        "valid_bid_ids": ["bid-a", "bid-b"],
        "winner_bid_id": "bid-b",
        "winner_total_score": 94,
    }
    engine = SimEngine(StateStore(chain_id=4221, seed="tendercouncil-live-shape"))
    engine.activate()
    for url, response in web.items():
        engine.vm.mock_web(url, response)
        engine.vm.mock_web(url.replace(".", "\\."), response)
    engine.vm.mock_llm("Required fields: status", json.dumps(result, sort_keys=True, separators=(",", ":")))
    core_address, _ = engine.deploy(str(CORE_FIXTURE), args=[snapshot_text, snapshot_digest], sender="0x" + "aa" * 20)
    evaluator_address, _ = engine.deploy(str(EVALUATOR), args=[core_address, "tendercouncil.evaluator.v1"], sender="0x" + "aa" * 20)
    engine.call_method(evaluator_address, "start_evaluation_job", [snapshot["tender_id"], 1, snapshot_digest], sender=core_address)
    payload = json.loads(engine.call_method(evaluator_address, "get_evaluation_result", [snapshot["tender_id"], 1]))
    print("web_mocks_hit", sorted(engine.vm._web_mocks_hit), "of", len(engine.vm._web_mocks))
    if payload["winner_bid_id"] != "bid-b" or payload["integrity_disqualified_bid_ids"] != []:
        raise SystemExit(f"unexpected result: {payload}")
    print("exact five-bid/evidence evaluator shape: PASS")


if __name__ == "__main__":
    main()
