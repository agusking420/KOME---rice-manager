"""Paths and constants for KOME (XDG-compliant)."""

from pathlib import Path
import os


def _xdg(env_var: str, default_subdir: str) -> Path:
    """Resolve an XDG base directory with fallback."""
    return Path(os.environ.get(env_var, Path.home() / default_subdir))


XDG_DATA_HOME = _xdg("XDG_DATA_HOME", ".local/share")
XDG_STATE_HOME = _xdg("XDG_STATE_HOME", ".local/state")
XDG_CONFIG_HOME = _xdg("XDG_CONFIG_HOME", ".config")

KOME_DATA_DIR: Path = XDG_DATA_HOME / "kome"
RICES_DIR: Path = KOME_DATA_DIR / "rices"
BACKUPS_DIR: Path = KOME_DATA_DIR / "backups"

KOME_STATE_DIR: Path = XDG_STATE_HOME / "kome"
STATE_FILE: Path = KOME_STATE_DIR / "state.json"

USER_CONFIG_DIR: Path = XDG_CONFIG_HOME

RICE_CONFIG_SUBDIR = ".config"
RICE_RELOAD_SCRIPT = "reload.sh"
RICE_PREVIEW_FILE = "preview.jpg"
RICE_DEPS_FILE = "deps.txt"
RICE_MAPPING_FILE = "mapping.json"
RICE_README_FILE = "README.md"

BAK_SUFFIX = ".bak"
APP_NAME = "kome"
VERSION = "0.1.0"


def ensure_dirs() -> None:
    """Create all required KOME directories if they don't exist."""
    for d in (KOME_DATA_DIR, RICES_DIR, BACKUPS_DIR, KOME_STATE_DIR):
        d.mkdir(parents=True, exist_ok=True)
