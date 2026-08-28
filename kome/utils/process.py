"""Process utilities — reload script execution and process detection."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from kome.utils import logger


def run_reload_script(rice_path: Path, *, timeout: int = 30) -> bool:
    """Execute reload.sh from the rice directory. Returns True on success."""
    script = rice_path / "reload.sh"
    if not script.is_file():
        logger.warning("No reload.sh found — skipping process reload.")
        return False

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
        logger.error(f"reload.sh timed out after {timeout}s — restart manually.")
        return False
    except FileNotFoundError:
        logger.error("bash not found — cannot execute reload.sh.")
        return False
    except OSError as exc:
        logger.error(f"Failed to run reload.sh: {exc}")
        return False


def is_process_running(name: str) -> bool:
    """Check if a process is running (via pgrep)."""
    try:
        return subprocess.run(["pgrep", "-x", name], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False
