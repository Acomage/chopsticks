"""
configmgr package initializer.

Also exposes a compatibility alias so user pkg.py can do:
from core.package import Package
from core.action import RunCommand
"""
from __future__ import annotations

import importlib
import sys

# Expose "core" namespace as an alias of "configmgr.core"
if "core" not in sys.modules:
    core_pkg = importlib.import_module("configmgr.core")
    sys.modules["core"] = core_pkg

# Also ensure submodules resolve correctly when importing "core.something"
for sub in ("action", "package", "executor", "state", "depsolver", "errors"):
    full = f"configmgr.core.{sub}"
    try:
        mod = importlib.import_module(full)
        sys.modules[f"core.{sub}"] = mod
    except ModuleNotFoundError:
        pass