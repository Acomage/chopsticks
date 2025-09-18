from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="hyprland",
    version="1.0.0",
    dependencies=[],
    install=[
        PacmanInstall(
            [
                "hyprland",
                "xdg-desktop-portal_hyprland",
                "hyprpolkitagent",
                "hyprpicker",
                "hyprpaper",
                "hypridle",
                "hyprlock",
                "hyprsunset",
                "qt5-wayland",
                "qt6-wayland",
            ]
        )
    ],
    uninstall=[],
    update=[],
)
