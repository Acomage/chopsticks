from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="fish",
    version="1.0.0",
    dependencies=[],
    install=[
        PacmanInstall(
            [
                "fish",
                "trash-cli",
                "zoxide",
            ]
        )
    ],
    uninstall=[],
    update=[],
)
