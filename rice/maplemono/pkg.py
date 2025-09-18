from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="maplemono",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["ttf-maplemononormal-nf-cn"])],
    uninstall=[],
    update=[],
)
