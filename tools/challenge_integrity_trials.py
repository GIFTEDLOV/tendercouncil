"""Execute the evaluator's exact-byte challenge states without network access."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path


def load_validator(source: Path):
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    wanted = {"_hash_bytes", "_validate_external_challenge", "_resolve_external_challenge", "_deterministic_uphold_review"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    namespace = {"json": json, "hashlib": hashlib, "MAX_CLAIMS": 6000}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_validate_external_challenge"], namespace["_resolve_external_challenge"], namespace["_deterministic_uphold_review"]


def run(source: Path) -> None:
    validate, resolve, uphold = load_validator(source)
    challenge = {
        "challenge_id": "c1", "challenger": "0x" + "11" * 20,
        "reason_code": "RUBRIC_MISAPPLIED", "target_bid_id": "bid-b",
        "referenced_evidence_id": "", "tender_id": "t1",
        "challenge_sha256": "", "challenge_url": "https://fixture/challenge.json",
    }
    body = json.dumps({
        "schema_version": "tendercouncil.challenge.v1", "challenge_id": "c1",
        "tender_id": "t1", "challenger": challenge["challenger"],
        "reason_code": challenge["reason_code"], "target_bid_id": "bid-b",
        "referenced_evidence_id": "", "claim": "The rubric was misapplied.",
    }, sort_keys=True, separators=(",", ":")).encode()
    challenge["challenge_sha256"] = "sha256:" + hashlib.sha256(body).hexdigest()
    if validate(body, challenge) != ("VALID", "The rubric was misapplied."):
        raise SystemExit("valid challenge was not admitted")
    if validate(body + b" changed", challenge)[0] != "HASH_MISMATCH":
        raise SystemExit("mutated challenge was not rejected as HASH_MISMATCH")
    malformed = json.dumps({"schema_version": "fake", "challenge_id": "c1"}, separators=(",", ":")).encode()
    bad = dict(challenge)
    bad["challenge_sha256"] = "sha256:" + hashlib.sha256(malformed).hexdigest()
    if validate(malformed, bad)[0] != "SCHEMA_INVALID":
        raise SystemExit("malformed challenge was not rejected as SCHEMA_INVALID")
    if resolve(("UNAVAILABLE", b""), challenge)[0] != "UNAVAILABLE":
        raise SystemExit("unavailable challenge was not classified as UNAVAILABLE")
    invalid_states = ["UNAVAILABLE", "HASH_MISMATCH", "SCHEMA_INVALID"]
    for state in invalid_states:
        result = uphold("bid-b", ["c1:" + state])
        if result["decision"] != "UPHOLD" or result["winner_bid_id"] != "bid-b":
            raise SystemExit("invalid challenge state overturned the original award")
    print("challenge integrity trials: PASS (VALID, UNAVAILABLE, HASH_MISMATCH, SCHEMA_INVALID, deterministic invalid-state UPHOLD)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("contracts/tender_council_evaluator.py"))
    args = parser.parse_args()
    run(args.source)


if __name__ == "__main__":
    main()
