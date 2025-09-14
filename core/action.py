from __future__ import annotations

import os
import shlex
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Sequence

from ..config import SHELL_ENV, INSTALL_PACKAGR
from ..utils.fs import atomic_write, ensure_dir, is_link_to, read_text
from ..utils.sysutils import run_systemctl, run_ufw


class Action(ABC):
    @abstractmethod
    def check(self) -> bool: ...

    @abstractmethod
    def run(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

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
        return f"run command: {shlex.join(self.cmd)}"


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
                atomic_write(
                    self.path, (self._backup or "").encode("utf-8"), mode=self.mode
                )
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
                atomic_write(
                    self.path,
                    ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8"),
                )
        except Exception:
            pass


class EnsureLinePresent(Action):
    """Ensure a line exists somewhere in the file; append if missing.

    - Idempotent: does nothing if the exact line already exists (compared without trailing newline).
    - Rollback: if the action appended the line, remove the last occurrence.
    """

    def __init__(self, path: str | Path, line: str) -> None:
        self.path = Path(path)
        self.line = line.rstrip("\n")
        self._appended = False

    def check(self) -> bool:
        content = read_text(self.path)
        if content is None:
            return True
        for ln in content.splitlines():
            if ln == self.line:
                return False
        return True

    def run(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = read_text(self.path)
        except Exception:
            content = None
        if content is None or content == "":
            new_content = self.line + "\n"
        else:
            # ensure file ends with newline before appending
            if not content.endswith("\n"):
                new_content = content + "\n" + self.line + "\n"
            else:
                new_content = content + self.line + "\n"
        atomic_write(self.path, new_content.encode("utf-8"))
        self._appended = True

    def rollback(self) -> None:
        if not self._appended:
            return
        try:
            content = read_text(self.path)
            if content is None:
                return
            lines = content.splitlines()
            # remove the last occurrence of the line we appended
            for i in range(len(lines) - 1, -1, -1):
                if lines[i] == self.line:
                    del lines[i]
                    break
            atomic_write(
                self.path, ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
            )
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
        atomic_write(
            self.path, ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        )
        self._changed = True

    def rollback(self) -> None:
        if self._changed and self._backup is not None:
            atomic_write(self.path, self._backup.encode("utf-8"))


class EnsureLineAbsent(Action):
    """Ensure a specific line is absent from the file; remove if present.

    By default removes all occurrences of the exact line (without trailing newline).
    """

    def __init__(self, path: str | Path, line: str, remove_all: bool = True) -> None:
        self.path = Path(path)
        self.line = line.rstrip("\n")
        self.remove_all = remove_all
        self._backup: Optional[str] = None

    def check(self) -> bool:
        content = read_text(self.path)
        if content is None:
            return False
        return any(ln == self.line for ln in content.splitlines())

    def run(self) -> None:
        content = read_text(self.path)
        if content is None:
            return
        self._backup = content
        lines = content.splitlines()
        if self.remove_all:
            new_lines = [ln for ln in lines if ln != self.line]
        else:
            # remove only the last occurrence
            new_lines = lines[:]
            for i in range(len(new_lines) - 1, -1, -1):
                if new_lines[i] == self.line:
                    del new_lines[i]
                    break
        if new_lines == lines:
            return
        atomic_write(
            self.path,
            ("\n".join(new_lines) + ("\n" if new_lines else "")).encode("utf-8"),
        )

    def rollback(self) -> None:
        if self._backup is None:
            return
        try:
            atomic_write(self.path, self._backup.encode("utf-8"))
        except Exception:
            pass


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


class EnsureBlockPresent(Action):
    """Ensure a managed block (between BEGIN/END markers) exists and equals given content.

    The block is marked by lines like:
      <prefix> BEGIN MANAGED:{key}
      ...content...
      <prefix> END MANAGED:{key}

    - Idempotent: if existing block content equals, do nothing.
    - If block exists but differs: replace the block.
    - If block doesn't exist: append the block at end (with a leading newline when needed).
    - Rollback: restore the original file content.
    """

    def __init__(
        self, path: str | Path, key: str, content: str, comment_prefix: str = "#"
    ) -> None:
        self.path = Path(path)
        self.key = key
        self.content = content.rstrip("\n")
        self.prefix = comment_prefix
        self._existed = False
        self._backup: Optional[str] = None

    def _find_block(self, text: str) -> tuple[int, int] | None:
        begin = f"{self.prefix} BEGIN MANAGED:{self.key}"
        end = f"{self.prefix} END MANAGED:{self.key}"
        lines = text.splitlines()
        start_idx = -1
        for i, ln in enumerate(lines):
            if ln.strip() == begin:
                start_idx = i
                break
        if start_idx == -1:
            return None
        for j in range(start_idx + 1, len(lines)):
            if lines[j].strip() == end:
                return start_idx, j
        # malformed (begin without end) -> treat as no block
        return None

    def check(self) -> bool:
        cur = read_text(self.path)
        if cur is None:
            return True
        rng = self._find_block(cur)
        if rng is None:
            return True
        i, j = rng
        lines = cur.splitlines()
        current_block = "\n".join(lines[i + 1 : j]).rstrip("\n")
        return current_block != self.content

    def run(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        cur = read_text(self.path)
        if cur is None:
            cur = ""
            self._existed = False
        else:
            self._existed = True
        self._backup = cur

        begin = f"{self.prefix} BEGIN MANAGED:{self.key}"
        end = f"{self.prefix} END MANAGED:{self.key}"
        lines = cur.splitlines()
        rng = self._find_block(cur)
        block_lines = [begin, *self.content.splitlines(), end]

        if rng is None:
            # append block to end, keep one trailing newline
            if cur and not cur.endswith("\n"):
                new_text = cur + "\n" + "\n".join(block_lines) + "\n"
            else:
                new_text = (
                    cur
                    + ("" if cur.endswith("\n") else "")
                    + "\n".join(block_lines)
                    + "\n"
                )
        else:
            i, j = rng
            new_lines = lines[:i] + block_lines + lines[j + 1 :]
            new_text = "\n".join(new_lines) + "\n"

        atomic_write(self.path, new_text.encode("utf-8"))

    def rollback(self) -> None:
        if self._backup is None:
            return
        try:
            atomic_write(self.path, self._backup.encode("utf-8"))
        except Exception:
            pass


class EnsureBlockAbsent(Action):
    """Ensure a managed block (BEGIN/END markers) for the given key is absent.

    If the block exists, remove it. Otherwise, do nothing. Rollback restores the original file.
    """

    def __init__(self, path: str | Path, key: str, comment_prefix: str = "#") -> None:
        self.path = Path(path)
        self.key = key
        self.prefix = comment_prefix
        self._backup: Optional[str] = None

    def _find_block(self, text: str) -> tuple[int, int] | None:
        begin = f"{self.prefix} BEGIN MANAGED:{self.key}"
        end = f"{self.prefix} END MANAGED:{self.key}"
        lines = text.splitlines()
        start_idx = -1
        for i, ln in enumerate(lines):
            if ln.strip() == begin:
                start_idx = i
                break
        if start_idx == -1:
            return None
        for j in range(start_idx + 1, len(lines)):
            if lines[j].strip() == end:
                return start_idx, j
        return None

    def check(self) -> bool:
        cur = read_text(self.path)
        if cur is None:
            return False
        return self._find_block(cur) is not None

    def run(self) -> None:
        cur = read_text(self.path)
        if cur is None:
            return
        self._backup = cur
        lines = cur.splitlines()
        rng = self._find_block(cur)
        if rng is None:
            return
        i, j = rng
        new_lines = lines[:i] + lines[j + 1 :]
        atomic_write(
            self.path,
            ("\n".join(new_lines) + ("\n" if new_lines else "")).encode("utf-8"),
        )

    def rollback(self) -> None:
        if self._backup is None:
            return
        try:
            atomic_write(self.path, self._backup.encode("utf-8"))
        except Exception:
            pass


class PacmanInstall(Action):
    def __init__(self, packages: Sequence[str]) -> None:
        self.packages = list(packages)
        self.need_to_install = []

    def is_installed(self, pkg: str) -> bool:
        cmd = ["pacman", "-Qq", pkg]
        result = subprocess.run(cmd, capture_output=True, text=True, env=SHELL_ENV)
        return result.stdout.strip() == pkg

    def check(self) -> bool:
        for pkg in self.packages:
            if not self.is_installed(pkg):
                self.need_to_install.append(pkg)
        if self.need_to_install:
            return True
        return False

    def run(self) -> None:
        if not self.packages:
            return
        for pkg in self.need_to_install:
            cmd = ["sudo", "pacman", "-S", "--needed", pkg]
            subprocess.run(cmd, check=True, env=SHELL_ENV)
            INSTALL_PACKAGR.parent.mkdir(parents=True, exist_ok=True)
            try:
                content = read_text(INSTALL_PACKAGR)
            except Exception:
                content = None
            if content is None or content == "":
                new_content = pkg + "\n"
            else:
                # ensure file ends with newline before appending
                if not content.endswith("\n"):
                    new_content = content + "\n" + pkg + "\n"
                else:
                    new_content = content + pkg + "\n"
            atomic_write(INSTALL_PACKAGR, new_content.encode("utf-8"))

    def rollback(self) -> None:
        try:
            content = read_text(INSTALL_PACKAGR)
        except Exception:
            content = None
        installed = content.splitlines() if content else []
        for pkg in self.need_to_install:
            if pkg in installed:
                installed.remove(pkg)
                cmd = ["sudo pacman", "-Rns", pkg]
                subprocess.run(cmd, check=True, env=SHELL_ENV)
        atomic_write(
            INSTALL_PACKAGR,
            ("\n".join(installed) + ("\n" if installed else "")).encode("utf-8"),
        )

    def describe(self) -> str:
        return f"pacman install {', '.join(self.packages)}"


class PacmanUninstall(Action):
    def __init__(self, packages: Sequence[str]) -> None:
        self.packages = list(packages)
        self.need_to_remove = []

    def check(self) -> bool:
        try:
            content = read_text(INSTALL_PACKAGR)
        except Exception:
            content = None
        installed = content.splitlines() if content else []
        for pkg in self.packages:
            if pkg in installed:
                self.need_to_remove.append(pkg)
        return True if self.need_to_remove else False

    def run(self) -> None:
        for pkg in self.need_to_remove:
            cmd = ["sudo", "pacman", "-Rns", pkg]
            subprocess.run(cmd, check=True, env=SHELL_ENV)
            try:
                content = read_text(INSTALL_PACKAGR)
            except Exception:
                content = None
            installed = content.splitlines() if content else []
            if pkg in installed:
                installed.remove(pkg)
                atomic_write(
                    INSTALL_PACKAGR,
                    ("\n".join(installed) + ("\n" if installed else "")).encode(
                        "utf-8"
                    ),
                )

    def rollback(self) -> None:
        try:
            content = read_text(INSTALL_PACKAGR)
        except Exception:
            content = None
        installed = content.splitlines() if content else []
        for pkg in self.need_to_remove:
            if pkg not in installed:
                cmd = ["sudo", "pacman", "-S", "--needed", pkg]
                subprocess.run(cmd, check=True, env=SHELL_ENV)
                installed.append(pkg)
        atomic_write(
            INSTALL_PACKAGR,
            ("\n".join(installed) + ("\n" if installed else "")).encode("utf-8"),
        )

    def describe(self) -> str:
        return f"pacman uninstall {', '.join(self.packages)}"
