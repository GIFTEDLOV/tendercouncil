"""Run executable semantic classification/admissibility trials on evaluator code."""

from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path


def load_normalizer(source: Path):
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    wanted = {"_canonical", "_same_ids", "_normalize_llm"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    namespace = {"json": json, "MAX_RATIONALE": 2000}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_normalize_llm"]


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


def run(source: Path) -> None:
    normalize = load_normalizer(source)
    canonical_fixture = {
        "A": {"price": 6200, "delivery_days": 26, "support_days": 90, "requirements": ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"]},
        "B": {"price": 7400, "delivery_days": 27, "support_days": 120, "requirements": ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"]},
        "C": {"price": 4300, "delivery_days": 20, "support_days": 90, "requirements": ["CSV export", "responsive/mobile", "dashboard/chart"]},
        "D": {"price": 8700, "delivery_days": 24, "support_days": 120, "requirements": ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"]},
        "E": {"price": 6900, "delivery_days": 45, "support_days": 120, "requirements": ["authentication", "CSV export", "responsive/mobile", "dashboard/chart"]},
    }
    if "authentication" in canonical_fixture["C"]["requirements"]:
        raise SystemExit("canonical Bid C fixture accidentally satisfies authentication")
    if canonical_fixture["D"]["price"] <= 8000 or canonical_fixture["E"]["delivery_days"] <= 30:
        raise SystemExit("canonical deterministic invalid fixture was weakened")
    accepted = normalize(result(), ["A", "B", "C", "D", "E"], ["D", "E"], [], ["A", "B", "C"], [35, 20, 20, 15, 10])
    if accepted["valid_bid_ids"] != ["A", "B"] or accepted["semantic_disqualified_bid_ids"] != ["C"]:
        raise SystemExit("semantic result did not preserve C disqualification")
    resurrected = copy.deepcopy(result())
    resurrected["semantic_candidate_ids"] = ["A", "B", "C", "D"]
    resurrected["semantic_classifications"].append({"bid_id": "D", "mandatory_requirements_pass": True})
    resurrected["valid_bid_ids"] = ["A", "B", "D"]
    resurrected["disqualified_bid_ids"] = ["C", "E"]
    try:
        normalize(resurrected, ["A", "B", "C", "D", "E"], ["D", "E"], [], ["A", "B", "C", "D"], [35, 20, 20, 15, 10])
    except Exception:
        pass
    else:
        raise SystemExit("deterministically invalid bid was resurrected")
    print("semantic policy trials: PASS (A/B valid, C semantic-disqualified, D/E deterministic)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("contracts/tender_council_evaluator.py"))
    args = parser.parse_args()
    run(args.source)


if __name__ == "__main__":
    main()
