Copilot

Step 1: Minimal runnable demo (install + list)

```python path=/home/acomage/workspace/chopsticks/configmgr/__init__.py start_line=1 end_line=200
"""
configmgr package initializer.

Also exposes a compatibility alias so user pkg.py can do:
from core.package import Package
from core.action import RunCommand
"""
from __future__ import annotations

import importlib
import sys

# Expose "core" namespace as an alias of "configmgr.core"
if "core" not in sys.modules:
    core_pkg = importlib.import_module("configmgr.core")
    sys.modules["core"] = core_pkg

# Also ensure submodules resolve correctly when importing "core.something"
for sub in ("action", "package", "executor", "state", "depsolver", "errors"):
    full = f"configmgr.core.{sub}"
    try:
        mod = importlib.import_module(full)
        sys.modules[f"core.{sub}"] = mod
    except ModuleNotFoundError:
        pass
```

```python path=/home/acomage/workspace/chopsticks/configmgr/config.py start_line=1 end_line=200
from __future__ import annotations

import os
from pathlib import Path

# Directory where packages (the external repo with pkg.py) are located.
# By default, use "<cwd>/repo" to match the example.
REPO_DIR = Path(os.environ.get("CONFIGMGR_REPO", Path.cwd() / "repo")).resolve()

# State file path (installed packages)
STATE_FILE = Path(os.environ.get("CONFIGMGR_STATE", Path.cwd() / ".configmgr_state.json")).resolve()

# Runtime behavior
DRY_RUN = bool(int(os.environ.get("CONFIGMGR_DRY_RUN", "0")))

# Command execution defaults
SHELL_ENV = os.environ.copy()
```

```python path=/home/acomage/workspace/chopsticks/configmgr/core/errors.py start_line=1 end_line=200
from __future__ import annotations


class ConfigMgrError(Exception):
    pass


class PackageNotFoundError(ConfigMgrError):
    def __init__(self, name: str):
        super().__init__(f"Package not found: {name}")
        self.name = name


class InvalidPackageError(ConfigMgrError):
    pass


class ActionError(ConfigMgrError):
    pass


class ExecutionError(ConfigMgrError):
    pass


class DependencyError(ConfigMgrError):
    pass
```

```python path=/home/acomage/workspace/chopsticks/configmgr/core/package.py start_line=1 end_line=200
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence


@dataclass(slots=True)
class Package:
    name: str
    version: str
    dependencies: List[str] = field(default_factory=list)
    install: Sequence[object] = field(default_factory=list)
    uninstall: Sequence[object] = field(default_factory=list)
    update: Sequence[object] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Package.name must be non-empty str")
        if not self.version or not isinstance(self.version, str):
            raise ValueError("Package.version must be non-empty str")
        self.dependencies = list(self.dependencies or [])
        # Actions are opaque objects implementing Action protocol (check/run/rollback)
```

```python path=/home/acomage/workspace/chopsticks/configmgr/core/action.py start_line=1 end_line=400
from __future__ import annotations

import shlex
import subprocess
from abc import ABC, abstractmethod
from typing import Optional, Sequence

from ..config import SHELL_ENV


class Action(ABC):
    """
    Base Action interface.
    - check(): return True to execute, False to skip
    - run(): execute the action
    - rollback(): revert the action (best-effort)
    """

    @abstractmethod
    def check(self) -> bool:  # precondition, True -> proceed, False -> skip
        ...

    @abstractmethod
    def run(self) -> None:
        ...

    @abstractmethod
    def rollback(self) -> None:
        ...

    def describe(self) -> str:
        return self.__class__.__name__


class RunCommand(Action):
    """
    Run a command without shell. Accepts:
    - cmd: str | Sequence[str]
    """

    def __init__(self, cmd: str | Sequence[str], cwd: Optional[str] = None) -> None:
        if isinstance(cmd, str):
            self.cmd: Sequence[str] = shlex.split(cmd)
        else:
            self.cmd = list(cmd)
        self.cwd = cwd

    def check(self) -> bool:
        return True

    def run(self) -> None:
        subprocess.run(self.cmd, check=True, cwd=self.cwd, env=SHELL_ENV)

    def rollback(self) -> None:
        # Non-reversible generic command; no-op
        pass

    def describe(self) -> str:
        return f"RunCommand({shlex.join(self.cmd)})"


class RunShell(Action):
    """
    Run a command via shell=True.
    """

    def __init__(self, script: str, cwd: Optional[str] = None) -> None:
        self.script = script
        self.cwd = cwd

    def check(self) -> bool:
        return True

    def run(self) -> None:
        subprocess.run(self.script, shell=True, check=True, cwd=self.cwd, env=SHELL_ENV)

    def rollback(self) -> None:
        pass

    def describe(self) -> str:
        return f"RunShell({self.script})"
```

