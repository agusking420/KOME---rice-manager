"""
Process management utilities for KOME.

Handles executing rice reload scripts and checking running processes.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from kome.utils import logger


def run_reload_script(rice_path: Path, *, timeout: int = 30) -> bool:
    """
    Execute the ``reload.sh`` script found inside *rice_path*.

    The script is run with ``bash`` in a subprocess.  A *timeout* (in
    seconds) guards against runaway scripts.

    Returns:
        ``True`` if the script ran successfully, ``False`` otherwise.
    """
    script = rice_path / "reload.sh"
    if not script.is_file():
        logger.warning("No reload.sh found — skipping process reload.")
        return False

    # Ensure the script is executable
    if not os.access(script, os.X_OK):
        script.chmod(script.stat().st_mode | 0o755)

    logger.info(f"Running reload script: {script}")

    try:
        result = subprocess.run(
            ["bash", str(script)],
            cwd=str(rice_path),
            timeout=timeout,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logger.error(f"reload.sh exited with code {result.returncode}")
            if result.stderr.strip():
                for line in result.stderr.strip().splitlines():
                    logger.error(f"  {line}")
            return False

        logger.success("Reload script finished successfully.")
        return True

    except subprocess.TimeoutExpired:
        logger.error(
            f"reload.sh timed out after {timeout}s — "
            "you may need to restart your session manually."
        )
        return False
    except FileNotFoundError:
        logger.error("bash not found — cannot execute reload.sh.")
        return False
    except OSError as exc:
        logger.error(f"Failed to run reload.sh: {exc}")
        return False


def is_process_running(name: str) -> bool:
    """
    Check if a process with the given *name* is currently running.

    Uses ``pgrep`` under the hood.
    """
    try:
        result = subprocess.run(
            ["pgrep", "-x", name],
            capture_output=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
