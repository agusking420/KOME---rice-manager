"""
Persistent state management for KOME.

Tracks which rice is active, what symlinks were created, and which
files were backed‐up.  All data is stored in a single JSON file
(``~/.local/state/kome/state.json``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from kome.config import STATE_FILE


@dataclass
class SymlinkRecord:
    """Record of a single symlink created by KOME."""

    link: str    # Path where the symlink lives (e.g. ~/.config/i3)
    target: str  # Path the symlink points to (inside the rice)


@dataclass
class BackupRecord:
    """Record of a file that was renamed to ``.bak``."""

    original: str  # Original path of the file
    backup: str    # Path after renaming (.bak)


@dataclass
class KomeState:
    """
    Full application state.

    This dataclass is serialised directly to/from JSON.
    """

    active_rice: str | None = None
    applied_at: str | None = None
    symlinks: list[SymlinkRecord] = field(default_factory=list)
    backup_files: list[BackupRecord] = field(default_factory=list)
    first_run_backup: str | None = None


class StateManager:
    """
    Read/write ``state.json`` atomically.

    Usage::

        sm = StateManager()
        state = sm.load()
        state.active_rice = "cyber-neon"
        sm.save(state)
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or STATE_FILE

    # -----------------------------------------------------------------
    # I/O
    # -----------------------------------------------------------------

    def load(self) -> KomeState:
        """Load state from disk.  Returns a fresh state if the file doesn't exist."""
        if not self.path.is_file():
            return KomeState()

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return KomeState()

        return KomeState(
            active_rice=raw.get("active_rice"),
            applied_at=raw.get("applied_at"),
            symlinks=[
                SymlinkRecord(**s) for s in raw.get("symlinks", [])
            ],
            backup_files=[
                BackupRecord(**b) for b in raw.get("backup_files", [])
            ],
            first_run_backup=raw.get("first_run_backup"),
        )

    def save(self, state: KomeState) -> None:
        """
        Write *state* to disk atomically.

        Writes to a temporary file first, then renames to avoid
        corruption on crash.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self.path.with_suffix(".tmp")
        data = json.dumps(asdict(state), indent=2, ensure_ascii=False)
        tmp_path.write_text(data + "\n", encoding="utf-8")
        tmp_path.replace(self.path)

    # -----------------------------------------------------------------
    # Convenience accessors
    # -----------------------------------------------------------------

    def get_active_rice(self) -> str | None:
        """Return the name of the currently active rice, or ``None``."""
        return self.load().active_rice

    def get_symlinks(self) -> list[SymlinkRecord]:
        """Return the list of symlinks registered by the last apply."""
        return self.load().symlinks

    def register_apply(
        self,
        rice_name: str,
        symlinks: list[SymlinkRecord],
        backups: list[BackupRecord],
    ) -> None:
        """Record a new rice application."""
        state = self.load()
        state.active_rice = rice_name
        state.applied_at = datetime.now(timezone.utc).isoformat()
        state.symlinks = symlinks
        state.backup_files = backups
        self.save(state)

    def set_first_run_backup(self, backup_path: str) -> None:
        """Store the path to the initial full backup tarball."""
        state = self.load()
        state.first_run_backup = backup_path
        self.save(state)

    def clear(self) -> None:
        """Reset state to empty (post‐restore)."""
        self.save(KomeState())