```python path=/home/acomage/workspace/chopsticks/configmgr/core/executor.py start_line=1 end_line=200
from __future__ import annotations

from typing import Iterable, List, Tuple

from .action import Action
from .errors import ExecutionError


class Executor:
    """
    Execute actions with rollback on failure.
    - If action.check() returns False, it will be skipped.
    """

    def __init__(self) -> None:
        self._applied: List[Action] = []

    def run(self, actions: Iterable[Action]) -> Tuple[bool, str]:
        self._applied.clear()
        for act in actions:
            try:
                if not act.check():
                    continue
                act.run()
                self._applied.append(act)
            except Exception as e:
                # rollback in reverse
                for done in reversed(self._applied):
                    try:
                        done.rollback()
                    except Exception:
                        pass
                return False, f"Action failed: {act.describe()}: {e}"
        return True, "ok"
```

```python path=/home/acomage/workspace/chopsticks/configmgr/core/state.py start_line=1 end_line=200
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from ..config import STATE_FILE


@dataclass(slots=True)
class InstalledInfo:
    version: str
    installed_at: str


class State:
    def __init__(self, path: Path = STATE_FILE) -> None:
        self.path = path
        self.installed: Dict[str, InstalledInfo] = {}

    def load(self) -> None:
        if not self.path.exists():
            self.installed = {}
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.installed = {
            name: InstalledInfo(**info) for name, info in data.get("installed", {}).items()
        }

    def save(self) -> None:
        data = {
            "installed": {
                name: {"version": info.version, "installed_at": info.installed_at}
                for name, info in self.installed.items()
            }
        }
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def mark_installed(self, name: str, version: str) -> None:
        self.installed[name] = InstalledInfo(
            version=version, installed_at=datetime.now(timezone.utc).isoformat()
        )

    def mark_uninstalled(self, name: str) -> None:
        self.installed.pop(name, None)
```

```python path=/home/acomage/workspace/chopsticks/configmgr/core/depsolver.py start_line=1 end_line=220
from __future__ import annotations

from typing import Callable, Dict, List, Set, Tuple

from .package import Package


Op = str  # "install" | "update" | "skip"


def resolve_install_order(
    targets: List[str],
    repo_lookup: Callable[[str], Package],
    installed: Dict[str, str],
) -> List[Tuple[Package, Op]]:
    """
    Return a topo-sorted list of (Package, op) for install/update.
    - If package not installed: op="install"
    - If installed with different version: op="update"
    - If installed with same version: op="skip" (not returned)
    """
    graph: Dict[str, Package] = {}
    visiting: Set[str] = set()
    visited: Set[str] = set()
    order: List[str] = []

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"Cycle detected at {name}")
        visiting.add(name)
        pkg = graph.get(name)
        if pkg is None:
            pkg = repo_lookup(name)
            graph[name] = pkg
        for dep in pkg.dependencies:
            visit(dep)
        visiting.remove(name)
        visited.add(name)
        order.append(name)

    for t in targets:
        visit(t)

    result: List[Tuple[Package, Op]] = []
    for name in order:
        pkg = graph[name]
        cur = installed.get(name)
        if cur is None:
            result.append((pkg, "install"))
        elif cur != pkg.version:
            result.append((pkg, "update"))
        else:
            # Up-to-date; skip
            pass
    return result
```

```python path=/home/acomage/workspace/chopsticks/configmgr/repo/loader.py start_line=1 end_line=220
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
```

