"""
Rice data model.

A :class:`Rice` object represents a single rice directory inside the
KOME rices store.  It provides helpers for introspecting the rice's
contents — config entries, dependencies, preview image, etc.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from kome.config import (
    RICE_CONFIG_SUBDIR,
    RICE_DEPS_FILE,
    RICE_MAPPING_FILE,
    RICE_PREVIEW_FILE,
    RICE_RELOAD_SCRIPT,
)
from kome.utils.deps import check_dependencies, parse_deps_file


@dataclass
class MappingEntry:
    """A single extra‐link declared in ``mapping.json``."""

    source: str  # Relative path inside the rice directory
    target: str  # Absolute destination path (~ is expanded)

    def resolve(self, rice_path: Path) -> tuple[Path, Path]:
        """Return ``(source_abs, target_abs)`` with all paths resolved."""
        src = (rice_path / self.source).resolve()
        tgt = Path(self.target).expanduser().resolve()
        return src, tgt


@dataclass
class Rice:
    """
    Represents a rice stored inside the KOME rices directory.

    Use the :meth:`from_directory` classmethod to build an instance
    from an existing directory on disk.
    """

    name: str
    path: Path
    config_path: Path
    has_reload: bool = False
    has_preview: bool = False
    has_deps: bool = False
    has_mapping: bool = False
    dependencies: list[str] = field(default_factory=list)
    extra_mappings: list[MappingEntry] = field(default_factory=list)

    # -----------------------------------------------------------------
    # Factory
    # -----------------------------------------------------------------

    @classmethod
    def from_directory(cls, path: Path) -> "Rice":
        """
        Build a :class:`Rice` from an on‐disk directory.

        Raises :exc:`ValueError` if *path* doesn't look like a valid rice
        (i.e. it has no ``.config/`` subdirectory).
        """
        path = path.resolve()
        if not path.is_dir():
            raise ValueError(f"Not a directory: {path}")

        config_path = path / RICE_CONFIG_SUBDIR
        # .config/ is required unless there's a mapping.json
        mapping_path = path / RICE_MAPPING_FILE
        has_mapping = mapping_path.is_file()

        if not config_path.is_dir() and not has_mapping:
            raise ValueError(
                f"Rice '{path.name}' is missing a '{RICE_CONFIG_SUBDIR}/' "
                f"directory and has no '{RICE_MAPPING_FILE}'."
            )

        deps_path = path / RICE_DEPS_FILE
        has_deps = deps_path.is_file()
        dependencies = parse_deps_file(deps_path) if has_deps else []

        extra_mappings: list[MappingEntry] = []
        if has_mapping:
            extra_mappings = _parse_mapping_file(mapping_path)

        return cls(
            name=path.name,
            path=path,
            config_path=config_path,
            has_reload=(path / RICE_RELOAD_SCRIPT).is_file(),
            has_preview=(path / RICE_PREVIEW_FILE).is_file(),
            has_deps=has_deps,
            has_mapping=has_mapping,
            dependencies=dependencies,
            extra_mappings=extra_mappings,
        )

    # -----------------------------------------------------------------
    # Public helpers
    # -----------------------------------------------------------------

    def get_config_entries(self) -> list[Path]:
        """
        Return the top‐level entries inside this rice's ``.config/``
        directory (absolute paths).

        Each entry maps 1‐to‐1 with a symlink that will be created
        under ``~/.config/``.
        """
        if not self.config_path.is_dir():
            return []
        return sorted(self.config_path.iterdir())

    def get_missing_deps(self) -> list[str]:
        """Return names of dependencies not installed on the system."""
        if not self.dependencies:
            return []
        _, missing = check_dependencies(self.dependencies)
        return missing

    def validate(self) -> list[str]:
        """
        Validate the rice structure and return a list of warnings.

        An empty list means the rice is fully valid.
        """
        warnings: list[str] = []

        if not self.config_path.is_dir() and not self.extra_mappings:
            warnings.append(
                f"Missing '{RICE_CONFIG_SUBDIR}/' directory and no extra mappings."
            )

        if self.config_path.is_dir() and not list(self.config_path.iterdir()):
            warnings.append(f"'{RICE_CONFIG_SUBDIR}/' directory is empty.")

        # Validate mapping sources exist
        for m in self.extra_mappings:
            src = self.path / m.source
            if not src.exists():
                warnings.append(
                    f"mapping.json references '{m.source}' but it doesn't exist."
                )

        return warnings


def _parse_mapping_file(path: Path) -> list[MappingEntry]:
    """
    Parse a ``mapping.json`` file.

    Expected format::

        {
          "extra_links": [
            {"source": ".Xresources", "target": "~/.Xresources"},
            {"source": "wallpapers", "target": "~/Pictures/wallpapers"}
          ]
        }
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Invalid mapping.json: {exc}") from exc

    entries: list[MappingEntry] = []
    for item in data.get("extra_links", []):
        if "source" not in item or "target" not in item:
            raise ValueError(
                "Each entry in 'extra_links' must have 'source' and 'target' keys."
            )
        entries.append(MappingEntry(source=item["source"], target=item["target"]))

    return entries
