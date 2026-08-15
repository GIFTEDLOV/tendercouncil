"""Kill mutations that would re-expand or weaken the v2.1 model boundary."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = "contracts/tender_council_evaluator.py"
DIRECT_TEST = "tests/direct/test_reduced_evaluation.py"

MUTATIONS = (
    (
        "trust-model-supplied-totals",
        '''        total = sum(item[name] for name in (
            "technical", "delivery", "price", "capability", "support",
        ))''',
        '''        total = item.get("total", 0)''',
        DIRECT_TEST,
    ),
    (
        "trust-model-supplied-winner",
        '    result["winner_bid_id"] = ordered[0]["bid_id"]',
        '    result["winner_bid_id"] = model.get("winner_bid_id", "")',
        DIRECT_TEST,
    ),
    (
        "omit-semantic-candidate",
        '    if not isinstance(classifications, list) or len(classifications) != len(candidate_ids):\n'
        '        return None',
        '    if not isinstance(classifications, list):\n'
        '        return None',
        DIRECT_TEST,
    ),
    (
        "ignore-semantic-fail",
        '        if not classified[bid_id]["mandatory_requirements_pass"]',
        '        if False',
        DIRECT_TEST,
    ),
    (
        "allow-score-over-rubric-bound",
        '                    or score < 0 or score > limit):',
        '                    or score < 0 or False):',
        DIRECT_TEST,
    ),
    (
        "accept-malformed-mandatory-flag",
        '                or not isinstance(item["mandatory_requirements_pass"], bool)):',
        '                or False):',
        DIRECT_TEST,
    ),
)

COMMON_TEST_FILES = (
    "pyproject.toml",
    "gltest.config.yaml",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/direct/__init__.py",
    DIRECT_TEST,
    "contracts/__init__.py",
    EVALUATOR,
)


def copy_files(root: Path, relatives: tuple[str, ...]) -> None:
    for relative in relatives:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)


@contextmanager
def mutant_directory(prefix: str):
    raw_dir = ROOT / f".{prefix}{uuid.uuid4().hex}"
    raw_dir.mkdir()
    try:
        yield raw_dir
    finally:
        shutil.rmtree(raw_dir, ignore_errors=True)


def run_direct_mutant(name: str, needle: str, replacement: str, test: str) -> None:
    with mutant_directory("tendercouncil-v21-mutant-") as raw_dir:
        mutant_root = Path(raw_dir)
        copy_files(mutant_root, COMMON_TEST_FILES)
        source_path = mutant_root / EVALUATOR
        source = source_path.read_text(encoding="utf-8")
        if source.count(needle) != 1:
            raise RuntimeError(f"{name}: mutation target count is {source.count(needle)}")
        source = source.replace(needle, replacement)
        if name == "omit-semantic-candidate":
            coverage = '    if set(by_id) != set(candidate_ids):\n        return None'
            if source.count(coverage) != 1:
                raise RuntimeError("omit-semantic-candidate: coverage target missing")
            source = source.replace(coverage, '    if False:', 1)
        source_path.write_text(source, encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", test],
            cwd=mutant_root,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if result.returncode == 0:
            raise RuntimeError(f"{name}: mutant survived\n{result.stdout}\n{result.stderr}")
        print(f"caught {name}")


def run_validator_winner_mutant() -> None:
    with mutant_directory("tendercouncil-v21-comparator-mutant-") as raw_dir:
        mutant_root = Path(raw_dir)
        copy_files(mutant_root, (EVALUATOR, "tools/equivalence_trials.py"))
        source_path = mutant_root / EVALUATOR
        source = source_path.read_text(encoding="utf-8")
        replacements = (
            ('        "status", "winner_bid_id", "runner_up_bid_id",',
             '        "status", "runner_up_bid_id",'),
            ('    if actual.get("winner_bid_id") != expected.get("winner_bid_id"):\n'
             '        return False',
             '    if False:\n        return False'),
            ('    if actual.get("runner_up_bid_id") != expected.get("runner_up_bid_id"):\n'
             '        return False',
             '    if False:\n        return False'),
            ("SCORE_TOLERANCE = 2", "SCORE_TOLERANCE = 100"),
        )
        for needle, replacement in replacements:
            if source.count(needle) != 1:
                raise RuntimeError(f"validator-winner-mismatch: target count is {source.count(needle)}")
            source = source.replace(needle, replacement, 1)
        source_path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "tools/equivalence_trials.py"],
            cwd=mutant_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            raise RuntimeError(f"validator-winner-mismatch: mutant survived\n{result.stdout}\n{result.stderr}")
        print("caught validator-winner-mismatch")


def main() -> None:
    for mutation in MUTATIONS:
        run_direct_mutant(*mutation)
    run_validator_winner_mutant()
    print(f"caught {len(MUTATIONS) + 1} v2.1 reduced-model mutants")


if __name__ == "__main__":
    main()
