from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="js",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["nodejs", "npm"])],
    uninstall=[],
    update=[],
)
