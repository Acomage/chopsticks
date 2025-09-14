from __future__ import annotations

import subprocess
from pathlib import Path


def git(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *cmd], cwd=str(cwd), check=check, capture_output=True, text=True
    )


def pull(repo_dir: Path) -> str:
    cp = git(["pull", "--ff-only"], cwd=repo_dir)
    return cp.stdout.strip()


def show(repo_dir: Path, rev: str, path: str) -> str:
    cp = git(["show", f"{rev}:{path}"], cwd=repo_dir)
    return cp.stdout

