"""KOME Rice Manager — main orchestrator tying all subsystems together."""

from __future__ import annotations

import json
import shutil
import tarfile
import zipfile
from pathlib import Path

from kome.config import RICES_DIR, ensure_dirs
from kome.core.backup import BackupManager
from kome.core.rice import Rice
from kome.core.state import StateManager
from kome.core.symlinker import Symlinker
from kome.utils import logger
from kome.utils.process import run_reload_script


class RiceManager:
    """High-level orchestrator — each public method maps to a CLI command."""

    def __init__(self) -> None:
        ensure_dirs()
        self.state_mgr = StateManager()
        self.symlinker = Symlinker()
        self.backup_mgr = BackupManager()

    def list_rices(self) -> list[Rice]:
        """Return all valid rices in the rices directory."""
        rices: list[Rice] = []

        if not RICES_DIR.is_dir():
            return rices

        for entry in sorted(RICES_DIR.iterdir()):
            if not entry.is_dir():
                continue
            try:
                rices.append(Rice.from_directory(entry))
            except ValueError as exc:
                logger.warning(f"Skipping '{entry.name}': {exc}")

        return rices

    def apply(
        self,
        name: str,
        *,
        force: bool = False,
        no_reload: bool = False,
    ) -> bool:
        """Apply a rice: backup → deps check → unlink old → symlink new → reload."""
        rice_path = RICES_DIR / name
        if not rice_path.is_dir():
            logger.error(f"Rice '{name}' not found in {RICES_DIR}")
            return False

        try:
            rice = Rice.from_directory(rice_path)
        except ValueError as exc:
            logger.error(str(exc))
            return False

        warnings = rice.validate()
        for w in warnings:
            logger.warning(w)

        state = self.state_mgr.load()

        if state.active_rice == name and not force:
            logger.info(f"Rice '{name}' is already active. Use --force to reapply.")
            return True

        # Initial backup (first run only)
        if state.first_run_backup is None:
            backup_path = self.backup_mgr.create_initial_backup()
            if backup_path:
                self.state_mgr.set_first_run_backup(backup_path)
                state = self.state_mgr.load()

        # Check dependencies
        if rice.has_deps and not force:
            missing = rice.get_missing_deps()
            if missing:
                logger.error(
                    "Missing dependencies for this rice:\n"
                    f"    {', '.join(missing)}\n"
                    "    Install them and try again, or use --force to skip."
                )
                return False
            else:
                logger.success("All dependencies satisfied.")

        # Unlink current rice
        if state.active_rice and state.symlinks:
            logger.header(f"Removing rice: {state.active_rice}")
            self.symlinker.unlink_current(state)

        # Create new symlinks
        logger.header(f"Applying rice: {name}")
        symlink_records, backup_records = self.symlinker.create_links(rice)

        if not symlink_records:
            logger.warning("No symlinks were created — the rice might be empty.")

        # Update state
        self.state_mgr.register_apply(name, symlink_records, backup_records)

        # Reload
        if not no_reload and rice.has_reload:
            logger.header("Reloading environment")
            run_reload_script(rice.path)
        elif not rice.has_reload:
            logger.info("No reload.sh — you may need to restart processes manually.")

        # Summary
        logger.header("Done")
        logger.success(
            f"Rice '{name}' applied with {len(symlink_records)} symlink(s)."
        )
        if backup_records:
            logger.info(f"{len(backup_records)} file(s) were backed up to .bak")

        return True

    def restore(self) -> bool:
        """Remove active rice symlinks and restore original config from backup."""
        state = self.state_mgr.load()

        if not state.active_rice and not state.first_run_backup:
            logger.info("Nothing to restore — no rice is active and no backup exists.")
            return True

        if state.active_rice and state.symlinks:
            logger.header(f"Removing rice: {state.active_rice}")
            self.symlinker.unlink_current(state)

        if state.first_run_backup:
            logger.header("Restoring full backup")
            self.backup_mgr.restore_full_backup(state.first_run_backup)

        # Preserve the first_run_backup ref so it's not recreated
        first_run = state.first_run_backup
        self.state_mgr.clear()
        if first_run:
            self.state_mgr.set_first_run_backup(first_run)

        logger.success("Configuration restored to original state.")
        return True

    def status(self) -> dict:
        """Return current status dict for display."""
        state = self.state_mgr.load()

        result = {
            "active_rice": state.active_rice,
            "applied_at": state.applied_at,
            "symlinks_total": len(state.symlinks),
            "valid": [],
            "broken": [],
            "first_run_backup": state.first_run_backup,
        }

        if state.symlinks:
            valid, broken = self.symlinker.verify_links(state)
            result["valid"] = valid
            result["broken"] = broken

        return result

    def add(self, source: str) -> bool:
        """Import a rice from a directory, .zip, or .tar.gz."""
        source_path = Path(source).resolve()

        if not source_path.exists():
            logger.error(f"Source not found: {source_path}")
            return False

        if source_path.is_file():
            return self._add_from_archive(source_path)

        if source_path.is_dir():
            return self._add_from_directory(source_path)

        logger.error(f"Unsupported source: {source_path}")
        return False

    def _add_from_directory(self, source: Path) -> bool:
        dest = RICES_DIR / source.name

        if dest.exists():
            logger.error(
                f"A rice named '{source.name}' already exists. "
                "Remove it first with `kome remove`."
            )
            return False

        try:
            Rice.from_directory(source)
        except ValueError as exc:
            logger.error(f"Invalid rice structure: {exc}")
            return False

        shutil.copytree(str(source), str(dest), symlinks=True)
        logger.success(f"Added rice '{source.name}' → {dest}")
        return True

    def _add_from_archive(self, archive: Path) -> bool:
        name = archive.stem
        if name.endswith(".tar"):
            name = name[:-4]

        dest = RICES_DIR / name

        if dest.exists():
            logger.error(
                f"A rice named '{name}' already exists. "
                "Remove it first with `kome remove`."
            )
            return False

        logger.info(f"Extracting '{archive.name}'…")

        try:
            if archive.suffix == ".zip":
                with zipfile.ZipFile(archive, "r") as zf:
                    zf.extractall(str(dest))
            elif archive.name.endswith((".tar.gz", ".tgz")):
                with tarfile.open(archive, "r:gz") as tf:
                    tf.extractall(str(dest), filter="data")
            elif archive.name.endswith(".tar"):
                with tarfile.open(archive, "r:") as tf:
                    tf.extractall(str(dest), filter="data")
            else:
                logger.error(f"Unsupported archive format: {archive.suffix}")
                return False
        except (zipfile.BadZipFile, tarfile.TarError, OSError) as exc:
            logger.error(f"Extraction failed: {exc}")
            if dest.exists():
                shutil.rmtree(str(dest))
            return False

        # Flatten single top-level directory from archive
        contents = list(dest.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            inner = contents[0]
            for child in inner.iterdir():
                child.rename(dest / child.name)
            inner.rmdir()

        try:
            rice = Rice.from_directory(dest)
            logger.success(f"Added rice '{rice.name}' from archive.")
            return True
        except ValueError as exc:
            logger.error(f"Extracted content is not a valid rice: {exc}")
            shutil.rmtree(str(dest))
            return False

    def remove(self, name: str) -> bool:
        """Remove a rice. Blocks if it's currently active."""
        rice_path = RICES_DIR / name

        if not rice_path.is_dir():
            logger.error(f"Rice '{name}' not found.")
            return False

        state = self.state_mgr.load()
        if state.active_rice == name:
            logger.error(
                f"Cannot remove '{name}' — it is currently active.\n"
                "    Run `kome apply <other-rice>` or `kome restore` first."
            )
            return False

        shutil.rmtree(str(rice_path))
        logger.success(f"Removed rice '{name}'.")
        return True
