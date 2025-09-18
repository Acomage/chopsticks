from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="waybar",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["waybar"])],
    uninstall=[],
    update=[],
)
