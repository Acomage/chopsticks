from __future__ import annotations

import shutil
import subprocess


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

