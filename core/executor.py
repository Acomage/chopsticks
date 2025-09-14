from __future__ import annotations

from typing import Iterable
import sys

from .action import Action


def query_before_action(act: Action) -> bool:
    while True:
        prompt = f"Run: {act.describe()}. Proceed? [y/N]: "
        input_str = input(prompt).strip().lower()
        match input_str:
            case "y" | "yes":
                return True
            case "n" | "no" | "":
                return False
            case _:
                print("Invalid input. Please enter `y` or `n`.")


def deal_with_failure(act: Action, ex: Exception) -> bool:
    rollback_succeeded = False
    while True:
        print(f"Action failed: {act.describe()}: {ex}", file=sys.stderr)
        try:
            act.rollback()
            rollback_succeeded = True
        except Exception as rex:
            print(f"Action rollback failed: {act.describe()}", file=sys.stderr)
            print(f"{rex}", file=sys.stderr)
        prompt = f"""The action {act.describe()} failed and rolled back{"" if rollback_succeeded else " failed"}.
if you want to deal with errors and rerun it, press `r` after fixing the issue.
if you want to run it manully and skip it in here, press `s`.
(hint: you can open another terminal to fix the issue) [r/s]: """
        input_str = input(prompt).strip().lower()
        match input_str:
            case "r":
                return True
            case "s":
                return False
            case _:
                print("Invalid input. Please enter `r` or `s`.")


def run_action(act: Action) -> None:
    while True:
        try:
            act.run()
            return  # Success, exit the loop
        except Exception as e:
            if not deal_with_failure(act, e):
                return  # User chose to skip, exit the loop


class Executor:
    """
    Execute actions with rollback on failure.
    - If action.check() returns False, it will be skipped.
    """

    def __init__(self) -> None:
        pass

    def run(self, actions: Iterable[Action], no_confirm: bool = False) -> None:
        for act in actions:
            if not act.check():
                continue
            if no_confirm:
                run_action(act)
                continue
            if not query_before_action(act):
                print(f"Skipping action: {act.describe()}")
                continue
            run_action(act)
