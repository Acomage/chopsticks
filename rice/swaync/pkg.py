from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="swaync",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["swaync"])],
    uninstall=[],
    update=[],
)
