from core.package import Package
from core.action import RunCommand

pkg = Package(
    name="example1",
    version="1.11.0",
    dependencies=["example"],
    install=[RunCommand("echo install example1"), RunCommand("echo Hello World!")],
    uninstall=[RunCommand("echo uninstall example1")],
    update=[RunCommand("echo update example1")],
)
