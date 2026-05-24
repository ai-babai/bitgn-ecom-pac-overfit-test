#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {
    "file": 350,
    "function": 60,
}


def code_lines(path: Path) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith("//"):
            out.append((n, line))
    return out


def rust_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.rs")
        if "vendor" not in path.parts and "target" not in path.parts
    )


def check_file(path: Path) -> list[str]:
    lines = code_lines(path)
    if len(lines) <= LIMITS["file"]:
        return []
    return [f"{path.relative_to(ROOT)} has {len(lines)} code lines > {LIMITS['file']}"]


def check_functions(path: Path) -> list[str]:
    issues: list[str] = []
    active: tuple[int, int] | None = None
    depth = 0
    for n, line in code_lines(path):
        stripped = line.strip()
        if active is None and (stripped.startswith("fn ") or stripped.startswith("pub fn ")):
            active = (n, 0)
            depth = 0
        if active is not None:
            depth += line.count("{") - line.count("}")
            start, count = active
            active = (start, count + 1)
            if depth <= 0:
                if active[1] > LIMITS["function"]:
                    rel = path.relative_to(ROOT)
                    issues.append(f"{rel}:{start} function has {active[1]} code lines > {LIMITS['function']}")
                active = None
    return issues


def main() -> int:
    issues: list[str] = []
    for path in rust_files():
        issues.extend(check_file(path))
        issues.extend(check_functions(path))
    if issues:
        print("\n".join(issues), file=sys.stderr)
        return 1
    print("code limits ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
