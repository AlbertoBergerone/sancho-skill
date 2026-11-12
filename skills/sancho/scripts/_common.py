"""Shared helpers for Sancho scripts (standard library only)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PHASES = ["discover", "specify", "plan", "tasks", "implement", "verify", "release", "evolve"]

PHASE_LEAD = {
    "discover": "analyst-pm",
    "specify": "analyst-pm",
    "plan": "architect",
    "tasks": "analyst-pm",
    "implement": "developer",
    "verify": "qa",
    "release": "release-manager",
    "evolve": "release-manager",
}

# Phases skipped by default ("level-default") for lightweight projects.
LEVEL_DEFAULT_SKIPS = {
    "L0": {"plan", "release", "evolve"},
    "L1": {"plan", "release", "evolve"},
    "L2": set(),
    "L3": set(),
}

SANCHO_DIR = ".sancho"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def find_root(start: Optional[Path] = None) -> Optional[Path]:
    """Return the nearest directory (upwards) containing .sancho/, or None."""
    here = (start or Path.cwd()).resolve()
    for d in [here, *here.parents]:
        if (d / SANCHO_DIR).is_dir():
            return d
    return None


def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)


def write_text(path: Path, text: str, encoding: str = "utf-8", newline: str = "\n") -> None:
    """Path.write_text with a newline argument that also works on Python 3.9."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding=encoding, newline=newline) as fh:
        fh.write(text)


def die(msg: str, code: int = 2) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def configure_stdout() -> None:
    """Make UTF-8 output safe on Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
