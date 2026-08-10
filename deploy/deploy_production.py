"""Repeatable list-based TenderCouncil production deployment wrapper.

This wrapper performs no implicit network selection or shell interpolation. It
records the exact CLI invocation metadata and raw result; release preflight
must be run before invoking it with a generated release configuration.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.make_deployable import make_deployable

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default="contracts/tender_council_production.py")
    parser.add_argument("--rpc", required=True)
    parser.add_argument("--network", required=True)
    parser.add_argument("--sender", required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = (ROOT / args.contract).resolve()
    artifact = (ROOT / args.artifact).resolve()
    if not contract.is_file():
        raise SystemExit("deployment failure: contract is missing")
    if not artifact.is_file():
        raise SystemExit("deployment failure: artifact is missing")
    if artifact.read_bytes() != make_deployable(contract.read_bytes()):
        raise SystemExit("deployment failure: artifact/source parity mismatch")

    cli = "genlayer.cmd" if os.name == "nt" else "genlayer"
    command = [
        cli,
        "deploy",
        "--contract",
        str(artifact),
        "--rpc",
        args.rpc,
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    record = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "network": args.network,
        "sender": args.sender,
        "rpc": args.rpc,
        "command": command,
        "source": str(contract),
        "artifact": str(artifact),
        "source_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if completed.returncode != 0:
        raise SystemExit("deployment failure: genlayer deploy returned non-zero")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
