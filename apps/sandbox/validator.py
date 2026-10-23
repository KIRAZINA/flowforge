import ast

from .exceptions import SandboxValidationError

FORBIDDEN_MODULES = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "requests",
    "http",
    "urllib",
    "pathlib",
    "builtins",
    "importlib",
    "ctypes",
    "multiprocessing",
    "threading",
    "pickle",
    "marshal",
    "codecs",
    "io",
    "json",
}

FORBIDDEN_CALLS = {
    "open",
    "exec",
    "eval",
    "compile",
    "__import__",
    "getattr",
    "setattr",
    "delattr",
    "globals",
    "locals",
    "vars",
    "dir",
    "input",
    "breakpoint",
    "help",
}


class _AstValidator(ast.NodeVisitor):
    def visit_Import(self, node):
        raise SandboxValidationError("Forbidden: import statement")

    def visit_ImportFrom(self, node):
        raise SandboxValidationError("Forbidden: from-import statement")

    def visit_ClassDef(self, node):
        raise SandboxValidationError("Forbidden: class definition")

    def visit_AsyncFunctionDef(self, node):
        raise SandboxValidationError("Forbidden: async function definition")

    def visit_AsyncFor(self, node):
        raise SandboxValidationError("Forbidden: async for loop")

    def visit_AsyncWith(self, node):
        raise SandboxValidationError("Forbidden: async with statement")

    def visit_Global(self, node):
        raise SandboxValidationError("Forbidden: global statement")

    def visit_Nonlocal(self, node):
        raise SandboxValidationError("Forbidden: nonlocal statement")

    def visit_Attribute(self, node):
        if node.attr.startswith("__"):
            raise SandboxValidationError("Forbidden: dunder attribute access is not allowed")
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in FORBIDDEN_MODULES:
            raise SandboxValidationError(f"Forbidden module reference: {node.id}")
        if node.id in FORBIDDEN_CALLS:
            raise SandboxValidationError(f"Forbidden builtin reference: {node.id}")
        if node.id.startswith("__"):
            raise SandboxValidationError("Forbidden: dunder name access is not allowed")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            raise SandboxValidationError(f"Forbidden call: {node.func.id}")
        if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_CALLS:
            raise SandboxValidationError(f"Forbidden call: {node.func.attr}")
        self.generic_visit(node)


def validate_code(code: str) -> None:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise SandboxValidationError(f"Invalid Python syntax: {exc}") from exc
    _AstValidator().visit(tree)
