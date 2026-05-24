#!/usr/bin/env python3
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"file": 750, "function": 80}
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", "reference", "runs", "target"}


def python_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.py")
        if not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
    )


def code_lines(path: Path) -> list[str]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(line)
    return lines


def check_file(path: Path) -> list[str]:
    count = len(code_lines(path))
    if count <= LIMITS["file"]:
        return []
    rel = path.relative_to(ROOT)
    return [f"{rel} has {count} code lines > {LIMITS['file']}"]


def check_functions(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    issues = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.end_lineno is None:
            continue
        length = node.end_lineno - node.lineno + 1
        if length > LIMITS["function"]:
            rel = path.relative_to(ROOT)
            issues.append(f"{rel}:{node.lineno} function {node.name} has {length} lines > {LIMITS['function']}")
    return issues


def main() -> int:
    issues: list[str] = []
    for path in python_files():
        issues.extend(check_file(path))
        issues.extend(check_functions(path))
    if issues:
        print("\n".join(issues), file=sys.stderr)
        return 1
    print("code limits ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
