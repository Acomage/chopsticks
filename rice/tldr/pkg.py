from core.package import Package
from core.action import RunCommand, PacmanInstall

pkg = Package(
    name="tldr",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["tealdeer"]), RunCommand("tldr --update")],
    uninstall=[],
    update=[RunCommand("tldr --update")],
)
