from __future__ import annotations

import argparse
from typing import List

from ..core.depsolver import resolve_install_order, resolve_uninstall_order
from ..core.executor import Executor
from ..core.state import State
from ..repo.loader import load_package


def cmd_list(_: argparse.Namespace) -> int:
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

    plan = resolve_install_order(
        targets, lookup, {k: v.version for k, v in st.installed.items()}
    )
    if not plan:
        print("All targets are up-to-date.")
        return 0

    ex = Executor()
    for pkg, op in plan:
        print(
            f"Installing {pkg.name}-{pkg.version}"
            if op == "install"
            else f"Updating {pkg.name}-{pkg.version}"
        )
        actions = pkg.install if op == "install" else pkg.update
        if args.dry_run:
            for a in actions:
                print(
                    f"  DRY-RUN: {a.__class__.__name__} -> {getattr(a, 'describe', lambda: '')()}"
                )
            # st.mark_installed(pkg.name, pkg.version)
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
        if args.dry_run:
            for a in actions:
                print(
                    f"  DRY-RUN: {a.__class__.__name__} -> {getattr(a, 'describe', lambda: '')()}"
                )
            # st.mark_uninstalled(pkg.name)
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

    st = State()
    st.load()

    # When no explicit targets provided, update all installed packages
    if not targets:
        targets = sorted(st.installed.keys())
        if not targets:
            print("No packages installed.")
            return 0

    def lookup(n: str):
        return load_package(n)

    plan = resolve_install_order(
        targets, lookup, {k: v.version for k, v in st.installed.items()}
    )
    # Filter only updates (or installs if not installed to get on latest)
    plan = [(p, op) for (p, op) in plan if op in ("update", "install")]
    if not plan:
        print("All targets are up-to-date.")
        return 0

    ex = Executor()
    for pkg, op in plan:
        print(
            f"Updating {pkg.name}-{pkg.version}"
            if op == "update"
            else f"Installing {pkg.name}-{pkg.version}"
        )
        actions = pkg.update if op == "update" else pkg.install
        if args.dry_run:
            for a in actions:
                print(
                    f"  DRY-RUN: {a.__class__.__name__} -> {getattr(a, 'describe', lambda: '')()}"
                )
            # st.mark_installed(pkg.name, pkg.version)
            continue
        ok, msg = ex.run(actions)
        if not ok:
            print(msg)
            return 1
        st.mark_installed(pkg.name, pkg.version)

    st.save()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chopsticks", description="Chopsticks, help you for your rice"
    )
    sub = p.add_subparsers(dest="command")
    p.add_argument(
        "--dry-run", action="store_true", help="Print actions without executing"
    )

    sp_list = sub.add_parser("list", help="List installed packages")
    sp_list.set_defaults(func=cmd_list)

    sp_install = sub.add_parser("install", help="Install packages")
    sp_install.add_argument("packages", nargs="+", help="Package names")
    sp_install.set_defaults(func=cmd_install)

    sp_un = sub.add_parser("uninstall", help="Uninstall packages")
    sp_un.add_argument("packages", nargs="+", help="Package names")
    sp_un.set_defaults(func=cmd_uninstall)

    sp_up = sub.add_parser("update", help="Update packages to latest")
    # Accept zero or more packages; when zero, update all installed
    sp_up.add_argument("packages", nargs="*", help="Package names")
    sp_up.set_defaults(func=cmd_update)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return int(args.func(args) or 0)
