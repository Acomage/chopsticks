from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="zathura",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["zathura", "zathura-pdf-mupdf"])],
    uninstall=[],
    update=[],
)