```python path=/home/acomage/workspace/chopsticks/configmgr/cli/main.py start_line=1 end_line=320
from __future__ import annotations

import argparse
from typing import List

from ..config import DRY_RUN
from ..core.depsolver import resolve_install_order
from ..core.executor import Executor
from ..core.state import State
from ..repo.loader import load_package


def cmd_list(args: argparse.Namespace) -> int:
    st = State()
    st.load()
    if not st.installed:
        print("No packages installed.")
        return 0
    for name, info in sorted(st.installed.items()):
        print(f"{name} {info.version} {info.installed_at}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    targets: List[str] = args.packages
    if not targets:
        print("Nothing to install.")
        return 0

    st = State()
    st.load()

    def lookup(n: str):
        return load_package(n)

    plan = resolve_install_order(targets, lookup, {k: v.version for k, v in st.installed.items()})
    if not plan:
        print("All targets are up-to-date.")
        return 0

    ex = Executor()
    for pkg, op in plan:
        print(f"Installing {pkg.name}-{pkg.version}" if op == "install" else f"Updating {pkg.name}-{pkg.version}")
        actions = pkg.install if op == "install" else pkg.update
        if DRY_RUN:
            for a in actions:
                print(f"  DRY-RUN: {a.__class__.__name__} -> {getattr(a, 'describe', lambda: '')()}")
            st.mark_installed(pkg.name, pkg.version)
            continue
        ok, msg = ex.run(actions)
        if not ok:
            print(msg)
            return 1
        # success
        st.mark_installed(pkg.name, pkg.version)

    st.save()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="configmgr", description="Lightweight config/package manager")
    sub = p.add_subparsers(dest="command")

    sp_list = sub.add_parser("list", help="List installed packages")
    sp_list.set_defaults(func=cmd_list)

    sp_install = sub.add_parser("install", help="Install packages")
    sp_install.add_argument("packages", nargs="+", help="Package names")
    sp_install.set_defaults(func=cmd_install)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return int(args.func(args) or 0)
```

```python path=/home/acomage/workspace/chopsticks/configmgr/__main__.py start_line=1 end_line=40
from __future__ import annotations

import sys

from .cli.main import main

if __name__ == "__main__":
    sys.exit(main())
```

Step 2: Extend to full functionality (all modules and actions)

```python path=/home/acomage/workspace/chopsticks/configmgr/utils/fs.py start_line=1 end_line=260
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
```

```python path=/home/acomage/workspace/chopsticks/configmgr/utils/sysutils.py start_line=1 end_line=220
from __future__ import annotations

import shutil
import subprocess
from typing import Optional


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run_systemctl(action: str, unit: str) -> None:
    if not have("systemctl"):
        raise RuntimeError("systemctl not found")
    subprocess.run(["systemctl", action, unit], check=True)


def run_ufw(action: str, spec: str) -> None:
    if not have("ufw"):
        raise RuntimeError("ufw not found")
    subprocess.run(["ufw", action, spec], check=True, input=b"y\n")
```

```python path=/home/acomage/workspace/chopsticks/configmgr/repo/gitutils.py start_line=1 end_line=220
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def git(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *cmd], cwd=str(cwd), check=check, capture_output=True, text=True)


def pull(repo_dir: Path) -> str:
    cp = git(["pull", "--ff-only"], cwd=repo_dir)
    return cp.stdout.strip()


def show(repo_dir: Path, rev: str, path: str) -> str:
    cp = git(["show", f"{rev}:{path}"], cwd=repo_dir)
    return cp.stdout
```

