from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="keyd",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["keyd"])],
    uninstall=[],
    update=[],
)
