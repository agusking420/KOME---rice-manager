"""State management — tracks active rice, symlinks, and backups in state.json."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from kome.config import STATE_FILE


@dataclass
class SymlinkRecord:
    """A single symlink created by KOME."""
    link: str    # Where the symlink lives (e.g. ~/.config/i3)
    target: str  # What the symlink points to (inside the rice)


@dataclass
class BackupRecord:
    """A file that was renamed to .bak."""
    original: str
    backup: str


@dataclass
class KomeState:
    """Full application state, serialised directly to/from JSON."""
    active_rice: str | None = None
    applied_at: str | None = None
    symlinks: list[SymlinkRecord] = field(default_factory=list)
    backup_files: list[BackupRecord] = field(default_factory=list)
    first_run_backup: str | None = None


class StateManager:
    """Reads/writes state.json with atomic writes (tmp + rename)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or STATE_FILE

    def load(self) -> KomeState:
        """Load state from disk. Returns fresh state if file is missing."""
        if not self.path.is_file():
            return KomeState()

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return KomeState()

        return KomeState(
            active_rice=raw.get("active_rice"),
            applied_at=raw.get("applied_at"),
            symlinks=[SymlinkRecord(**s) for s in raw.get("symlinks", [])],
            backup_files=[BackupRecord(**b) for b in raw.get("backup_files", [])],
            first_run_backup=raw.get("first_run_backup"),
        )

    def save(self, state: KomeState) -> None:
        """Write state atomically (write to .tmp, then rename)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self.path.with_suffix(".tmp")
        data = json.dumps(asdict(state), indent=2, ensure_ascii=False)
        tmp_path.write_text(data + "\n", encoding="utf-8")
        tmp_path.replace(self.path)

    def get_active_rice(self) -> str | None:
        return self.load().active_rice

    def get_symlinks(self) -> list[SymlinkRecord]:
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
        state = self.load()
        state.first_run_backup = backup_path
        self.save(state)

    def clear(self) -> None:
        """Reset state to empty."""
        self.save(KomeState())
