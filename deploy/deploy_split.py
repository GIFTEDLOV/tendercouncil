"""Repeatable Core/Evaluator deployment plan.

Default mode is dry-run and writes a manifest containing source/artifact
parity, hashes, constructor arguments, and the exact ordered operations.  A
future release operator must explicitly opt into broadcasting after the
estimate gate and review gate have passed.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.make_deployable import make_deployable

ROOT = Path(__file__).resolve().parents[1]
HEADER = '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }'
COMPONENTS = (
    ("core", ROOT / "contracts/tender_council_core.py", ROOT / "artifacts/tender_council_core_deployable.py", []),
    ("evaluator", ROOT / "contracts/tender_council_evaluator.py", ROOT / "artifacts/tender_council_evaluator_deployable.py", ["<CORE_ADDRESS>", "tendercouncil.evaluator.v2"]),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def component_record(name: str, source: Path, artifact: Path, constructor_args: list[str]):
    if not source.is_file() or not artifact.is_file():
        raise SystemExit(f"missing {name} source or artifact")
    if source.read_text(encoding="utf-8").splitlines()[0] != HEADER:
        raise SystemExit(f"{name} runner header mismatch")
    if artifact.read_bytes() != make_deployable(source.read_bytes()):
        raise SystemExit(f"{name} artifact/source parity mismatch")
    return {
        "name": name,
        "source": str(source.relative_to(ROOT)),
        "artifact": str(artifact.relative_to(ROOT)),
        "source_sha256": sha256(source),
        "artifact_sha256": sha256(artifact),
        "source_bytes": source.stat().st_size,
        "artifact_bytes": artifact.stat().st_size,
        "constructor_args": constructor_args,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", default="testnet-bradbury")
    parser.add_argument("--chain-id", type=int, default=4221)
    parser.add_argument("--sender", default="0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/tender_council_split-deployment-dry-run.json")
    parser.add_argument("--broadcast", action="store_true", help="Reserved release switch; deliberately refused in this implementation task")
    args = parser.parse_args()
    if args.broadcast:
        raise SystemExit("broadcast is disabled until the reviewed two-contract gate is opened")
    records = [component_record(*component) for component in COMPONENTS]
    manifest = {
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": "DRY_RUN_NO_BROADCAST",
        "network": args.network,
        "chain_id": args.chain_id,
        "sender": args.sender,
        "ordered_steps": [
            "preflight network/chain/sender and component parity",
            "deploy Core and await finalized deployment",
            "deploy Evaluator with finalized Core address",
            "bind Evaluator once in Core and await finalized binding",
            "verify Core binding address/version/exact evaluator artifact code hash",
        ],
        "components": records,
        "binding": {
            "method": "bind_evaluator(evaluator_address, evaluator_version, evaluator_code_hash)",
            "code_hash_definition": "sha256:<exact bytes of artifacts/tender_council_evaluator_deployable.py>",
            "one_time": True,
            "core_authority": "Core bootstrapper only",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
