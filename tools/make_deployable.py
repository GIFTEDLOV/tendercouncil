"""Generate the deterministic deployable source artifact from a contract."""

from __future__ import annotations

import argparse
import ast
import io
import tokenize


LEGACY_COMPACT_SHA256_REFERENCE = r'''def _sha256_hex(data: bytes) -> str:
    k=tuple(int(x,16) for x in "428a2f98 71374491 b5c0fbcf e9b5dba5 3956c25b 59f111f1 923f82a4 ab1c5ed5 d807aa98 12835b01 243185be 550c7dc3 72be5d74 80deb1fe 9bdc06a7 c19bf174 e49b69c1 efbe4786 0fc19dc6 240ca1cc 2de92c6f 4a7484aa 5cb0a9dc 76f988da 983e5152 a831c66d b00327c8 bf597fc7 c6e00bf3 d5a79147 06ca6351 14292967 27b70a85 2e1b2138 4d2c6dfc 53380d13 650a7354 766a0abb 81c2c92e 92722c85 a2bfe8a1 a81a664b c24b8b70 c76c51a3 d192e819 d6990624 f40e3585 106aa070 19a4c116 1e376c08 2748774c 34b0bcb5 391c0cb3 4ed8aa4a 5b9cca4f 682e6ff3 748f82ee 78a5636f 84c87814 8cc70208 90befffa a4506ceb bef9a3f7 c67178f2".split())
    h=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
    n=len(data);data+=b"\x80"+b"\0"*((55-n)%64)+(n*8).to_bytes(8,"big")
    for o in range(0,len(data),64):
        w=[int.from_bytes(data[i:i+4],"big") for i in range(o,o+64,4)]
        for i in range(16,64):
            x=w[i-15];y=w[i-2];w.append((w[i-16]+(_rotate_right(x,7)^_rotate_right(x,18)^x>>3)+w[i-7]+(_rotate_right(y,17)^_rotate_right(y,19)^y>>10))&0xffffffff)
        a,b,c,d,e,f,g,z=h
        for i in range(64):
            s=_rotate_right(e,6)^_rotate_right(e,11)^_rotate_right(e,25);t=(z+s+((e&f)^((~e)&g))+k[i]+w[i])&0xffffffff;s=_rotate_right(a,2)^_rotate_right(a,13)^_rotate_right(a,22);u=(s+((a&b)^(a&c)^(b&c)))&0xffffffff;z,g,f,e,d,c,b,a=g,f,e,(d+t)&0xffffffff,c,b,a,(t+u)&0xffffffff
        h=[(h[0]+a)&0xffffffff,(h[1]+b)&0xffffffff,(h[2]+c)&0xffffffff,(h[3]+d)&0xffffffff,(h[4]+e)&0xffffffff,(h[5]+f)&0xffffffff,(h[6]+g)&0xffffffff,(h[7]+z)&0xffffffff]
    return "".join(f"{x:08x}" for x in h)
'''

# The canonical source already imports hashlib. Keep the generated artifact
# aligned with the proven pinned native implementation instead of carrying a
# second cryptographic implementation into deployment payloads.
COMPACT_SHA256 = r'''def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
'''

from pathlib import Path


class StripDocstrings(ast.NodeTransformer):
    def _strip(self, node):
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(getattr(node.body[0], "value", None), ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:]
        return self.generic_visit(node)

    visit_Module = _strip
    visit_ClassDef = _strip
    visit_FunctionDef = _strip
    visit_AsyncFunctionDef = _strip


