"""
KOME command‐line interface.

Exposes: list, apply, restore, status, add, remove.
"""

from __future__ import annotations

import argparse
import sys

from kome import __version__
from kome.core.manager import RiceManager
from kome.utils import logger


# =====================================================================
# Command handlers
# =====================================================================

def _cmd_list(manager: RiceManager, _args: argparse.Namespace) -> int:
    """Handle ``kome list``."""
    rices = manager.list_rices()

    if not rices:
        logger.info("No rices found. Add one with `kome add <path>`.")
        return 0

    state = manager.state_mgr.load()
    active = state.active_rice

    logger.header("Available rices")

    for rice in rices:
        missing = rice.get_missing_deps()
        card = logger.rice_card(
            rice.name,
            is_active=(rice.name == active),
            has_preview=rice.has_preview,
            has_reload=rice.has_reload,
            has_deps=rice.has_deps,
            has_mapping=rice.has_mapping,
            missing_deps=missing if missing else None,
        )
        print(card)
        print()

    logger.info(f"{len(rices)} rice(s) available.")
    return 0


def _cmd_apply(manager: RiceManager, args: argparse.Namespace) -> int:
    """Handle ``kome apply <name>``."""
    ok = manager.apply(
        args.name,
        force=args.force,
        no_reload=args.no_reload,
    )
    return 0 if ok else 1


def _cmd_restore(manager: RiceManager, _args: argparse.Namespace) -> int:
    """Handle ``kome restore``."""
    ok = manager.restore()
    return 0 if ok else 1


def _cmd_status(manager: RiceManager, _args: argparse.Namespace) -> int:
    """Handle ``kome status``."""
    status = manager.status()

    logger.header("KOME Status")

    if status["active_rice"]:
        logger.info(f"Active rice: {logger.accent(status['active_rice'])}")
        logger.info(f"Applied at:  {status['applied_at']}")
        logger.info(f"Symlinks:    {status['symlinks_total']}")

        valid = status["valid"]
        broken = status["broken"]

        if valid:
            logger.success(f"{len(valid)} symlink(s) OK")
        if broken:
            logger.error(f"{len(broken)} broken symlink(s):")
            for b in broken:
                logger.error(f"  → {b}")
    else:
        logger.info("No rice is currently active.")

    if status["first_run_backup"]:
        logger.info(f"Initial backup: {logger.dim(status['first_run_backup'])}")

    return 0


def _cmd_add(manager: RiceManager, args: argparse.Namespace) -> int:
    """Handle ``kome add <path>``."""
    ok = manager.add(args.path)
    return 0 if ok else 1


def _cmd_remove(manager: RiceManager, args: argparse.Namespace) -> int:
    """Handle ``kome remove <name>``."""
    ok = manager.remove(args.name)
    return 0 if ok else 1


# =====================================================================
# Parser construction
# =====================================================================

def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="kome",
        description="🍚 KOME — Rice manager for Linux",
        epilog="https://github.com/agusdev/kome",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"kome {__version__}",
    )

    sub = parser.add_subparsers(dest="command", metavar="command")

    # --- list ---------------------------------------------------------
    sub.add_parser(
        "list",
        aliases=["ls"],
        help="List available rices",
    )

    # --- apply --------------------------------------------------------
    apply_p = sub.add_parser(
        "apply",
        aliases=["switch"],
        help="Apply a rice",
    )
    apply_p.add_argument("name", help="Name of the rice to apply")
    apply_p.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip dependency checks and reapply even if already active",
    )
    apply_p.add_argument(
        "--no-reload",
        action="store_true",
        help="Don't run reload.sh after applying",
    )

    # --- restore ------------------------------------------------------
    sub.add_parser(
        "restore",
        help="Restore original configuration from backup",
    )

    # --- status -------------------------------------------------------
    sub.add_parser(
        "status",
        help="Show current rice status and symlink integrity",
    )

    # --- add ----------------------------------------------------------
    add_p = sub.add_parser(
        "add",
        help="Import a rice from a directory or archive (.zip, .tar.gz)",
    )
    add_p.add_argument(
        "path",
        help="Path to a rice directory or archive file",
    )

    # --- remove -------------------------------------------------------
    rm_p = sub.add_parser(
        "remove",
        aliases=["rm"],
        help="Remove a rice from the library",
    )
    rm_p.add_argument("name", help="Name of the rice to remove")

    return parser


# =====================================================================
# Entry point
# =====================================================================

def main(argv: list[str] | None = None) -> None:
    """Main CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        logger.banner()
        parser.print_help()
        sys.exit(0)

    manager = RiceManager()

    # Resolve aliases
    handlers = {
        "list": _cmd_list,
        "ls": _cmd_list,
        "apply": _cmd_apply,
        "switch": _cmd_apply,
        "restore": _cmd_restore,
        "status": _cmd_status,
        "add": _cmd_add,
        "remove": _cmd_remove,
        "rm": _cmd_remove,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    try:
        code = handler(manager, args)
        sys.exit(code)
    except KeyboardInterrupt:
        print()
        logger.info("Interrupted.")
        sys.exit(130)
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}")
        sys.exit(1)
