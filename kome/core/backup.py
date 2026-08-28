"""Backup management — tar.gz of ~/.config/ for safe rollback."""

from __future__ import annotations

import tarfile
from datetime import datetime
from pathlib import Path

from kome.config import BACKUPS_DIR, USER_CONFIG_DIR
from kome.utils import logger


class BackupManager:
    """Creates and restores full backups of ~/.config/."""

    def __init__(
        self,
        config_dir: Path | None = None,
        backups_dir: Path | None = None,
    ) -> None:
        self.config_dir = config_dir or USER_CONFIG_DIR
        self.backups_dir = backups_dir or BACKUPS_DIR

    def create_initial_backup(self) -> str | None:
        """Create a .tar.gz of ~/.config/ if no backup exists yet. Returns path or None."""
        self.backups_dir.mkdir(parents=True, exist_ok=True)

        existing = list(self.backups_dir.glob("config_backup_*.tar.gz"))
        if existing:
            logger.info("Initial backup already exists — skipping.")
            return str(existing[0])

        if not self.config_dir.is_dir():
            logger.warning(f"{self.config_dir} does not exist — nothing to backup.")
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_path = self.backups_dir / f"config_backup_{timestamp}.tar.gz"

        logger.info(f"Creating initial backup of {self.config_dir}…")

        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                for item in self.config_dir.iterdir():
                    if item.is_symlink():
                        continue  # Skip KOME-managed or broken symlinks
                    tar.add(
                        str(item),
                        arcname=item.relative_to(self.config_dir.parent),
                    )

            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.success(f"Backup created: {backup_path} ({size_mb:.1f} MB)")
            return str(backup_path)

        except OSError as exc:
            logger.error(f"Failed to create backup: {exc}")
            return None

    def restore_full_backup(self, backup_path: str | None = None) -> bool:
        """Extract the full backup tarball. Uses most recent if path is None."""
        if backup_path:
            tar_path = Path(backup_path)
        else:
            backups = sorted(self.backups_dir.glob("config_backup_*.tar.gz"))
            if not backups:
                logger.error("No backup found — cannot restore.")
                return False
            tar_path = backups[-1]

        if not tar_path.is_file():
            logger.error(f"Backup file not found: {tar_path}")
            return False

        logger.info(f"Restoring from: {tar_path}")

        extract_dir = str(self.config_dir.parent)

        try:
            with tarfile.open(tar_path, "r:gz") as tar:
                # 'tar' filter allows absolute symlinks (e.g. Discord) that 'data' rejects
                try:
                    tar.extractall(path=extract_dir, filter="tar")
                except TypeError:
                    tar.extractall(path=extract_dir)  # Python < 3.12

            logger.success("Full backup restored successfully.")
            return True

        except (tarfile.TarError, OSError) as exc:
            logger.error(f"Restore failed: {exc}")
            return False
