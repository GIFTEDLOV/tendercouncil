"""Reject cross-contract emits that are not explicitly finalized-only."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def check(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    emits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "emit":
            continue
        mode = next((item.value for item in node.keywords if item.arg == "on"), None)
        if not isinstance(mode, ast.Constant) or mode.value != "finalized":
            raise SystemExit(f"{path}: emit at line {node.lineno} is not finalized-only")
        emits.append(node.lineno)
    if not emits:
        raise SystemExit(f"{path}: no cross-contract emit sites found")
    print(f"{path}: {len(emits)} finalized-only emit sites")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_finalized_messages.py CONTRACT.py")
    raise SystemExit(check(Path(sys.argv[1])))
