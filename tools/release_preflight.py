"""Fail-closed release preflight for TenderCouncil deployment artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_FIELDS = (
    "network",
    "chain_id",
    "sender",
    "source",
    "source_sha256",
    "runner_header",
    "constructor_args",
    "schema_version",
    "fixture_hashes",
    "deployment_transport",
)


def fail(message: str) -> "NoReturn":
    raise SystemExit("release preflight failure: " + message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--network", required=True)
    parser.add_argument("--chain-id", required=True, type=int)
    parser.add_argument("--sender", required=True)
    parser.add_argument("--constructor-args", required=True)
    parser.add_argument("--schema-version", required=True)
    parser.add_argument("--deployment-transport", required=True)
    args = parser.parse_args()

    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except Exception as error:
        fail("cannot read config: " + str(error))
    if not isinstance(config, dict):
        fail("config must be a JSON object")
    missing = [field for field in REQUIRED_FIELDS if field not in config]
    if missing:
        fail("missing fields: " + ",".join(missing))

    if config["network"] != args.network:
        fail("network mismatch")
    if int(config["chain_id"]) != args.chain_id:
        fail("chain ID mismatch")
    if config["sender"].lower() != args.sender.lower():
        fail("sender mismatch")
    if config["schema_version"] != args.schema_version:
        fail("schema version mismatch")
    if config["deployment_transport"] != args.deployment_transport:
        fail("deployment transport mismatch")
    try:
        constructor_args = json.loads(args.constructor_args)
    except Exception as error:
        fail("constructor args are not valid JSON: " + str(error))
    if canonical_json(config["constructor_args"]) != canonical_json(constructor_args):
        fail("constructor/deploy args mismatch")

    source = Path(config["source"])
    if not source.is_absolute():
        source = args.config.parent / source
    if not source.is_file():
        fail("source file is missing")
    source_hash = sha256_file(source)
    expected_source_hash = str(config["source_sha256"]).lower()
    if not SHA256_RE.fullmatch(expected_source_hash) or source_hash != expected_source_hash:
        fail("source hash mismatch")

    source_text = source.read_text(encoding="utf-8")
    if config["runner_header"] not in source_text.splitlines()[:3]:
        fail("runner header is absent or mismatched")

    fixture_hashes = config["fixture_hashes"]
    if not isinstance(fixture_hashes, dict):
        fail("fixture_hashes must be an object")
    for fixture_name, expected_hash in fixture_hashes.items():
        fixture = Path(fixture_name)
        if not fixture.is_absolute():
            fixture = args.config.parent / fixture
        if not fixture.is_file():
            fail("fixture is missing: " + str(fixture_name))
        expected_hash = str(expected_hash).lower()
        if not SHA256_RE.fullmatch(expected_hash) or sha256_file(fixture) != expected_hash:
            fail("fixture hash mismatch: " + str(fixture_name))

    artifact = config.get("artifact")
    if artifact is not None:
        artifact_path = Path(artifact)
        if not artifact_path.is_absolute():
            artifact_path = args.config.parent / artifact_path
        if not artifact_path.is_file():
            fail("deployable artifact is missing")
        if artifact_path.read_bytes() != source.read_bytes():
            fail("deployable artifact/source parity mismatch")

    print("release_preflight=PASS")
    print("network=" + str(config["network"]))
    print("chain_id=" + str(config["chain_id"]))
    print("sender=" + str(config["sender"]))
    print("source_sha256=" + source_hash)
    print("runner_header=" + str(config["runner_header"]))
    print("deployment_transport=" + str(config["deployment_transport"]))


if __name__ == "__main__":
    main()
