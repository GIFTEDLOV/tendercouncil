"""Run focused split-contract mutants against the direct security tests."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MUTATIONS = (
    (
        "core-evaluator-rebinding",
        "if self.evaluator_bound:\n            raise gl.vm.UserError(\"evaluator is already permanently bound\")",
        "if False:",
        "core_is_unconfigured",
    ),
    (
        "core-callback-caller-authentication",
        "if gl.message.sender_address != self.evaluator_address:\n            raise gl.vm.UserError(\"caller is not the bound evaluator\")\n        tender = self._tender(tender_id)\n        if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:",
        "if False:\n            pass\n        tender = self._tender(tender_id)\n        if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:",
        "evaluation_is_locked",
    ),
    (
        "evaluator-core-caller-authentication",
        "def _require_core(self):\n        if gl.message.sender_address != self.core_address:\n            raise gl.vm.UserError(\"only the bound Core may call evaluator\")",
        "def _require_core(self):\n        if False:\n            raise gl.vm.UserError(\"only the bound Core may call evaluator\")",
        "evaluator_rejects_non_core",
    ),
)


def run_mutant(name: str, needle: str, replacement: str, selector: str) -> None:
    raw_dir = tempfile.mkdtemp(prefix="tendercouncil-split-mutant-", dir=ROOT)
    try:
        mutant_root = Path(raw_dir)
        for relative in ("pyproject.toml", "gltest.config.yaml", "tests/__init__.py", "tests/direct/__init__.py", "tests/direct/test_split_contracts.py"):
            destination = mutant_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        for relative in ("contracts/__init__.py", "contracts/tender_council_core.py", "contracts/tender_council_evaluator.py"):
            destination = mutant_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        path = mutant_root / ("contracts/tender_council_evaluator.py" if "evaluator-core" in name else "contracts/tender_council_core.py")
        source = path.read_text(encoding="utf-8")
        if source.count(needle) != 1:
            raise RuntimeError(f"{name}: mutation target count is {source.count(needle)}")
        path.write_text(source.replace(needle, replacement), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests/direct/test_split_contracts.py", "-k", selector],
            cwd=mutant_root, capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            raise RuntimeError(f"{name}: mutant survived\n{result.stdout}")
        print(f"caught {name}")
    finally:
        shutil.rmtree(raw_dir, ignore_errors=True)


def main() -> None:
    core = (ROOT / "contracts/tender_council_core.py").read_text(encoding="utf-8")
    evaluator = (ROOT / "contracts/tender_council_evaluator.py").read_text(encoding="utf-8")
    required_guards = (
        "closed_snapshot_digest",
        "evaluator_schema_version != EVALUATOR_SCHEMA_VERSION",
        "original_result_digest != tender.evaluation_result_digest",
        "on=\"finalized\"",
    )
    for guard in required_guards:
        if guard not in core and guard not in evaluator:
            raise RuntimeError("split security guard missing: " + guard)
    if "emit_transfer" in evaluator or "award_amount" in evaluator:
        raise RuntimeError("evaluator contains custody authority")
    for mutation in MUTATIONS:
        run_mutant(*mutation)
    print(f"caught {len(MUTATIONS)} split mutants")


if __name__ == "__main__":
    main()
