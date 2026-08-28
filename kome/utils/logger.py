"""
Colored terminal output for KOME.

Uses ANSI escape codes directly — no external dependencies.
Respects NO_COLOR (https://no-color.org/) and dumb terminals.
"""

from __future__ import annotations

import os
import sys


# ---------------------------------------------------------------------------
# Color support detection
# ---------------------------------------------------------------------------

def _color_enabled() -> bool:
    """Return True when the terminal supports color output."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_COLOR = _color_enabled()


# ---------------------------------------------------------------------------
# ANSI codes
# ---------------------------------------------------------------------------

class _Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"


def _c(code: str, text: str) -> str:
    """Wrap *text* in an ANSI color code if colors are enabled."""
    if not _COLOR:
        return text
    return f"{code}{text}{_Ansi.RESET}"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def info(msg: str) -> None:
    """Print an informational message."""
    prefix = _c(_Ansi.CYAN + _Ansi.BOLD, "ℹ")
    print(f"  {prefix}  {msg}")


def success(msg: str) -> None:
    """Print a success message."""
    prefix = _c(_Ansi.GREEN + _Ansi.BOLD, "✔")
    print(f"  {prefix}  {msg}")


def warning(msg: str) -> None:
    """Print a warning message."""
    prefix = _c(_Ansi.YELLOW + _Ansi.BOLD, "⚠")
    print(f"  {prefix}  {_c(_Ansi.YELLOW, msg)}")


def error(msg: str) -> None:
    """Print an error message to stderr."""
    prefix = _c(_Ansi.RED + _Ansi.BOLD, "✖")
    print(f"  {prefix}  {_c(_Ansi.RED, msg)}", file=sys.stderr)


def header(title: str) -> None:
    """Print a styled section header."""
    line = _c(_Ansi.MAGENTA + _Ansi.BOLD, f"  ── {title} ──")
    print()
    print(line)
    print()


def dim(text: str) -> str:
    """Return dimmed text."""
    return _c(_Ansi.DIM, text)


def bold(text: str) -> str:
    """Return bold text."""
    return _c(_Ansi.BOLD, text)


def accent(text: str) -> str:
    """Return text in the accent color (cyan)."""
    return _c(_Ansi.CYAN + _Ansi.BOLD, text)


def rice_card(
    name: str,
    *,
    is_active: bool = False,
    has_preview: bool = False,
    has_reload: bool = False,
    has_deps: bool = False,
    has_mapping: bool = False,
    missing_deps: list[str] | None = None,
) -> str:
    """
    Format a single rice entry for the `list` command.

    Returns a multi-line string ready to print.
    """
    # Title line
    star = _c(_Ansi.GREEN + _Ansi.BOLD, " ★ active") if is_active else ""
    title = f"  {_c(_Ansi.BOLD, name)}{star}"

    # Feature badges
    badges: list[str] = []
    if has_reload:
        badges.append(_c(_Ansi.BLUE, "reload.sh"))
    if has_preview:
        badges.append(_c(_Ansi.MAGENTA, "preview"))
    if has_deps:
        badges.append(_c(_Ansi.CYAN, "deps.txt"))
    if has_mapping:
        badges.append(_c(_Ansi.YELLOW, "mapping.json"))

    lines = [title]
    if badges:
        lines.append(f"    {dim('┗')} {' · '.join(badges)}")
    if missing_deps:
        dep_str = ", ".join(missing_deps)
        lines.append(f"    {_c(_Ansi.RED, f'  ⚠ missing: {dep_str}')}")

    return "\n".join(lines)


def banner() -> None:
    """Print the KOME ASCII banner."""
    art = _c(_Ansi.MAGENTA + _Ansi.BOLD, r"""
   ██╗  ██╗ ██████╗ ███╗   ███╗███████╗
   ██║ ██╔╝██╔═══██╗████╗ ████║██╔════╝
   █████╔╝ ██║   ██║██╔████╔██║█████╗
   ██╔═██╗ ██║   ██║██║╚██╔╝██║██╔══╝
   ██║  ██╗╚██████╔╝██║ ╚═╝ ██║███████╗
   ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝
    """)
    subtitle = _c(_Ansi.DIM, "   🍚  Rice manager for Linux\n")
    print(art + subtitle)
