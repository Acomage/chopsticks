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