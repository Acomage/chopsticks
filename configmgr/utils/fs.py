from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional


def ensure_dir(path: Path, mode: int = 0o755, exist_ok: bool = True) -> None:
    path.mkdir(parents=True, exist_ok=exist_ok)
    if mode is not None:
        os.chmod(path, mode)


def atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    if mode is not None:
        os.chmod(path, mode)


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def is_link_to(path: Path, target: Path) -> bool:
    try:
        return path.is_symlink() and Path(os.readlink(path)) == target
    except OSError:
        return False


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)