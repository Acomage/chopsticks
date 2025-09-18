from core.package import Package
from core.action import PacmanInstall

pkg = Package(
    name="neovim",
    version="1.0.0",
    dependencies=["js", "maplemono"],
    install=[
        PacmanInstall(
            [
                "neovim-git",
                "lazygit",
                "tree-sitter-cli",
                "luarocks",
                "lua51",
            ]
        )
    ],
    uninstall=[],
    update=[],
)
