from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="sddm",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["sddm"])],
    uninstall=[],
    update=[],
)
