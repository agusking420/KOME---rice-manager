"""
Paths and constants for KOME.

Follows the XDG Base Directory Specification:
  - Data:  ~/.local/share/kome/
  - State: ~/.local/state/kome/
"""

from pathlib import Path
import os


def _xdg(env_var: str, default_subdir: str) -> Path:
    """Resolve an XDG base directory, falling back to the spec default."""
    return Path(os.environ.get(env_var, Path.home() / default_subdir))


# --- XDG roots ---------------------------------------------------------------
XDG_DATA_HOME = _xdg("XDG_DATA_HOME", ".local/share")
XDG_STATE_HOME = _xdg("XDG_STATE_HOME", ".local/state")
XDG_CONFIG_HOME = _xdg("XDG_CONFIG_HOME", ".config")

# --- KOME directories --------------------------------------------------------
KOME_DATA_DIR: Path = XDG_DATA_HOME / "kome"
RICES_DIR: Path = KOME_DATA_DIR / "rices"
BACKUPS_DIR: Path = KOME_DATA_DIR / "backups"

# --- State file ---------------------------------------------------------------
KOME_STATE_DIR: Path = XDG_STATE_HOME / "kome"
STATE_FILE: Path = KOME_STATE_DIR / "state.json"

# --- Target (user's config) ---------------------------------------------------
USER_CONFIG_DIR: Path = XDG_CONFIG_HOME

# --- Rice structure constants -------------------------------------------------
RICE_CONFIG_SUBDIR = ".config"
RICE_RELOAD_SCRIPT = "reload.sh"
RICE_PREVIEW_FILE = "preview.jpg"
RICE_DEPS_FILE = "deps.txt"
RICE_MAPPING_FILE = "mapping.json"
RICE_README_FILE = "README.md"

# --- Backup -------------------------------------------------------------------
BAK_SUFFIX = ".bak"

# --- Misc ---------------------------------------------------------------------
APP_NAME = "kome"
VERSION = "0.1.0"


def ensure_dirs() -> None:
    """Create all required KOME directories if they don't exist."""
    for d in (KOME_DATA_DIR, RICES_DIR, BACKUPS_DIR, KOME_STATE_DIR):
        d.mkdir(parents=True, exist_ok=True)
