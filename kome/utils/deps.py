"""Dependency checking — verifies programs exist via shutil.which."""

from __future__ import annotations

import shutil
from pathlib import Path


def parse_deps_file(path: Path) -> list[str]:
    """Parse deps.txt: one program name per line, # comments ignored."""
    if not path.is_file():
        return []

    deps: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            deps.append(line)
    return deps


def check_dependencies(deps: list[str]) -> tuple[list[str], list[str]]:
    """Return (found, missing) lists for the given program names."""
    found: list[str] = []
    missing: list[str] = []

    for dep in deps:
        if shutil.which(dep) is not None:
            found.append(dep)
        else:
            missing.append(dep)

    return found, missing
