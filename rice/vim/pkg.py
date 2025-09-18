from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="vim",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["vim"])],
    uninstall=[],
    update=[],
)
