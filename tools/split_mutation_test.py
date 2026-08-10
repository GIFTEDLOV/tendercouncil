"""Run executable Core/Evaluator mutants against direct and multi-contract probes."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIRECT_MUTATIONS = (
    (
        "core-evaluator-rebinding",
        "if self.evaluator_bound:\n            raise gl.vm.UserError(\"evaluator is already permanently bound\")",
        "if False:",
        "core_is_unconfigured",
        "core",
    ),
    (
        "core-callback-caller-authentication",
        "if gl.message.sender_address != self.evaluator_address:\n            raise gl.vm.UserError(\"caller is not the bound evaluator\")\n        tender = self._tender(tender_id)\n        if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:",
        "if False:\n            pass\n        tender = self._tender(tender_id)\n        if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:",
        "evaluation_is_locked",
        "core",
    ),
    (
        "evaluator-core-caller-authentication",
        "def _require_core(self):\n        if gl.message.sender_address != self.core_address:\n            raise gl.vm.UserError(\"only the bound Core may call evaluator\")",
        "def _require_core(self):\n        if False:\n            raise gl.vm.UserError(\"only the bound Core may call evaluator\")",
        "evaluator_rejects_non_core",
        "evaluator",
    ),
)

RUNTIME_MUTATIONS = (
    (
        "evaluator-caller-authentication-runtime",
        "if gl.message.sender_address != self.evaluator_address:\n            raise gl.vm.UserError(\"caller is not the bound evaluator\")\n        tender = self._tender(tender_id)\n        if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:",
        "if False:\n            pass\n        tender = self._tender(tender_id)\n        if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:",
        "caller",
        "core",
    ),
    (
        "snapshot-digest-validation-runtime",
        "if snapshot_digest != tender.closed_snapshot_digest:",
        "if False:",
        "snapshot",
        "core",
    ),
    (
        "evaluation-nonce-validation-runtime",
        "if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:",
        "if tender.status != STATUS_EVALUATING:",
        "nonce",
        "core",
    ),
    (
        "duplicate-evaluation-callback-runtime",
        "if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:",
        "if tender.evaluation_nonce != nonce:",
        "duplicate",
        "core",
    ),
    (
        "stale-lifecycle-callback-runtime",
        "if tender.status != STATUS_EVALUATING or tender.evaluation_nonce != nonce:",
        "if False:",
        "lifecycle",
        "core",
    ),
    (
        "result-digest-validation-runtime",
        "if _sha256(payload) != result_digest:\n            raise gl.vm.UserError(\"evaluation result digest mismatch\")\n        result = json.loads(payload)\n        if result.get(\"winner_bid_id\", \"\") != winner_bid_id:",
        "if False:\n            pass\n        result = json.loads(payload)\n        if result.get(\"winner_bid_id\", \"\") != winner_bid_id:",
        "result-digest",
        "core",
    ),
    (
        "review-nonce-challenge-correlation-runtime",
        "if (snapshot_digest != tender.closed_snapshot_digest\n                or original_result_digest != tender.evaluation_result_digest\n                or challenge_set_digest != tender.challenge_set_digest):",
        "if False:",
        "review-correlation",
        "core",
    ),
)


def _copy_fixture(mutant_root: Path, relative: str) -> None:
    destination = mutant_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / relative, destination)


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, env=env)


def run_direct_mutant(name, needle, replacement, selector, component):
    raw_dir = tempfile.mkdtemp(prefix="tendercouncil-split-mutant-", dir=ROOT)
    try:
        mutant_root = Path(raw_dir)
        for relative in (
            "pyproject.toml", "gltest.config.yaml", "tests/__init__.py",
            "tests/direct/__init__.py", "tests/direct/test_split_contracts.py",
            "contracts/__init__.py", "contracts/tender_council_core.py",
            "contracts/tender_council_evaluator.py",
        ):
            _copy_fixture(mutant_root, relative)
        path = mutant_root / ("contracts/tender_council_evaluator.py" if component == "evaluator" else "contracts/tender_council_core.py")
        source = path.read_text(encoding="utf-8")
        if source.count(needle) != 1:
            raise RuntimeError(f"{name}: mutation target count is {source.count(needle)}")
        path.write_text(source.replace(needle, replacement), encoding="utf-8")
        result = _run([sys.executable, "-m", "pytest", "-q", "tests/direct/test_split_contracts.py", "-k", selector], mutant_root)
        if result.returncode == 0:
            raise RuntimeError(f"{name}: mutant survived\n{result.stdout}\n{result.stderr}")
        print(f"caught {name}")
    finally:
        shutil.rmtree(raw_dir, ignore_errors=True)


def run_runtime_mutant(name, needle, replacement, control, component):
    raw_dir = tempfile.mkdtemp(prefix="tendercouncil-split-runtime-mutant-", dir=ROOT)
    try:
        mutant_root = Path(raw_dir)
        for relative in (
            "contracts/tender_council_core.py", "contracts/tender_council_evaluator.py",
            "tests/fixtures/split_fake_evaluator.py", "tests/split_runtime_probe.py",
        ):
            _copy_fixture(mutant_root, relative)
        path = mutant_root / ("contracts/tender_council_evaluator.py" if component == "evaluator" else "contracts/tender_council_core.py")
        source = path.read_text(encoding="utf-8")
        if source.count(needle) != 1:
            raise RuntimeError(f"{name}: mutation target count is {source.count(needle)}")
        path.write_text(source.replace(needle, replacement), encoding="utf-8")
        result = _run([
            sys.executable, "tests/split_runtime_probe.py", "--core",
            "contracts/tender_council_core.py", "--fake",
            "tests/fixtures/split_fake_evaluator.py", "--control", control,
        ], mutant_root)
        if result.returncode == 0:
            raise RuntimeError(f"{name}: mutant survived\n{result.stdout}\n{result.stderr}")
        print(f"caught {name}")
    finally:
        shutil.rmtree(raw_dir, ignore_errors=True)


def run_finality_mutant():
    raw_dir = tempfile.mkdtemp(prefix="tendercouncil-split-finality-mutant-", dir=ROOT)
    try:
        mutant_root = Path(raw_dir)
        for relative in ("contracts/tender_council_core.py", "contracts/tender_council_evaluator.py", "tools/check_finalized_messages.py"):
            _copy_fixture(mutant_root, relative)
        for filename in ("tender_council_core.py", "tender_council_evaluator.py"):
            path = mutant_root / "contracts" / filename
            source = path.read_text(encoding="utf-8")
            if source.count('emit(on="finalized")') == 0:
                raise RuntimeError("finalized-message mutant target missing")
            path.write_text(source.replace('emit(on="finalized")', 'emit(on="accepted")'), encoding="utf-8")
        result = _run([sys.executable, "tools/check_finalized_messages.py", "contracts/tender_council_core.py"], mutant_root)
        evaluator_result = _run([sys.executable, "tools/check_finalized_messages.py", "contracts/tender_council_evaluator.py"], mutant_root)
        if result.returncode == 0 or evaluator_result.returncode == 0:
            raise RuntimeError("finalized-message mutant survived")
        print("caught finalized-message-requirement")
    finally:
        shutil.rmtree(raw_dir, ignore_errors=True)


def main():
    for mutation in DIRECT_MUTATIONS:
        run_direct_mutant(*mutation)
    for mutation in RUNTIME_MUTATIONS:
        run_runtime_mutant(*mutation)
    run_finality_mutant()
    print(f"caught {len(DIRECT_MUTATIONS) + len(RUNTIME_MUTATIONS) + 1} split mutants")


if __name__ == "__main__":
    main()
