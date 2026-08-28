"""
Backup management for KOME.

Creates a compressed tarball of the user's ``~/.config/`` directory
on first run so the original setup can always be recovered.
"""

from __future__ import annotations

import tarfile
from datetime import datetime
from pathlib import Path

from kome.config import BACKUPS_DIR, USER_CONFIG_DIR
from kome.utils import logger


class BackupManager:
    """Creates and restores full backups of ``~/.config/``."""

    def __init__(
        self,
        config_dir: Path | None = None,
        backups_dir: Path | None = None,
    ) -> None:
        self.config_dir = config_dir or USER_CONFIG_DIR
        self.backups_dir = backups_dir or BACKUPS_DIR

    # -----------------------------------------------------------------
    # Full backup
    # -----------------------------------------------------------------

    def create_initial_backup(self) -> str | None:
        """
        Create a ``.tar.gz`` of ``~/.config/`` if no backup exists yet.

        Returns the backup file path as a string, or ``None`` if a
        backup was already present.
        """
        self.backups_dir.mkdir(parents=True, exist_ok=True)

        # Check if we already did an initial backup
        existing = list(self.backups_dir.glob("config_backup_*.tar.gz"))
        if existing:
            logger.info("Initial backup already exists — skipping.")
            return str(existing[0])

        if not self.config_dir.is_dir():
            logger.warning(f"{self.config_dir} does not exist — nothing to backup.")
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_name = f"config_backup_{timestamp}.tar.gz"
        backup_path = self.backups_dir / backup_name

        logger.info(f"Creating initial backup of {self.config_dir}…")

        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                # Walk through config dir, skipping symlinks
                # (symlinks are likely KOME-managed or broken)
                for item in self.config_dir.iterdir():
                    if item.is_symlink():
                        continue
                    tar.add(
                        str(item),
                        arcname=item.relative_to(self.config_dir.parent),
                    )

            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.success(
                f"Backup created: {backup_path} ({size_mb:.1f} MB)"
            )
            return str(backup_path)

        except OSError as exc:
            logger.error(f"Failed to create backup: {exc}")
            return None

    # -----------------------------------------------------------------
    # Full restore
    # -----------------------------------------------------------------

    def restore_full_backup(self, backup_path: str | None = None) -> bool:
        """
        Extract the full backup tarball to restore the original
        ``~/.config/`` state.

        If *backup_path* is ``None``, the most recent backup in the
        backups directory is used.

        Returns ``True`` on success.
        """
        if backup_path:
            tar_path = Path(backup_path)
        else:
            # Find the most recent backup
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
                # Use 'tar' filter which is more permissive than 'data'
                # but still prevents path traversal.  Some configs contain
                # absolute symlinks (e.g. Discord) that 'data' rejects.
                try:
                    tar.extractall(path=extract_dir, filter="tar")
                except TypeError:
                    # Python < 3.12 doesn't support the filter kwarg
                    tar.extractall(path=extract_dir)

            logger.success("Full backup restored successfully.")
            return True

        except (tarfile.TarError, OSError) as exc:
            logger.error(f"Restore failed: {exc}")
            return False

