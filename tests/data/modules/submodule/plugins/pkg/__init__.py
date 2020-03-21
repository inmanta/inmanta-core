from inmanta.plugins import plugin
from inmanta_plugins.submodule.pkg.submod2 import test_submod2

print("#loading inmanta_plugins.submodule.pkg#")


@plugin
def test_pkg() -> "string":
    return f"test_pkg -- {test_submod2()}"
