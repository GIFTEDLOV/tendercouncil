"""Fail-closed parity and conservative outer deployment-size check."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.make_deployable import make_deployable

ROOT = Path(__file__).resolve().parents[1]
TARGET = 40_000
OUTER_ENCODING_OVERHEAD_BOUND = 1_024


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/tender_council_split-size-budget.json")
    args = parser.parse_args()
    components = []
    for name in ("core", "evaluator"):
        source = ROOT / f"contracts/tender_council_{name}.py"
        artifact = ROOT / f"artifacts/tender_council_{name}_deployable.py"
        if artifact.read_bytes() != make_deployable(source.read_bytes()):
            raise SystemExit(f"{name}: artifact/source parity mismatch")
        artifact_bytes = artifact.stat().st_size
        conservative_outer = artifact_bytes + OUTER_ENCODING_OVERHEAD_BOUND
        components.append({
            "name": name,
            "source_bytes": source.stat().st_size,
            "artifact_bytes": artifact_bytes,
            "conservative_outer_bytes": conservative_outer,
            "target_outer_bytes": TARGET,
            "within_target": conservative_outer < TARGET,
        })
    if any(not item["within_target"] for item in components):
        raise SystemExit("split deployment size target exceeded")
    result = {
        "method": "artifact bytes plus conservative 1024-byte outer-encoding bound",
        "target_outer_bytes": TARGET,
        "measured_network_boundary": {"accepted_outer_bytes": 53316, "failed_outer_bytes": 53348},
        "components": components,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for item in components:
        print(f"{item['name']}: artifact={item['artifact_bytes']} conservative_outer={item['conservative_outer_bytes']} target={TARGET}")


if __name__ == "__main__":
    main()
