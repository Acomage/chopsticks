from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="grimblast",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["grimblast"])],
    uninstall=[],
    update=[],
)
