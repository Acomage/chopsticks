from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="dolphin",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["dolphin", "gwenview", "ark"])],
    uninstall=[],
    update=[],
)
