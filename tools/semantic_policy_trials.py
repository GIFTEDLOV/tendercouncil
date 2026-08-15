"""Executable semantic/admissibility trials for the reduced v2.1 model boundary."""

from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path


def load_helpers(source: Path):
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    wanted = {"_try_normalize_evaluation_model", "_derive_evaluation_result"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_try_normalize_evaluation_model"], namespace["_derive_evaluation_result"]


def model(rows, confidence="HIGH"):
    return {"classifications": rows, "confidence": confidence}


def canonical_rows(pass_ids, fail_ids=()):
    rows = []
    for bid_id in list(pass_ids) + list(fail_ids):
        scores = {
            "A": (34, 19, 16, 15, 10),
            "B": (30, 18, 14, 13, 8),
        }.get(bid_id, (0, 0, 0, 0, 0))
        rows.append({
            "bid_id": bid_id,
            "mandatory_requirements_pass": bid_id in pass_ids,
            "technical": scores[0], "delivery": scores[1],
            "price": scores[2], "capability": scores[3], "support": scores[4],
        })
    return rows


def run(source: Path) -> None:
    normalize, derive = load_helpers(source)
    all_ids = ["A", "B", "C", "D", "E"]
    deterministic = ["D", "E"]
    integrity = []
    candidates = ["A", "B", "C"]
    weights = [35, 20, 20, 15, 10]

    valid_model = model(canonical_rows(["A", "B"], ["C"]))
    normalized = normalize(valid_model, all_ids, deterministic, integrity, candidates, weights)
    assert set(item["bid_id"] for item in normalized["classifications"]) == set(candidates)
    derived = derive(normalized, all_ids, deterministic, integrity, candidates)
    assert derived["valid_bid_ids"] == ["A", "B"]
    assert derived["semantic_disqualified_bid_ids"] == ["C"]
    assert derived["disqualified_bid_ids"] == ["C", "D", "E"]
    assert derived["winner_bid_id"] == "A"
    assert derived["runner_up_bid_id"] == "B"
    assert derived["winner_total_score"] == 94

    resurrected = copy.deepcopy(valid_model)
    resurrected["classifications"].append(canonical_rows(["D"])[0])
    assert normalize(resurrected, all_ids, deterministic, integrity, candidates, weights) is None

    all_fail = model(canonical_rows([], ["A", "B", "C"]), "LOW")
    normalized_fail = normalize(all_fail, all_ids, deterministic, integrity, candidates, weights)
    no_valid = derive(normalized_fail, all_ids, deterministic, integrity, candidates)
    assert no_valid["status"] == "NO_VALID_BID"
    assert no_valid["winner_bid_id"] == ""
    assert no_valid["scores"] == []

    integrity_context = ["C"]
    integrity_model = model(canonical_rows(["A", "B"]))
    normalized_integrity = normalize(
        integrity_model, all_ids, deterministic, integrity_context, ["A", "B"], weights,
    )
    integrity_result = derive(
        normalized_integrity, all_ids, deterministic, integrity_context, ["A", "B"],
    )
    assert integrity_result["integrity_disqualified_bid_ids"] == ["C"]
    assert integrity_result["disqualified_bid_ids"] == ["C", "D", "E"]

    print("reduced semantic policy trials: PASS (A/B valid, C semantic-disqualified, D/E deterministic, all-fail NO_VALID_BID, integrity derived)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("contracts/tender_council_evaluator.py"))
    run(parser.parse_args().source)


if __name__ == "__main__":
    main()
