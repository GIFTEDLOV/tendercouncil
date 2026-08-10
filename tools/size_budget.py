"""Produce a reproducible TenderCouncil source-size budget."""

from __future__ import annotations

import ast
import io
import json
import tokenize
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "contracts" / "tender_council_production.py"
ARTIFACT = ROOT / "artifacts" / "tender_council_production_deployable.py"
OUTPUT = ROOT / "artifacts" / "tender_council-size-budget.json"


def line_bytes(lines: list[str], start: int, end: int) -> int:
    return sum(len(line.encode("utf-8")) for line in lines[start - 1:end])


def function_ranges(tree: ast.Module) -> dict[str, tuple[int, int]]:
    result = {}

    def collect(body: list[ast.stmt], module_end: int) -> None:
        nodes = [node for node in body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
        for index, node in enumerate(nodes):
            end = nodes[index + 1].lineno - 1 if index + 1 < len(nodes) else module_end
            result[node.name] = (node.lineno, min(end, node.end_lineno or end)) if isinstance(node, ast.FunctionDef) else (node.lineno, node.end_lineno or end)
            if isinstance(node, ast.ClassDef):
                collect(node.body, node.end_lineno or end)

    collect(tree.body, getattr(tree, "end_lineno", None) or 1)
    return result


def token_bytes(source: str, token_type: int) -> int:
    stream = tokenize.generate_tokens(io.StringIO(source).readline)
    return sum(len(token.string.encode("utf-8")) for token in stream if token.type == token_type)


def all_token_bytes(source: str) -> int:
    stream = tokenize.generate_tokens(io.StringIO(source).readline)
    return sum(
        len(token.string.encode("utf-8"))
        for token in stream
        if token.type not in (tokenize.ENCODING, tokenize.ENDMARKER)
    )


def docstring_bytes(tree: ast.AST, source: str) -> int:
    total = 0
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            total += len(ast.get_source_segment(source, body[0]).encode("utf-8"))
    return total


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    ranges = function_ranges(tree)
    first_contract = next(
        node.lineno for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TenderCouncilProduction"
    )

    def span(name: str) -> tuple[int, int]:
        return ranges[name]

    regions = [
        ("protocol constants/schema constants", 17, span("_parse_rubric")[0] - 1),
        ("rubric parsing", *span("_parse_rubric")),
        ("native SHA-256 commitment", *span("_sha256_hex")),
        ("web fetch/evidence integrity", span("_manifest_failure")[0], span("_validate_evidence_body")[1]),
        ("comparative evaluator helpers", span("_normalize_comparative_result")[0], span("_validate_manifest_bytes")[0] - 1),
        ("manifest/schema validation", *span("_validate_manifest_bytes")),
        ("challenge schema/review helpers", span("_validate_challenge_body")[0], span("_normalize_challenge_review")[1]),
        ("storage dataclasses", first_contract - 85, first_contract - 2),
        ("contract views/validation", first_contract, span("create_tender")[0] - 1),
        ("tender/bid/policy writes", span("create_tender")[0], span("evaluate_tender")[0] - 1),
        ("comparative evaluation write", *span("evaluate_tender")),
        ("provisional award/challenge flow", span("begin_provisional_award")[0], span("settle_award")[0] - 1),
        ("settlement and lifecycle", span("settle_award")[0], len(lines)),
    ]
    rows = [
        {
            "component": name,
            "start_line": start,
            "end_line": end,
            "source_bytes": line_bytes(lines, start, end),
        }
        for name, start, end in regions
    ]

    prompt_lines = set()
    prompt_keywords = ("TRUSTED", "UNTRUSTED", "rubric", "Return JSON", "proposal", "evidence")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and any(
            keyword in node.value for keyword in prompt_keywords
        ):
            prompt_lines.update(range(node.lineno, node.end_lineno + 1))

    output = {
        "method": "UTF-8 source bytes by exclusive line regions; prompt bytes are union of matching AST string lines",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_bytes": len(SOURCE.read_bytes()),
        "deployable_artifact": str(ARTIFACT.relative_to(ROOT)),
        "deployable_bytes": len(ARTIFACT.read_bytes()) if ARTIFACT.is_file() else None,
        "exclusive_regions": rows,
        "prompt_text": {
            "keywords": prompt_keywords,
            "line_count": len(prompt_lines),
            "source_bytes": sum(len(lines[index - 1].encode("utf-8")) for index in prompt_lines),
        },
        "lexical_overhead": {
            "comment_token_bytes": token_bytes(source, tokenize.COMMENT),
            "string_token_bytes": token_bytes(source, tokenize.STRING),
            "docstring_token_bytes": docstring_bytes(tree, source),
            "whitespace_bytes_outside_token_text": len(SOURCE.read_bytes()) - all_token_bytes(source),
        },
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
