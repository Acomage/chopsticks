from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import ModuleType

from ..config import REPO_DIR
from ..core.errors import InvalidPackageError, PackageNotFoundError
from ..core.package import Package


def _ensure_core_alias() -> None:
    # Handled in configmgr.__init__, but ensure alias exists when loader is used standalone
    if "core" not in sys.modules:
        import importlib

        core_pkg: ModuleType = importlib.import_module("configmgr.core")
        sys.modules["core"] = core_pkg


def repo_dir() -> Path:
    return REPO_DIR


def load_package(name: str) -> Package:
    """
    Load a Package object from <REPO_DIR>/<name>/pkg.py expecting `pkg`.
    """
    base = repo_dir()
    pkg_file = base / name / "pkg.py"
    if not pkg_file.exists():
        raise PackageNotFoundError(name)

    _ensure_core_alias()
    # Ensure project root (containing configmgr) is in sys.path for imports
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    globs = runpy.run_path(str(pkg_file))
    obj = globs.get("pkg")
    if not isinstance(obj, Package):
        raise InvalidPackageError(f"{pkg_file} must define `pkg: Package`")
    return obj