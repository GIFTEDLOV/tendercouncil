"""Verify the deterministic repository release manifest."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path, default=ROOT / "MANIFEST.sha256")
    args = parser.parse_args()
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    seen: set[str] = set()
    failures: list[str] = []
    checked = 0
    for line_number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            failures.append(f"line {line_number}: expected '<64-hex>  normalized/path'")
            continue
        expected, relative = parts
        if relative in seen:
            failures.append(f"line {line_number}: duplicate path {relative}")
            continue
        seen.add(relative)
        if ("\\" in relative or relative.startswith("/")
                or Path(relative).drive or ".." in Path(relative).parts):
            failures.append(f"line {line_number}: path is not normalized and repository-relative: {relative}")
            continue
        if any(char not in "0123456789abcdef" for char in expected.lower()):
            failures.append(f"line {line_number}: digest is not hexadecimal")
            continue
        target = ROOT / Path(relative)
        if not target.is_file():
            failures.append(f"line {line_number}: missing file {relative}")
            continue
        actual = digest(target)
        checked += 1
        if actual != expected.lower():
            failures.append(f"line {line_number}: hash mismatch {relative}: {actual}")
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print(f"MANIFEST OK: {checked} files verified from {manifest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
