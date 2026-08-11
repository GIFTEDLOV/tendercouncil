"""Execute the Evaluator-owned original-result lookup regression probe."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Record:
    tender_id: str
    nonce: int
    result_json: str
    result_digest: str


def load(source: Path):
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_load_original_result"]
    namespace = {"json": json}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_load_original_result"]


def run(source: Path) -> None:
    load_result = load(source)
    payload = '{"winner_bid_id":"B","status":"COMPARATIVE"}'
    record = Record("t1", 1, payload, "sha256:result")
    result = load_result(record, "t1", 1, "sha256:result")
    if result["winner_bid_id"] != "B":
        raise SystemExit("Evaluator-owned result was not loaded")
    for bad in (
        (None, "t1", 1, "sha256:result"),
        (record, "wrong", 1, "sha256:result"),
        (record, "t1", 2, "sha256:result"),
        (record, "t1", 1, "sha256:wrong"),
    ):
        try:
            load_result(*bad)
        except Exception:
            continue
        raise SystemExit("mismatched original result record was accepted")
    print("review lookup trials: PASS (Evaluator-owned record and correlation guards)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("contracts/tender_council_evaluator.py"))
    args = parser.parse_args()
    run(args.source)


if __name__ == "__main__":
    main()
