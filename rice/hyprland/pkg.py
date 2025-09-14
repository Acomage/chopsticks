from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="hyprland",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["hyprland"])],
    uninstall=[],
    update=[],
)