```python path=/home/acomage/workspace/chopsticks/configmgr/core/action.py start_line=1 end_line=500
from __future__ import annotations

import os
import shlex
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Sequence

from ..config import SHELL_ENV
from ..utils.fs import atomic_write, ensure_dir, is_link_to, read_text
from ..utils.sysutils import run_systemctl, run_ufw


class Action(ABC):
    @abstractmethod
    def check(self) -> bool:
        ...

    @abstractmethod
    def run(self) -> None:
        ...

    @abstractmethod
    def rollback(self) -> None:
        ...

    def describe(self) -> str:
        return self.__class__.__name__


# -------- Command actions --------
class RunCommand(Action):
    def __init__(self, cmd: str | Sequence[str], cwd: Optional[str] = None) -> None:
        if isinstance(cmd, str):
            self.cmd: Sequence[str] = shlex.split(cmd)
        else:
            self.cmd = list(cmd)
        self.cwd = cwd

    def check(self) -> bool:
        return True

    def run(self) -> None:
        subprocess.run(self.cmd, check=True, cwd=self.cwd, env=SHELL_ENV)

    def rollback(self) -> None:
        pass

    def describe(self) -> str:
        return f"RunCommand({shlex.join(self.cmd)})"


class RunShell(Action):
    def __init__(self, script: str, cwd: Optional[str] = None) -> None:
        self.script = script
        self.cwd = cwd

    def check(self) -> bool:
        return True

    def run(self) -> None:
        subprocess.run(self.script, shell=True, check=True, cwd=self.cwd, env=SHELL_ENV)

    def rollback(self) -> None:
        pass

    def describe(self) -> str:
        return f"RunShell({self.script})"


# -------- Filesystem actions --------
class CreateDir(Action):
    def __init__(self, path: str | Path, mode: int = 0o755) -> None:
        self.path = Path(path)
        self.mode = mode
        self.created = False

    def check(self) -> bool:
        return not self.path.exists()

    def run(self) -> None:
        ensure_dir(self.path, mode=self.mode, exist_ok=True)
        self.created = True

    def rollback(self) -> None:
        try:
            if self.created and self.path.exists() and not any(self.path.iterdir()):
                self.path.rmdir()
        except Exception:
            pass


class DeleteDir(Action):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._removed = False

    def check(self) -> bool:
        return self.path.exists()

    def run(self) -> None:
        # Delete empty dir only (safer)
        if self.path.is_dir() and not any(self.path.iterdir()):
            self.path.rmdir()
            self._removed = True

    def rollback(self) -> None:
        if self._removed:
            ensure_dir(self.path, exist_ok=True)


class CreateFile(Action):
    def __init__(self, path: str | Path, content: str, mode: int = 0o644) -> None:
        self.path = Path(path)
        self.content = content
        self.mode = mode
        self._existed = False
        self._backup: Optional[str] = None

    def check(self) -> bool:
        cur = read_text(self.path)
        return cur != self.content

    def run(self) -> None:
        parent = self.path.parent
        ensure_dir(parent, exist_ok=True)
        if self.path.exists():
            self._existed = True
            self._backup = read_text(self.path)
        atomic_write(self.path, self.content.encode("utf-8"), mode=self.mode)

    def rollback(self) -> None:
        try:
            if self._existed:
                atomic_write(self.path, (self._backup or "").encode("utf-8"), mode=self.mode)
            else:
                if self.path.exists():
                    self.path.unlink(missing_ok=True)
        except Exception:
            pass


class DeleteFile(Action):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._backup: Optional[bytes] = None
        self._existed = False

    def check(self) -> bool:
        return self.path.exists()

    def run(self) -> None:
        if self.path.exists() and self.path.is_file():
            self._existed = True
            self._backup = self.path.read_bytes()
            self.path.unlink()

    def rollback(self) -> None:
        if self._existed and self._backup is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(self.path, self._backup)


class CreateLink(Action):
    def __init__(self, link_path: str | Path, target: str | Path) -> None:
        self.link_path = Path(link_path)
        self.target = Path(target)
        self._existed = False
        self._backup: Optional[str] = None

    def check(self) -> bool:
        if is_link_to(self.link_path, self.target):
            return False
        return True

    def run(self) -> None:
        if self.link_path.exists() or self.link_path.is_symlink():
            self._existed = True
            try:
                # If symlink, remember old target for rollback
                if self.link_path.is_symlink():
                    self._backup = os.readlink(self.link_path)
                self.link_path.unlink()
            except FileNotFoundError:
                pass
        self.link_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(self.target, self.link_path)

    def rollback(self) -> None:
        try:
            if self.link_path.is_symlink() or self.link_path.exists():
                self.link_path.unlink(missing_ok=True)
            if self._existed:
                if self._backup is not None:
                    os.symlink(self._backup, self.link_path)
        except Exception:
            pass


class DeleteLink(Action):
    def __init__(self, link_path: str | Path) -> None:
        self.link_path = Path(link_path)
        self._backup: Optional[str] = None
        self._existed = False

    def check(self) -> bool:
        return self.link_path.is_symlink()

    def run(self) -> None:
        if self.link_path.is_symlink():
            self._existed = True
            try:
                self._backup = os.readlink(self.link_path)
            except OSError:
                self._backup = None
            self.link_path.unlink()

    def rollback(self) -> None:
        if self._existed and self._backup:
            try:
                os.symlink(self._backup, self.link_path)
            except Exception:
                pass


class AppendFile(Action):
    def __init__(self, path: str | Path, line: str) -> None:
        self.path = Path(path)
        self.line = line
        self._appended = False

    def check(self) -> bool:
        cur = read_text(self.path)
        if cur is None:
            return True
        return not cur.endswith(self.line + "\n")

    def run(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(self.line + "\n")
        self._appended = True

    def rollback(self) -> None:
        if not self._appended:
            return
        # remove last line if it equals self.line
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            if lines and lines[-1] == self.line:
                lines = lines[:-1]
                atomic_write(self.path, ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8"))
        except Exception:
            pass


class RemoveLastLine(Action):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._backup: Optional[str] = None
        self._changed = False

    def check(self) -> bool:
        return self.path.exists()

    def run(self) -> None:
        if not self.path.exists():
            return
        self._backup = read_text(self.path) or ""
        lines = self._backup.splitlines()
        if not lines:
            return
        lines = lines[:-1]
        atomic_write(self.path, ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8"))
        self._changed = True

    def rollback(self) -> None:
        if self._changed and self._backup is not None:
            atomic_write(self.path, self._backup.encode("utf-8"))


# -------- System / Firewall actions --------
class SystemdStart(Action):
    def __init__(self, unit: str) -> None:
        self.unit = unit

    def check(self) -> bool:
        return True

    def run(self) -> None:
        run_systemctl("start", self.unit)

    def rollback(self) -> None:
        try:
            run_systemctl("stop", self.unit)
        except Exception:
            pass


class SystemdStop(Action):
    def __init__(self, unit: str) -> None:
        self.unit = unit

    def check(self) -> bool:
        return True

    def run(self) -> None:
        run_systemctl("stop", self.unit)

    def rollback(self) -> None:
        try:
            run_systemctl("start", self.unit)
        except Exception:
            pass


class UfwAllow(Action):
    def __init__(self, spec: str) -> None:
        self.spec = spec

    def check(self) -> bool:
        return True

    def run(self) -> None:
        run_ufw("allow", self.spec)

    def rollback(self) -> None:
        try:
            run_ufw("delete", f"allow {self.spec}")
        except Exception:
            pass


class UfwDeny(Action):
    def __init__(self, spec: str) -> None:
        self.spec = spec

    def check(self) -> bool:
        return True

    def run(self) -> None:
        run_ufw("deny", self.spec)

    def rollback(self) -> None:
        try:
            run_ufw("delete", f"deny {self.spec}")
        except Exception:
            pass
```

