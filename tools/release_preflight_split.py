"""Fail-closed preflight for the reviewed two-contract Bradbury release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.make_deployable import make_deployable

HEADER = '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }'
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PREFERRED_OUTER_TARGET = 40_000
MAX_OUTER_TARGET = 42_000
CLI_TRANSIENT = "?? deploy/01_deploy_split_bradbury.compiled.js"


def fail(message: str):
    raise SystemExit("split release preflight failure: " + message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT}", *args],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        fail("git command failed: " + result.stderr.strip())
    return result.stdout.strip()


def component(name: str):
    source = ROOT / f"contracts/tender_council_{name}.py"
    artifact = ROOT / f"artifacts/tender_council_{name}_deployable.py"
    if not source.is_file() or not artifact.is_file():
        fail(f"missing {name} source or deployable artifact")
    if source.read_text(encoding="utf-8").splitlines()[0] != HEADER:
        fail(f"{name} runner header mismatch")
    if artifact.read_bytes() != make_deployable(source.read_bytes()):
        fail(f"{name} artifact/source parity mismatch")
    if artifact.stat().st_size + 1024 >= MAX_OUTER_TARGET:
        fail(f"{name} exceeds conservative outer target")
    return {
        "name": name,
        "canonical_source": str(source.relative_to(ROOT)).replace("\\", "/"),
        "canonical_source_sha256": digest(source),
        "canonical_source_bytes": source.stat().st_size,
        "deployable_artifact": str(artifact.relative_to(ROOT)).replace("\\", "/"),
        "deployable_artifact_sha256": digest(artifact),
        "deployable_artifact_bytes": artifact.stat().st_size,
        "preferred_outer_target_bytes": PREFERRED_OUTER_TARGET,
        "conservative_outer_bytes": artifact.stat().st_size + 1024,
        "within_preferred_outer_target": artifact.stat().st_size + 1024 < PREFERRED_OUTER_TARGET,
    }


def build_manifest(network: str, chain_id: int, sender: str):
    if network != "testnet-bradbury" or chain_id != 4221:
        fail("deployment network must be testnet-bradbury / chain 4221")
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", sender):
        fail("sender must be a 20-byte hex address")
    status_lines = [line for line in git("status", "--porcelain").splitlines() if line]
    unexpected = [line for line in status_lines if line != CLI_TRANSIENT]
    if unexpected:
        fail("worktree is not clean: " + "; ".join(unexpected))
    current_head = git("rev-parse", "HEAD")
    expected_head = os.environ.get("TENDERCOUNCIL_EXPECTED_HEAD")
    if expected_head and current_head != expected_head:
        fail("HEAD differs from reviewed hardening commit")
    core = component("core")
    evaluator = component("evaluator")
    return {
        "network": network,
        "chain_id": chain_id,
        "rpc": "https://rpc-bradbury.genlayer.com",
        "sender": sender.lower(),
        "git_commit": current_head,
        "runner_header": HEADER,
        "artifact_generator": "tools/make_deployable.py",
        "artifact_generator_sha256": digest(ROOT / "tools/make_deployable.py"),
        "evaluator_schema_version": "tendercouncil.evaluator.v2",
        "components": [core, evaluator],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", default="testnet-bradbury")
    parser.add_argument("--chain-id", type=int, default=4221)
    parser.add_argument("--sender", required=True)
    args = parser.parse_args()
    print(json.dumps(build_manifest(args.network, args.chain_id, args.sender), indent=2))
    print("split_release_preflight=PASS")


if __name__ == "__main__":
    main()
