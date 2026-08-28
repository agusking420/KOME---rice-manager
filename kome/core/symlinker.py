"""Symlink engine — creates, removes, and verifies symlinks for rices."""

from __future__ import annotations

import os
from pathlib import Path

from kome.config import BAK_SUFFIX, USER_CONFIG_DIR
from kome.core.rice import Rice
from kome.core.state import BackupRecord, KomeState, SymlinkRecord
from kome.utils import logger


class Symlinker:
    """Manages the lifecycle of symlinks for a rice."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or USER_CONFIG_DIR

    def unlink_current(self, state: KomeState) -> int:
        """Remove all symlinks in state and restore .bak files. Returns count removed."""
        removed = 0

        for record in state.symlinks:
            link_path = Path(record.link)

            if link_path.is_symlink():
                link_path.unlink()
                logger.info(f"Removed symlink: {link_path}")
                removed += 1
            elif link_path.exists():
                logger.warning(
                    f"Expected symlink but found real file: {link_path} — skipping."
                )
            else:
                logger.info(f"Symlink already gone: {link_path}")
                removed += 1

        restored = self._restore_bak_files(state.backup_files)
        if restored:
            logger.success(f"Restored {restored} backed‐up file(s).")

        return removed

    def create_links(
        self, rice: Rice
    ) -> tuple[list[SymlinkRecord], list[BackupRecord]]:
        """Create symlinks for a rice. Returns (symlink_records, backup_records)."""
        symlinks: list[SymlinkRecord] = []
        backups: list[BackupRecord] = []

        # Standard .config/ entries
        for entry in rice.get_config_entries():
            link_path = self.target_dir / entry.name
            target_path = entry.resolve()

            bak = self._prepare_destination(link_path)
            if bak:
                backups.append(bak)

            self._make_symlink(target_path, link_path)
            symlinks.append(SymlinkRecord(
                link=str(link_path),
                target=str(target_path),
            ))

        # Extra mappings (mapping.json)
        for mapping in rice.extra_mappings:
            source_abs, target_abs = mapping.resolve(rice.path)

            if not source_abs.exists():
                logger.warning(
                    f"Skipping mapping: source '{mapping.source}' not found."
                )
                continue

            target_abs.parent.mkdir(parents=True, exist_ok=True)

            bak = self._prepare_destination(target_abs)
            if bak:
                backups.append(bak)

            self._make_symlink(source_abs, target_abs)
            symlinks.append(SymlinkRecord(
                link=str(target_abs),
                target=str(source_abs),
            ))

        return symlinks, backups

    def verify_links(self, state: KomeState) -> tuple[list[str], list[str]]:
        """Verify symlink integrity. Returns (valid, broken) path lists."""
        valid: list[str] = []
        broken: list[str] = []

        for record in state.symlinks:
            link_path = Path(record.link)

            if not link_path.exists() and not link_path.is_symlink():
                broken.append(record.link)
            elif link_path.is_symlink():
                real_target = link_path.resolve()
                expected_target = Path(record.target).resolve()
                if real_target == expected_target:
                    valid.append(record.link)
                else:
                    broken.append(record.link)
            else:
                broken.append(record.link)

        return valid, broken

    def _prepare_destination(self, dest: Path) -> BackupRecord | None:
        """Handle existing destination: remove old symlinks, .bak real files."""
        if dest.is_symlink():
            dest.unlink()
            logger.info(f"Removed old symlink: {dest}")
            return None

        if dest.exists():
            bak_path = dest.with_name(dest.name + BAK_SUFFIX)

            # Numeric suffix if .bak already exists
            counter = 1
            while bak_path.exists():
                bak_path = dest.with_name(f"{dest.name}{BAK_SUFFIX}.{counter}")
                counter += 1

            dest.rename(bak_path)
            logger.warning(f"Backed up: {dest} → {bak_path}")
            return BackupRecord(original=str(dest), backup=str(bak_path))

        return None

    @staticmethod
    def _make_symlink(target: Path, link: Path) -> None:
        """Create a symlink at link pointing to target."""
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(target), str(link))
        logger.success(f"Linked: {link} → {target}")

    @staticmethod
    def _restore_bak_files(backup_records: list[BackupRecord]) -> int:
        """Restore .bak files to their original paths. Returns count restored."""
        count = 0
        for record in backup_records:
            bak_path = Path(record.backup)
            original_path = Path(record.original)

            if not bak_path.exists():
                logger.warning(f"Backup file missing, cannot restore: {bak_path}")
                continue

            if original_path.is_symlink():
                original_path.unlink()
            elif original_path.exists():
                logger.warning(
                    f"Cannot restore {original_path} — "
                    "a non-symlink file already exists there."
                )
                continue

            bak_path.rename(original_path)
            logger.info(f"Restored: {bak_path} → {original_path}")
            count += 1

        return count
