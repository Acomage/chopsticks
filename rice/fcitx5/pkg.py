from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="fcitx5",
    version="1.0.0",
    dependencies=[],
    install=[
        PacmanInstall(
            [
                "fcitx5",
                "fcitx5-configtool",
                "fcitx5-gtk",
                "fcitx5-qt",
                "fcitx5-chinese-addons",
                "fcitx5-pinyin-zhwiki",
            ]
        )
    ],
    uninstall=[],
    update=[],
)
