from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="wlogout",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["wlogout"])],
    uninstall=[],
    update=[],
)
