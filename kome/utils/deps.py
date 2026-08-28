"""
Dependency checking for rices.

Reads a rice's ``deps.txt`` and verifies that the listed programs
are available on the system using :func:`shutil.which`.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def parse_deps_file(path: Path) -> list[str]:
    """
    Parse a ``deps.txt`` file.

    Each non-empty line that doesn't start with ``#`` is treated as a
    program name.  Leading/trailing whitespace is stripped.
    """
    if not path.is_file():
        return []

    deps: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            deps.append(line)
    return deps


def check_dependencies(deps: list[str]) -> tuple[list[str], list[str]]:
    """
    Check which programs from *deps* are installed.

    Returns:
        A ``(found, missing)`` tuple where each element is a list of
        program names.
    """
    found: list[str] = []
    missing: list[str] = []

    for dep in deps:
        if shutil.which(dep) is not None:
            found.append(dep)
        else:
            missing.append(dep)

    return found, missing
