"""Run bounded source mutants and require the direct security suite to catch them."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path("contracts/tender_council_production.py")
TEST = "tests/direct/test_production_foundation.py"

MUTATIONS = (
    (
        "budget-bypass",
        "bid.price <= tender.max_budget",
        "True",
        "hard_commercial_constraints",
    ),
    (
        "delivery-bypass",
        "bid.delivery_days <= tender.max_delivery_days",
        "True",
        "hard_commercial_constraints",
    ),
    (
        "support-bypass",
        "bid.support_days >= tender.min_support_days",
        "True",
        "hard_commercial_constraints",
    ),
    (
        "hash-verification-bypass",
        "if len(raw_body) > MAX_MANIFEST_BYTES:\n        return _manifest_failure(MANIFEST_SCHEMA_INVALID)\n    if \"sha256:\" + _sha256_hex(raw_body) != committed_hash:",
        "if False:",
        "manifest_hash_mismatch",
    ),
    (
        "response-window-bypass",
        "if self._now_seconds() <= tender.response_deadline:",
        "if False:",
        "provisional_award_requires_response_window",
    ),
    (
        "challenge-evidence-injection",
        "if not found_evidence:",
        "if False:",
        "only_authenticated_bidder_can_submit_one_committed_evidence_challenge",
    ),
    (
        "duplicate-payout-bypass",
        "if (tender.status == STATUS_SETTLEMENT_PENDING\n                and tender.settlement_state == SETTLEMENT_TRANSFER_PENDING):",
        "if False:",
        "settlement_is_separate_from_award_and_replay_protected",
    ),
)


def run_mutant(name: str, needle: str, replacement: str, selector: str) -> None:
    with tempfile.TemporaryDirectory(prefix="tendercouncil-mutant-") as raw_dir:
        mutant_root = Path(raw_dir)
        shutil.copytree(
            ROOT,
            mutant_root,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "artifacts", "__pycache__"),
        )
        source_path = mutant_root / CONTRACT
        source = source_path.read_text(encoding="utf-8")
        if source.count(needle) != 1:
            raise RuntimeError(f"{name}: expected one mutation target")
        source_path.write_text(source.replace(needle, replacement), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", TEST, "-k", selector],
            cwd=mutant_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            raise RuntimeError(f"{name}: mutant survived\n{result.stdout}")
        print(f"caught {name}")


def main() -> None:
    if "def award_bid" in (ROOT / CONTRACT).read_text(encoding="utf-8"):
        raise RuntimeError("manual award bypass exists in production contract")
    for mutation in MUTATIONS:
        run_mutant(*mutation)
    print(f"caught {len(MUTATIONS)} security mutants")


if __name__ == "__main__":
    main()
