"""Colored terminal output. Respects NO_COLOR and dumb terminals."""

from __future__ import annotations

import os
import sys


def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_COLOR = _color_enabled()


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


def _c(code: str, text: str) -> str:
    """Wrap text in ANSI color if enabled."""
    if not _COLOR:
        return text
    return f"{code}{text}{_Ansi.RESET}"


def info(msg: str) -> None:
    print(f"  {_c(_Ansi.CYAN + _Ansi.BOLD, 'ℹ')}  {msg}")


def success(msg: str) -> None:
    print(f"  {_c(_Ansi.GREEN + _Ansi.BOLD, '✔')}  {msg}")


def warning(msg: str) -> None:
    print(f"  {_c(_Ansi.YELLOW + _Ansi.BOLD, '⚠')}  {_c(_Ansi.YELLOW, msg)}")


def error(msg: str) -> None:
    print(f"  {_c(_Ansi.RED + _Ansi.BOLD, '✖')}  {_c(_Ansi.RED, msg)}", file=sys.stderr)


def header(title: str) -> None:
    print()
    print(_c(_Ansi.MAGENTA + _Ansi.BOLD, f"  ── {title} ──"))
    print()


def dim(text: str) -> str:
    return _c(_Ansi.DIM, text)


def bold(text: str) -> str:
    return _c(_Ansi.BOLD, text)


def accent(text: str) -> str:
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
    """Format a rice entry for the `list` command."""
    star = _c(_Ansi.GREEN + _Ansi.BOLD, " ★ active") if is_active else ""
    title = f"  {_c(_Ansi.BOLD, name)}{star}"

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
    print(art + _c(_Ansi.DIM, "   🍚  Rice manager for Linux\n"))
