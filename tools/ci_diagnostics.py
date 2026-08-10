"""Print and, in CI, resolve TenderCouncil's pinned test toolchain."""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "tender_council.py"
DIRECT_GENVM_VERSION = os.environ.get("TENDERCOUNCIL_DIRECT_GENVM_VERSION", "v0.2.16")


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "NOT_INSTALLED"


def print_diagnostics() -> None:
    from gltest.direct.sdk_loader import parse_contract_header

    dependencies = parse_contract_header(CONTRACT)
    print(f"python_version={platform.python_version()}")
    print(f"python_implementation={platform.python_implementation()}")
    print(f"genlayer_test_version={package_version('genlayer-test')}")
    print(f"genlayer_py_version={package_version('genlayer-py')}")
    print(f"genvm_linter_version={package_version('genvm-linter')}")
    print(f"pytest_version={package_version('pytest')}")
    print(f"cloudpickle_version={package_version('cloudpickle')}")
    print(f"contract_runner_header={dependencies.get('py-genlayer', 'MISSING')}")
    print(f"direct_genvm_requested_version={DIRECT_GENVM_VERSION}")


def resolve_direct_runtime() -> None:
    from gltest.direct.sdk_loader import setup_sdk_paths

    paths = setup_sdk_paths(CONTRACT, version=DIRECT_GENVM_VERSION)
    runner_path = next((path for path in paths if path.name == "py-genlayer"), paths[0])
    runner_hash = runner_path.name
    if runner_hash == "py-genlayer":
        runner_hash = runner_path.parent.name
    runner_manifest = runner_path / "runner.json"
    if not runner_manifest.exists():
        raise RuntimeError(f"resolved runner manifest missing: {runner_manifest}")
    print(f"resolved_genvm_direct_version={DIRECT_GENVM_VERSION}")
    print(f"resolved_genvm_runner_hash={runner_hash}")
    print(f"resolved_genvm_runner_manifest={runner_manifest}")
    print("resolved_genvm_direct_runtime=READY")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolve", action="store_true")
    args = parser.parse_args()
    print_diagnostics()
    if args.resolve:
        resolve_direct_runtime()


if __name__ == "__main__":
    main()