class CompactIdentifiers(ast.NodeTransformer):
    """Alpha-rename deployment-internal symbols without changing the ABI."""

    LOCAL_NAMES = (
        "tender", "result", "value", "challenge", "bid", "payload",
        "failure", "item", "score", "ordered", "valid", "field", "kind",
        "amount", "now", "rows", "keys", "expected", "required",
        "leader_fn", "validator_fn", "values", "name", "payout",
    )
    LOCAL_REPLACEMENTS = tuple("trvcbpfiqoxzkanywedljghm")

    @staticmethod
    def _short(index: int) -> str:
        """Return A..Z, AA..AZ, BA.. for module-internal globals."""
        result = ""
        while True:
            result = chr(65 + index % 26) + result
            index = index // 26 - 1
            if index < 0:
                return result

    def __init__(self, tree: ast.Module):
        self.names = dict(zip(self.LOCAL_NAMES, self.LOCAL_REPLACEMENTS))
        constants = []
        helpers = []
        private_methods = []
        interfaces = []
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                constants.extend(
                    target.id for target in targets
                    if isinstance(target, ast.Name) and target.id.isupper()
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                helpers.append(node.name)
            elif isinstance(node, ast.ClassDef):
                if node.name in ("EvaluatorInterface", "CoreInterface", "Recipient"):
                    interfaces.append(node.name)
                for child in node.body:
                    if (isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and child.name.startswith("_")
                            and child.name != "__init__"):
                        private_methods.append(child.name)
        globals_to_compact = constants + helpers + interfaces
        self.names.update({
            name: self._short(index)
            for index, name in enumerate(globals_to_compact)
        })
        private_name_map = {
            name: chr(97 + index) if index < 26 else "m" + str(index)
            for index, name in enumerate(private_methods)
        }
        self.names.update(private_name_map)
        self.attributes = private_name_map

    def visit_Name(self, node: ast.Name):
        node.id = self.names.get(node.id, node.id)
        return node

    def visit_arg(self, node: ast.arg):
        node.arg = self.names.get(node.arg, node.arg)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        node.name = self.names.get(node.name, node.name)
        return self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef):
        node.name = self.names.get(node.name, node.name)
        return self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        node.attr = self.attributes.get(node.attr, node.attr)
        return self.generic_visit(node)


class ShareUserError(ast.NodeTransformer):
    """Use one generated helper for the repeated UserError constructor path."""

    @staticmethod
    def _is_user_error(node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Attribute) and node.attr == "UserError"
            and isinstance(node.value, ast.Attribute) and node.value.attr == "vm"
            and isinstance(node.value.value, ast.Name) and node.value.value.id == "gl"
        )

    def visit_Call(self, node: ast.Call):
        node = self.generic_visit(node)
        if self._is_user_error(node.func):
            node.func = ast.Name(id="_user_error", ctx=ast.Load())
        return node


def make_deployable(source: bytes) -> bytes:
    text = source.decode("utf-8")
    lines = text.splitlines()
    header = lines[0] if lines and lines[0].startswith("# {") else ""
    tree = ast.parse(text)
    tree = StripDocstrings().visit(tree)
    compact_sha = ast.parse(COMPACT_SHA256).body[0]
    for index, node in enumerate(tree.body):
        if isinstance(node, ast.FunctionDef) and node.name == "_sha256_hex":
            tree.body[index] = compact_sha
            break
    tree = ShareUserError().visit(tree)
    tree.body.append(ast.parse(
        "def _user_error(message: str):\n"
        "    return gl.vm.UserError(message)\n"
    ).body[0])
    tree = CompactIdentifiers(tree).visit(tree)
    ast.fix_missing_locations(tree)
    body = ast.unparse(tree)
    tokens = tokenize.generate_tokens(io.StringIO(body).readline)
    output = []
    previous = None
    indent_stack = [""]
    at_line_start = True
    for token in tokens:
        if token.type in (tokenize.ENCODING, tokenize.ENDMARKER):
            continue
        if token.type == tokenize.INDENT:
            indent_stack.append(token.string)
            continue
        if token.type == tokenize.DEDENT:
            indent_stack.pop()
            continue
        if token.type == tokenize.NEWLINE:
            output.append("\n")
            previous = None
            at_line_start = True
            continue
        if token.type in (tokenize.NL, tokenize.COMMENT):
            continue
        if at_line_start:
            output.append(indent_stack[-1])
            at_line_start = False
        needs_space = (
            previous is not None
            and previous.type in (tokenize.NAME, tokenize.NUMBER, tokenize.STRING)
            and token.type in (tokenize.NAME, tokenize.NUMBER, tokenize.STRING)
        )
        if needs_space:
            output.append(" ")
        output.append(token.string)
        previous = token
    minified = "".join(output).strip() + "\n"
    return (((header + "\n") if header else "") + minified).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    generated = make_deployable(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(generated)
    print(f"deployable_bytes={len(generated)}")


if __name__ == "__main__":
    main()
