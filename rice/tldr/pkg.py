from core.package import Package
from core.action import RunCommand, PacmanInstall, PacmanUninstall

pkg = Package(
    name="tldr",
    version="1.0.0",
    dependencies=[],
    install=[PacmanInstall(["tealdeer"]), RunCommand("tldr --update")],
    uninstall=[PacmanUninstall(["tealdeer"])],
    update=[RunCommand("tldr --update")],
)
