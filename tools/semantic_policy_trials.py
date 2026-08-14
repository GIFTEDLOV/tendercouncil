"""Run executable semantic classification/admissibility trials on evaluator code."""

from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path


def load_normalizer(source: Path):
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    wanted = {
        "_canonical", "_same_ids", "_string_list",
        "_try_normalize_evaluation_model",
    }
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    namespace = {"json": json, "MAX_RATIONALE": 2000, "MAX_BIDS": 32}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_try_normalize_evaluation_model"]


def result() -> dict:
    return {
        "status": "COMPARATIVE", "deterministic_disqualified_bid_ids": ["D", "E"],
        "integrity_disqualified_bid_ids": [], "semantic_candidate_ids": ["A", "B", "C"],
        "semantic_disqualified_bid_ids": ["C"],
        "semantic_classifications": [
            {"bid_id": "A", "mandatory_requirements_pass": True},
            {"bid_id": "B", "mandatory_requirements_pass": True},
            {"bid_id": "C", "mandatory_requirements_pass": False},
        ],
        "valid_bid_ids": ["A", "B"], "disqualified_bid_ids": ["C", "D", "E"],
        "scores": [
            {"bid_id": "A", "technical": 30, "delivery": 17, "price": 14, "capability": 8, "support": 8, "total": 77},
            {"bid_id": "B", "technical": 34, "delivery": 19, "price": 16, "capability": 15, "support": 10, "total": 94},
        ],
        "winner_bid_id": "B", "winner_total_score": 94,
        "runner_up_bid_id": "A", "runner_up_score": 77,
        "confidence": "HIGH", "rationale": "natural policy result",
    }


def all_semantic_fail_result() -> dict:
    return {
        "status": "NO_VALID_BID", "deterministic_disqualified_bid_ids": ["D", "E"],
        "integrity_disqualified_bid_ids": [], "semantic_candidate_ids": ["A", "B", "C"],
        "semantic_disqualified_bid_ids": ["A", "B", "C"],
        "semantic_classifications": [
            {"bid_id": "A", "mandatory_requirements_pass": False},
            {"bid_id": "B", "mandatory_requirements_pass": False},
            {"bid_id": "C", "mandatory_requirements_pass": False},
        ], "valid_bid_ids": [], "disqualified_bid_ids": ["A", "B", "C", "D", "E"],
        "scores": [], "winner_bid_id": "", "winner_total_score": 0,
        "runner_up_bid_id": "", "runner_up_score": 0,
        "confidence": "LOW", "rationale": "all semantic candidates failed",
    }


def run(source: Path) -> None:
    normalize = load_normalizer(source)
    canonical_fixture = {
        "A": {"price_wei": 6_200_000_000_000_000_000, "delivery_days": 26, "support_days": 90, "requirements": ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"]},
        "B": {"price_wei": 7_400_000_000_000_000_000, "delivery_days": 27, "support_days": 120, "requirements": ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"]},
        "C": {"price_wei": 4_300_000_000_000_000_000, "delivery_days": 20, "support_days": 90, "requirements": ["CSV export", "responsive/mobile", "dashboard/chart"]},
        "D": {"price_wei": 8_700_000_000_000_000_000, "delivery_days": 24, "support_days": 120, "requirements": ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"]},
        "E": {"price_wei": 6_900_000_000_000_000_000, "delivery_days": 45, "support_days": 120, "requirements": ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"]},
    }
    if "authentication" in canonical_fixture["C"]["requirements"]:
        raise SystemExit("canonical Bid C fixture accidentally satisfies authentication")
    if canonical_fixture["D"]["price_wei"] <= 8_000_000_000_000_000_000 or canonical_fixture["E"]["delivery_days"] <= 30:
        raise SystemExit("canonical deterministic invalid fixture was weakened")
    accepted = normalize(result(), ["A", "B", "C", "D", "E"], ["D", "E"], [], ["A", "B", "C"], [35, 20, 20, 15, 10])
    if accepted["valid_bid_ids"] != ["A", "B"] or accepted["semantic_disqualified_bid_ids"] != ["C"]:
        raise SystemExit("semantic result did not preserve C disqualification")
    resurrected = copy.deepcopy(result())
    resurrected["semantic_candidate_ids"] = ["A", "B", "C", "D"]
    resurrected["semantic_classifications"].append({"bid_id": "D", "mandatory_requirements_pass": True})
    resurrected["valid_bid_ids"] = ["A", "B", "D"]
    resurrected["disqualified_bid_ids"] = ["C", "E"]
    if normalize(resurrected, ["A", "B", "C", "D", "E"], ["D", "E"], [], ["A", "B", "C", "D"], [35, 20, 20, 15, 10]) is not None:
        raise SystemExit("deterministically invalid bid was resurrected")
    no_valid = normalize(all_semantic_fail_result(), ["A", "B", "C", "D", "E"], ["D", "E"], [], ["A", "B", "C"], [35, 20, 20, 15, 10])
    if no_valid["status"] != "NO_VALID_BID" or no_valid["semantic_candidate_ids"] != ["A", "B", "C"] or no_valid["valid_bid_ids"]:
        raise SystemExit("all-semantic-fail result was not represented as NO_VALID_BID")
    integrity_result = result()
    integrity_result["integrity_disqualified_bid_ids"] = ["C"]
    integrity_result["semantic_candidate_ids"] = ["A", "B"]
    integrity_result["semantic_disqualified_bid_ids"] = []
    integrity_result["semantic_classifications"] = [
        {"bid_id": "A", "mandatory_requirements_pass": True},
        {"bid_id": "B", "mandatory_requirements_pass": True},
    ]
    integrity_result["valid_bid_ids"] = ["A", "B"]
    integrity_result["disqualified_bid_ids"] = ["C", "D", "E"]
    integrity_result["scores"] = [row for row in integrity_result["scores"] if row["bid_id"] in ("A", "B")]
    normalize(integrity_result, ["A", "B", "C", "D", "E"], ["D", "E"], ["C"], ["A", "B"], [35, 20, 20, 15, 10])
    tampered_integrity = copy.deepcopy(integrity_result)
    tampered_integrity["integrity_disqualified_bid_ids"] = []
    if normalize(tampered_integrity, ["A", "B", "C", "D", "E"], ["D", "E"], ["C"], ["A", "B"], [35, 20, 20, 15, 10]) is not None:
        raise SystemExit("LLM changed independently computed integrity set")
    print("semantic policy trials: PASS (A/B valid, C semantic-disqualified, D/E deterministic, all-fail NO_VALID_BID)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("contracts/tender_council_evaluator.py"))
    args = parser.parse_args()
    run(args.source)


if __name__ == "__main__":
    main()
