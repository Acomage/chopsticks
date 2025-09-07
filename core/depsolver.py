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