"""
Tests for the KOME symlinker, state manager, and full apply/restore flow.

All tests operate inside a temporary directory to avoid touching the
real filesystem.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from kome.core.backup import BackupManager
from kome.core.rice import Rice
from kome.core.state import BackupRecord, KomeState, StateManager, SymlinkRecord
from kome.core.symlinker import Symlinker


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def workspace(tmp_path: Path):
    """
    Create a self-contained workspace with:
    - A fake ~/.config/ directory
    - A fake rices/ directory with a sample rice
    - A state.json path
    - A backups/ directory
    """
    config_dir = tmp_path / ".config"
    config_dir.mkdir()

    rices_dir = tmp_path / "rices"
    rices_dir.mkdir()

    backups_dir = tmp_path / "backups"
    backups_dir.mkdir()

    state_file = tmp_path / "state.json"

    return {
        "root": tmp_path,
        "config_dir": config_dir,
        "rices_dir": rices_dir,
        "backups_dir": backups_dir,
        "state_file": state_file,
    }


@pytest.fixture
def sample_rice(workspace) -> Rice:
    """Create a sample rice directory and return a Rice object."""
    rice_dir = workspace["rices_dir"] / "test-rice"
    rice_dir.mkdir()

    # Create .config/ with some entries
    config = rice_dir / ".config"
    config.mkdir()

    # i3 directory with a config file
    i3 = config / "i3"
    i3.mkdir()
    (i3 / "config").write_text("# i3 config from test-rice\n")

    # kitty directory
    kitty = config / "kitty"
    kitty.mkdir()
    (kitty / "kitty.conf").write_text("# kitty config\n")

    # Single file
    (config / "starship.toml").write_text("# starship config\n")

    # deps.txt
    (rice_dir / "deps.txt").write_text("bash\npython3\n# comment\n\nls\n")

    # reload.sh
    (rice_dir / "reload.sh").write_text("#!/bin/bash\necho 'reloaded'\n")
    (rice_dir / "reload.sh").chmod(0o755)

    return Rice.from_directory(rice_dir)


@pytest.fixture
def rice_with_mapping(workspace) -> Rice:
    """Create a rice with mapping.json for extra links."""
    rice_dir = workspace["rices_dir"] / "mapped-rice"
    rice_dir.mkdir()

    config = rice_dir / ".config"
    config.mkdir()
    rofi = config / "rofi"
    rofi.mkdir()
    (rofi / "config.rasi").write_text("/* rofi */\n")

    # Extra files outside .config
    (rice_dir / ".Xresources").write_text("! Xresources\n")
    (rice_dir / ".bashrc_extra").write_text("# bashrc additions\n")

    # mapping.json
    mapping = {
        "extra_links": [
            {"source": ".Xresources", "target": str(workspace["root"] / ".Xresources")},
            {"source": ".bashrc_extra", "target": str(workspace["root"] / ".bashrc_extra")},
        ]
    }
    (rice_dir / "mapping.json").write_text(json.dumps(mapping))

    return Rice.from_directory(rice_dir)


# =====================================================================
# Rice model tests
# =====================================================================


class TestRice:
    def test_from_directory(self, sample_rice: Rice):
        assert sample_rice.name == "test-rice"
        assert sample_rice.has_reload is True
        assert sample_rice.has_deps is True
        assert sample_rice.dependencies == ["bash", "python3", "ls"]

    def test_get_config_entries(self, sample_rice: Rice):
        entries = sample_rice.get_config_entries()
        names = [e.name for e in entries]
        assert "i3" in names
        assert "kitty" in names
        assert "starship.toml" in names

    def test_missing_deps(self, sample_rice: Rice):
        # bash, python3, ls should all exist on any Linux system
        missing = sample_rice.get_missing_deps()
        assert missing == [], f"Unexpectedly missing: {missing}"

    def test_invalid_rice(self, workspace):
        empty_dir = workspace["rices_dir"] / "empty"
        empty_dir.mkdir()
        with pytest.raises(ValueError, match="missing"):
            Rice.from_directory(empty_dir)

    def test_rice_with_mapping(self, rice_with_mapping: Rice):
        assert rice_with_mapping.has_mapping is True
        assert len(rice_with_mapping.extra_mappings) == 2
        assert rice_with_mapping.extra_mappings[0].source == ".Xresources"

    def test_validate_ok(self, sample_rice: Rice):
        warnings = sample_rice.validate()
        assert warnings == []


# =====================================================================
# State manager tests
# =====================================================================


class TestStateManager:
    def test_fresh_state(self, workspace):
        sm = StateManager(workspace["state_file"])
        state = sm.load()
        assert state.active_rice is None
        assert state.symlinks == []

    def test_save_and_load(self, workspace):
        sm = StateManager(workspace["state_file"])

        sm.register_apply(
            "test-rice",
            [SymlinkRecord(link="/a/b", target="/c/d")],
            [BackupRecord(original="/a/b", backup="/a/b.bak")],
        )

        state = sm.load()
        assert state.active_rice == "test-rice"
        assert len(state.symlinks) == 1
        assert state.symlinks[0].link == "/a/b"
        assert len(state.backup_files) == 1

    def test_clear(self, workspace):
        sm = StateManager(workspace["state_file"])
        sm.register_apply("x", [], [])
        sm.clear()

        state = sm.load()
        assert state.active_rice is None

    def test_atomic_write(self, workspace):
        """Verify that .tmp file is cleaned up after save."""
        sm = StateManager(workspace["state_file"])
        sm.save(KomeState(active_rice="test"))

        tmp = workspace["state_file"].with_suffix(".tmp")
        assert not tmp.exists(), ".tmp file should be cleaned up"
        assert workspace["state_file"].is_file()


# =====================================================================
# Symlinker tests
# =====================================================================


class TestSymlinker:
    def test_create_links(self, workspace, sample_rice: Rice):
        symlinker = Symlinker(target_dir=workspace["config_dir"])
        symlinks, backups = symlinker.create_links(sample_rice)

        assert len(symlinks) == 3  # i3, kitty, starship.toml
        assert len(backups) == 0

        # Verify symlinks exist and point correctly
        for record in symlinks:
            link = Path(record.link)
            assert link.is_symlink()
            assert link.resolve() == Path(record.target).resolve()

    def test_backup_existing_files(self, workspace, sample_rice: Rice):
        """Existing real files should be renamed to .bak."""
        # Create a conflicting real directory
        existing_i3 = workspace["config_dir"] / "i3"
        existing_i3.mkdir()
        (existing_i3 / "old_config").write_text("user's original config\n")

        symlinker = Symlinker(target_dir=workspace["config_dir"])
        symlinks, backups = symlinker.create_links(sample_rice)

        # i3 should have been backed up
        assert len(backups) == 1
        assert backups[0].original == str(existing_i3)
        bak_path = Path(backups[0].backup)
        assert bak_path.is_dir()
        assert (bak_path / "old_config").read_text() == "user's original config\n"

    def test_unlink_current(self, workspace, sample_rice: Rice):
        symlinker = Symlinker(target_dir=workspace["config_dir"])
        symlinks, backups = symlinker.create_links(sample_rice)

        # Build a state
        state = KomeState(
            active_rice="test-rice",
            symlinks=[SymlinkRecord(link=s.link, target=s.target) for s in symlinks],
            backup_files=[BackupRecord(original=b.original, backup=b.backup) for b in backups],
        )

        removed = symlinker.unlink_current(state)
        assert removed == 3

        # Verify symlinks are gone
        for record in symlinks:
            assert not Path(record.link).is_symlink()

    def test_restore_bak_on_unlink(self, workspace, sample_rice: Rice):
        """When unlinking, .bak files should be restored."""
        # Create a conflict
        existing = workspace["config_dir"] / "kitty"
        existing.mkdir()
        (existing / "user.conf").write_text("original\n")

        symlinker = Symlinker(target_dir=workspace["config_dir"])
        symlinks, backups = symlinker.create_links(sample_rice)

        # Now unlink
        state = KomeState(
            active_rice="test-rice",
            symlinks=[SymlinkRecord(link=s.link, target=s.target) for s in symlinks],
            backup_files=[BackupRecord(original=b.original, backup=b.backup) for b in backups],
        )

        symlinker.unlink_current(state)

        # The original kitty dir should be back
        restored = workspace["config_dir"] / "kitty"
        assert restored.is_dir()
        assert (restored / "user.conf").read_text() == "original\n"

    def test_verify_links(self, workspace, sample_rice: Rice):
        symlinker = Symlinker(target_dir=workspace["config_dir"])
        symlinks, _ = symlinker.create_links(sample_rice)

        state = KomeState(
            symlinks=[SymlinkRecord(link=s.link, target=s.target) for s in symlinks],
        )

        valid, broken = symlinker.verify_links(state)
        assert len(valid) == 3
        assert len(broken) == 0

    def test_mapping_links(self, workspace, rice_with_mapping: Rice):
        """Extra mapping links should be created alongside .config/ entries."""
        symlinker = Symlinker(target_dir=workspace["config_dir"])
        symlinks, backups = symlinker.create_links(rice_with_mapping)

        # 1 config entry (rofi) + 2 mappings = 3
        assert len(symlinks) == 3

        # Check that extra mappings point correctly
        xres = workspace["root"] / ".Xresources"
        assert xres.is_symlink()
        assert xres.resolve().name == ".Xresources"

    def test_double_bak(self, workspace, sample_rice: Rice):
        """If .bak already exists, a numeric suffix should be used."""
        # Create conflict + existing .bak
        existing = workspace["config_dir"] / "i3"
        existing.mkdir()
        (existing / "a").write_text("original\n")

        bak = workspace["config_dir"] / "i3.bak"
        bak.mkdir()
        (bak / "b").write_text("old bak\n")

        symlinker = Symlinker(target_dir=workspace["config_dir"])
        _, backups = symlinker.create_links(sample_rice)

        # Should have created i3.bak.1
        assert len(backups) == 1
        assert backups[0].backup.endswith(".bak.1")
        assert Path(backups[0].backup).is_dir()


# =====================================================================
# Backup manager tests
# =====================================================================


class TestBackupManager:
    def test_create_initial_backup(self, workspace):
        # Put something in config
        (workspace["config_dir"] / "something.conf").write_text("data\n")

        bm = BackupManager(
            config_dir=workspace["config_dir"],
            backups_dir=workspace["backups_dir"],
        )

        path = bm.create_initial_backup()
        assert path is not None
        assert Path(path).is_file()
        assert path.endswith(".tar.gz")

    def test_skip_second_backup(self, workspace):
        (workspace["config_dir"] / "x").write_text("x\n")

        bm = BackupManager(
            config_dir=workspace["config_dir"],
            backups_dir=workspace["backups_dir"],
        )

        first = bm.create_initial_backup()
        second = bm.create_initial_backup()

        # Should return the same path (not create a new one)
        assert first == second
