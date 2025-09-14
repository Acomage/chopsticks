from core.package import Package
from core.action import RunCommand

pkg = Package(
    name="example",
    version="1.28.0",
    dependencies=[],
    install=[RunCommand("echo install example"), RunCommand("echo Hello World!")],
    uninstall=[RunCommand("echo uninstall example")],
    update=[RunCommand("echo update example")],
)
