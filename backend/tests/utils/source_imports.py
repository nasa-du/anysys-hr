"""Helpers for architecture tests that inspect module imports."""

import ast
from pathlib import Path
from types import ModuleType


def imported_modules(module: ModuleType) -> set[str]:
    """Return the module names imported by ``module``'s source file."""
    path = Path(module.__file__ or "")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    return imported
