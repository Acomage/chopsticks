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