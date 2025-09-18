from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="kdesystemsettings",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["systemsettings", "plasma-nm"])],
    uninstall=[],
    update=[],
)
