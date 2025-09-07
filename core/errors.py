from __future__ import annotations


class ConfigMgrError(Exception):
    pass


class PackageNotFoundError(ConfigMgrError):
    def __init__(self, name: str):
        super().__init__(f"Package not found: {name}")
        self.name = name


class InvalidPackageError(ConfigMgrError):
    pass


class ActionError(ConfigMgrError):
    pass


class ExecutionError(ConfigMgrError):
    pass


class DependencyError(ConfigMgrError):
    pass