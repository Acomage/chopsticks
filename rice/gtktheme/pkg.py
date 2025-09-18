from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="gtktheme",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["adw-gtk-theme"])],
    uninstall=[],
    update=[],
)
