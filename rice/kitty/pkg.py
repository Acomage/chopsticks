from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="kitty",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["kitty"])],
    uninstall=[],
    update=[],
)
