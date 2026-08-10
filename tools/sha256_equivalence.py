"""Compare TenderCouncil's former pure SHA-256 routine with hashlib vectors."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "contracts" / "tender_council_production.py"
REFERENCE_COMMIT = "230ecd0fd2df0249f3b251d8f489bf225129210c"
OUTPUT = ROOT / "artifacts" / "sha256-equivalence.json"


def main() -> None:
    reference = subprocess.run(
        [
            "git",
            "-c",
            "safe.directory=C:/Users/DELL/tendercouncil",
            "show",
            f"{REFERENCE_COMMIT}:contracts/tender_council_production.py",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    tree = ast.parse(reference)
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"_rotate_right", "_sha256_hex"}
    ]
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), "exec"), namespace)
    pure = namespace["_sha256_hex"]
    vectors = [
        ("empty", b""),
        ("short", b"abc"),
        ("utf8", "TenderCouncil exact bytes ✓".encode("utf-8")),
        ("binary", bytes(range(256))),
        ("multi_block", (b"GenLayer exact-byte probe" * 257) + b"!"),
    ]
    results = []
    for name, value in vectors:
        pure_digest = pure(value)
        native_digest = hashlib.sha256(value).hexdigest()
        results.append(
            {
                "name": name,
                "bytes": len(value),
                "pure_sha256": pure_digest,
                "hashlib_sha256": native_digest,
                "equal": pure_digest == native_digest,
            }
        )
    output = {
        "method": "AST-extracted former production pure-Python SHA-256 vs hashlib.sha256",
        "source": str(SOURCE.relative_to(ROOT)),
        "reference_commit": REFERENCE_COMMIT,
        "vectors": results,
        "all_equal": all(item["equal"] for item in results),
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    if not output["all_equal"]:
        raise SystemExit("SHA-256 equivalence failure")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
