from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="kdeconnect",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["kdeconnect"])],
    uninstall=[],
    update=[],
)