```python path=/home/acomage/workspace/chopsticks/configmgr/core/executor.py start_line=1 end_line=240
from __future__ import annotations

from typing import Iterable, List, Tuple

from .action import Action
from .errors import ExecutionError


class Executor:
    """
    Execute actions with rollback on failure.
    - If action.check() returns False, it will be skipped.
    """

    def __init__(self) -> None:
        self._applied: List[Action] = []

    def run(self, actions: Iterable[Action]) -> Tuple[bool, str]:
        self._applied.clear()
        for act in actions:
            try:
                if not act.check():
                    continue
                act.run()
                self._applied.append(act)
            except Exception as e:
                for done in reversed(self._applied):
                    try:
                        done.rollback()
                    except Exception:
                        pass
                return False, f"Action failed: {act.describe()}: {e}"
        return True, "ok"
```

```python path=/home/acomage/workspace/chopsticks/configmgr/core/depsolver.py start_line=1 end_line=340
from __future__ import annotations

from typing import Callable, Dict, List, Set, Tuple

from .package import Package


Op = str  # "install" | "update" | "skip" | "uninstall"


def resolve_install_order(
    targets: List[str],
    repo_lookup: Callable[[str], Package],
    installed: Dict[str, str],
) -> List[Tuple[Package, Op]]:
    """
    Return a topo-sorted list of (Package, op) for install/update.
    """
    graph: Dict[str, Package] = {}
    visiting: Set[str] = set()
    visited: Set[str] = set()
    order: List[str] = []

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"Cycle detected at {name}")
        visiting.add(name)
        pkg = graph.get(name)
        if pkg is None:
            pkg = repo_lookup(name)
            graph[name] = pkg
        for dep in pkg.dependencies:
            visit(dep)
        visiting.remove(name)
        visited.add(name)
        order.append(name)

    for t in targets:
        visit(t)

    result: List[Tuple[Package, Op]] = []
    for name in order:
        pkg = graph[name]
        cur = installed.get(name)
        if cur is None:
            result.append((pkg, "install"))
        elif cur != pkg.version:
            result.append((pkg, "update"))
        else:
            pass
    return result


def resolve_uninstall_order(
    targets: List[str],
    repo_lookup: Callable[[str], Package],
    installed: Dict[str, str],
) -> List[Tuple[Package, Op]]:
    """
    Compute safe uninstall order: reverse topological order of the closure of targets.
    Raises if some installed package outside targets depends on targets.
    """
    # Build graph for all installed packages we can load
    graph: Dict[str, Package] = {}
    for name in installed.keys():
        try:
            graph[name] = repo_lookup(name)
        except Exception:
            # If package is unknown in repo, treat as leaf
            graph[name] = Package(name=name, version=installed[name])

    # Check reverse deps
    target_set = set(targets)
    dependents: Dict[str, Set[str]] = {k: set() for k in graph}
    for pkg in graph.values():
        for dep in pkg.dependencies:
            if dep in graph:
                dependents[dep].add(pkg.name)

    # Ensure no outside dependent blocks removal
    for t in target_set:
        for d in dependents.get(t, set()):
            if d not in target_set and d in installed:
                raise ValueError(f"Cannot uninstall {t}: required by installed package {d}")

    # Compute closure (targets + all their deps that are also in targets)
    # For safety we only uninstall exactly requested targets (no autoremove).
    closure = target_set

    # Order: reverse topological among closure
    visited: Set[str] = set()
    order: List[str] = []

    def visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        for dep in graph.get(name, Package(name, installed.get(name, ""), [])).dependencies:
            if dep in closure:
                visit(dep)
        order.append(name)

    for t in closure:
        visit(t)

    order.reverse()
    result: List[Tuple[Package, Op]] = []
    for name in order:
        if name not in installed:
            continue
        pkg = graph.get(name, Package(name, installed[name]))
        result.append((pkg, "uninstall"))
    return result
```

