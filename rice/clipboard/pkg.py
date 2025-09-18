from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="clipboard",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["wl-clipboard", "cliphist"])],
    uninstall=[],
    update=[],
)
