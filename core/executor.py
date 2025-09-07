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