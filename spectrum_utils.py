# -*- coding: utf-8 -*-
"""Small shared utilities that are not tied to audio analysis or rendering."""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys

import numpy as np

from spectrum_types import RGB, LogFn


def runtime_app_dir() -> Path:
    """Return the directory where app-side resources are expected.

    Source/Python run:
        directory containing this module.

    PyInstaller frozen run:
        directory containing the executable.  This allows a sibling `bin`
        folder next to the EXE.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def _tool_names(name: str) -> list[str]:
    names = [str(name)]
    if os.name == "nt" and not str(name).lower().endswith(".exe"):
        names.insert(0, f"{name}.exe")
    return list(dict.fromkeys(names))

def find_external_tool(name: str) -> Path | None:
    """Find an external executable.

    Lookup order:
    1. `<app dir>/bin/<name>` or `<app dir>/bin/<name>.exe`
    2. System PATH
    """
    bin_dir = runtime_app_dir() / "bin"
    for tool_name in _tool_names(name):
        candidate = bin_dir / tool_name
        if candidate.is_file():
            return candidate

    for tool_name in _tool_names(name):
        found = shutil.which(tool_name)
        if found:
            return Path(found)

    return None

def resolve_external_tool(name: str) -> str:
    """Return the executable path for subprocess calls, falling back to name."""
    found = find_external_tool(name)
    return str(found) if found is not None else str(name)

def no_window_subprocess_kwargs() -> dict[str, int]:
    """Return subprocess kwargs that suppress console windows on Windows.

    PyInstaller --windowed builds can otherwise flash a black console window
    whenever ffmpeg/ffprobe is started.  Non-Windows platforms keep the default
    subprocess behavior by receiving no extra keyword arguments.
    """
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def log(message: str, callback: LogFn = None) -> None:
    if callback:
        callback(message)
    else:
        print(message, flush=True)

def parse_color(value: str | None, default: RGB = (0, 0, 0)) -> RGB:
    if value is None or str(value).strip() == "":
        return default
    text = str(value).strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        raise ValueError(f"Invalid color: {value}. Use #RRGGBB.")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))

def color_to_hex(color: RGB) -> str:
    return "#%02X%02X%02X" % tuple(int(np.clip(c, 0, 255)) for c in color)

def unique_path(path: Path) -> Path:
    """Return a non-existing path by appending ' (1)', ' (2)', ... if needed."""
    path = Path(path)
    if not path.exists():
        return path
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    for i in range(1, 10000):
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create a unique filename for: {path}")
