from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="fuzzel",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["fuzzel"])],
    uninstall=[],
    update=[],
)