```python path=/home/acomage/workspace/chopsticks/configmgr/cli/main.py start_line=1 end_line=520
from __future__ import annotations

import argparse
from typing import List

from ..config import DRY_RUN
from ..core.depsolver import resolve_install_order, resolve_uninstall_order
from ..core.executor import Executor
from ..core.state import State
from ..repo.loader import load_package


def cmd_list(args: argparse.Namespace) -> int:
    st = State()
    st.load()
    if not st.installed:
        print("No packages installed.")
        return 0
    for name, info in sorted(st.installed.items()):
        print(f"{name} {info.version} {info.installed_at}")
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    targets: List[str] = args.packages
    if not targets:
        print("Nothing to install.")
        return 0

    st = State()
    st.load()

    def lookup(n: str):
        return load_package(n)

    plan = resolve_install_order(targets, lookup, {k: v.version for k, v in st.installed.items()})
    if not plan:
        print("All targets are up-to-date.")
        return 0

    ex = Executor()
    for pkg, op in plan:
        print(f"Installing {pkg.name}-{pkg.version}" if op == "install" else f"Updating {pkg.name}-{pkg.version}")
        actions = pkg.install if op == "install" else pkg.update
        if DRY_RUN:
            for a in actions:
                print(f"  DRY-RUN: {a.__class__.__name__} -> {getattr(a, 'describe', lambda: '')()}")
            st.mark_installed(pkg.name, pkg.version)
            continue
        ok, msg = ex.run(actions)
        if not ok:
            print(msg)
            return 1
        st.mark_installed(pkg.name, pkg.version)

    st.save()
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    targets: List[str] = args.packages
    if not targets:
        print("Nothing to uninstall.")
        return 0

    st = State()
    st.load()
    installed = {k: v.version for k, v in st.installed.items()}
    missing = [t for t in targets if t not in installed]
    if missing:
        print(f"Not installed: {', '.join(missing)}")
        return 1

    def lookup(n: str):
        return load_package(n)

    try:
        plan = resolve_uninstall_order(targets, lookup, installed)
    except Exception as e:
        print(str(e))
        return 1

    ex = Executor()
    for pkg, _ in plan:
        print(f"Uninstalling {pkg.name}-{installed[pkg.name]}")
        actions = pkg.uninstall
        if DRY_RUN:
            for a in actions:
                print(f"  DRY-RUN: {a.__class__.__name__} -> {getattr(a, 'describe', lambda: '')()}")
            st.mark_uninstalled(pkg.name)
            continue
        ok, msg = ex.run(actions)
        if not ok:
            print(msg)
            return 1
        st.mark_uninstalled(pkg.name)

    st.save()
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    targets: List[str] = args.packages
    if not targets:
        print("Nothing to update.")
        return 0

    st = State()
    st.load()

    def lookup(n: str):
        return load_package(n)

    plan = resolve_install_order(targets, lookup, {k: v.version for k, v in st.installed.items()})
    # Filter only updates (or installs if not installed to get on latest)
    plan = [(p, op) for (p, op) in plan if op in ("update", "install")]
    if not plan:
        print("All targets are up-to-date.")
        return 0

    ex = Executor()
    for pkg, op in plan:
        print(f"Updating {pkg.name}-{pkg.version}" if op == "update" else f"Installing {pkg.name}-{pkg.version}")
        actions = pkg.update if op == "update" else pkg.install
        if DRY_RUN:
            for a in actions:
                print(f"  DRY-RUN: {a.__class__.__name__} -> {getattr(a, 'describe', lambda: '')()}")
            st.mark_installed(pkg.name, pkg.version)
            continue
        ok, msg = ex.run(actions)
        if not ok:
            print(msg)
            return 1
        st.mark_installed(pkg.name, pkg.version)

    st.save()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="configmgr", description="Lightweight config/package manager")
    sub = p.add_subparsers(dest="command")

    sp_list = sub.add_parser("list", help="List installed packages")
    sp_list.set_defaults(func=cmd_list)

    sp_install = sub.add_parser("install", help="Install packages")
    sp_install.add_argument("packages", nargs="+", help="Package names")
    sp_install.set_defaults(func=cmd_install)

    sp_un = sub.add_parser("uninstall", help="Uninstall packages")
    sp_un.add_argument("packages", nargs="+", help="Package names")
    sp_un.set_defaults(func=cmd_uninstall)

    sp_up = sub.add_parser("update", help="Update packages to latest")
    sp_up.add_argument("packages", nargs="+", help="Package names")
    sp_up.set_defaults(func=cmd_update)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return int(args.func(args) or 0)
```

Usage

- Create your packages repo at ./repo, e.g.:
  - mkdir -p repo/python
  - echo a pkg.py similar to the example into repo/python/pkg.py
- Run:
  - python -m configmgr install nginx
  - python -m configmgr list
- Optional environment variables:
  - CONFIGMGR_REPO=/path/to/repo
  - CONFIGMGR_STATE=/path/to/state.json
  - CONFIGMGR_DRY_RUN=1 for dry runs

Linux-specific actions (systemctl/ufw) require systemctl or ufw present.

## User (99cd1032-3cf7-4715-b3a0-42df63fdbcf5)───
