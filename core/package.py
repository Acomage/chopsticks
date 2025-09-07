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