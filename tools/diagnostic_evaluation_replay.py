"""Local mutation/equivalence proof for the reduced v2.1 model boundary."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import random
from pathlib import Path


MAX_BIDS = 32
EXPECTED = ("classifications", "confidence")
ROW_KEYS = tuple(sorted((
    "bid_id", "mandatory_requirements_pass", "technical", "delivery",
    "price", "capability", "support",
)))


def _string_list(value, maximum):
    if (not isinstance(value, list) or len(value) > maximum
            or any(not isinstance(item, str) or not item for item in value)
            or len(set(value)) != len(value)):
        return None
    return list(value)


def load_production_normalizer(source_path: Path):
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    wanted = {"_try_normalize_evaluation_model"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source_path), "exec"), namespace)
    return namespace["_try_normalize_evaluation_model"]


def diagnostic_normalize(value, all_ids, deterministic_ids, integrity_ids, candidate_ids, weights):
    """Return ``(reason, normalized)`` with production branch ordering."""
    del all_ids, deterministic_ids, integrity_ids
    if (not isinstance(value, dict) or len(value) != len(EXPECTED)
            or tuple(sorted(value)) != tuple(sorted(EXPECTED))):
        return "TOP_LEVEL_SHAPE", None
    if value["confidence"] not in ("HIGH", "MEDIUM", "LOW"):
        return "CONFIDENCE_INVALID", None
    rows = value["classifications"]
    if not isinstance(rows, list) or len(rows) != len(candidate_ids):
        return "CLASSIFICATIONS_SHAPE", None
    by_id = {}
    for row in rows:
        if (not isinstance(row, dict) or len(row) != len(ROW_KEYS)
                or tuple(sorted(row)) != ROW_KEYS):
            return "CLASSIFICATION_OBJECT_SHAPE", None
        bid_id = row["bid_id"]
        if (not isinstance(bid_id, str) or not bid_id or bid_id in by_id
                or bid_id not in candidate_ids):
            return "CLASSIFICATION_BID_INVALID", None
        if not isinstance(row["mandatory_requirements_pass"], bool):
            return "MANDATORY_FLAG_INVALID", None
        for name, limit in zip(
            ("technical", "delivery", "price", "capability", "support"), weights,
        ):
            score = row[name]
            if not isinstance(score, int) or isinstance(score, bool):
                return "SCORE_NOT_INTEGER", None
            if score < 0 or score > limit:
                return "SCORE_BOUND", None
        by_id[bid_id] = {
            "bid_id": bid_id,
            "mandatory_requirements_pass": row["mandatory_requirements_pass"],
            "technical": row["technical"], "delivery": row["delivery"],
            "price": row["price"], "capability": row["capability"],
            "support": row["support"],
        }
    if set(by_id) != set(candidate_ids):
        return "CANDIDATE_COVERAGE", None
    return None, {
        "classifications": [by_id[bid_id] for bid_id in sorted(by_id)],
        "confidence": value["confidence"],
    }


def base_result(ids):
    a, b, c, _, _ = ids
    return {
        "classifications": [
            {"bid_id": a, "mandatory_requirements_pass": True,
             "technical": 30, "delivery": 18, "price": 17,
             "capability": 14, "support": 9},
            {"bid_id": b, "mandatory_requirements_pass": True,
             "technical": 28, "delivery": 17, "price": 15,
             "capability": 13, "support": 8},
            {"bid_id": c, "mandatory_requirements_pass": True,
             "technical": 34, "delivery": 19, "price": 19,
             "capability": 15, "support": 10},
        ],
        "confidence": "HIGH",
    }


def mutation_corpus(ids, count=12000):
    base = base_result(ids)
    cases = [copy.deepcopy(base)]

    def add(mutator):
        value = copy.deepcopy(base)
        mutator(value)
        cases.append(value)

    add(lambda x: x.pop("confidence"))
    add(lambda x: x.update({"extra": True}))
    add(lambda x: x.update({"confidence": "certain"}))
    add(lambda x: x.update({"classifications": []}))
    add(lambda x: x["classifications"].append(copy.deepcopy(x["classifications"][0])))
    add(lambda x: x["classifications"].__setitem__(0, {"bid_id": ids[0]}))
    add(lambda x: x["classifications"][0].update({"bid_id": ids[3]}))
    add(lambda x: x["classifications"][0].update({"mandatory_requirements_pass": "true"}))
    add(lambda x: x["classifications"][0].update({"technical": 35.0}))
    add(lambda x: x["classifications"][0].update({"technical": 36}))
    add(lambda x: x["classifications"][0].update({"technical": -1}))
    add(lambda x: x["classifications"][0].update({"extra": 1}))
    add(lambda x: x["classifications"].__setitem__(0, {
        **x["classifications"][0], "bid_id": ids[0],
    }))

    randomizer = random.Random(20260815)
    for _ in range(count - len(cases)):
        value = copy.deepcopy(base)
        choice = randomizer.randrange(10)
        if choice == 0:
            value.pop(randomizer.choice(["classifications", "confidence"]), None)
        elif choice == 1:
            value["extra"] = True
        elif choice == 2:
            value["confidence"] = randomizer.choice([None, "certain", 7])
        else:
            row = value["classifications"][randomizer.randrange(3)]
            field = randomizer.choice(list(row))
            if choice == 3:
                row[field] = None
            elif choice == 4:
                row[field] = "invalid"
            elif choice == 5:
                row["bid_id"] = randomizer.choice(ids)
            elif choice == 6:
                row["mandatory_requirements_pass"] = randomizer.choice([0, 1, "true"])
            elif choice == 7:
                row[randomizer.choice(["technical", "delivery", "price", "capability", "support"])] = 101
            elif choice == 8:
                row[randomizer.choice(["technical", "delivery", "price", "capability", "support"])] = -1
            else:
                row["extra"] = True
        cases.append(value)
    return cases


def run_equivalence(source_path: Path):
    production = load_production_normalizer(source_path)
    ids = [
        "analytics-dashboard-2026-final-v2-bid-a",
        "analytics-dashboard-2026-final-v2-bid-b",
        "analytics-dashboard-2026-final-v2-bid-c",
        "analytics-dashboard-2026-final-v2-bid-d",
        "analytics-dashboard-2026-final-v2-bid-e",
    ]
    context = (ids, [ids[3], ids[4]], [], ids[:3], [35, 20, 20, 15, 10])
    corpus = mutation_corpus(ids)
    mismatches = []
    reason_counts = {}
    accepted = 0
    for index, value in enumerate(corpus):
        try:
            production_result = production(value, *context)
            production_accepts = production_result is not None
        except Exception:
            production_result = None
            production_accepts = False
        reason, diagnostic_result = diagnostic_normalize(value, *context)
        diagnostic_accepts = reason is None
        reason_counts[reason or "ACCEPTED"] = reason_counts.get(reason or "ACCEPTED", 0) + 1
        accepted += int(production_accepts)
        if production_accepts != diagnostic_accepts:
            mismatches.append({"index": index, "production": production_accepts, "diagnostic": reason})
        elif production_accepts and production_result != diagnostic_result:
            mismatches.append({"index": index, "production": "canonical-mismatch", "diagnostic": "accepted"})
    return {
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "corpus_size": len(corpus), "production_accepted": accepted,
        "diagnostic_reason_counts": dict(sorted(reason_counts.items())),
        "equivalent": not mismatches, "mismatches": mismatches[:5],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    result = run_equivalence(args.source)
    print(json.dumps(result, sort_keys=True, indent=2))
    if not result["equivalent"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
