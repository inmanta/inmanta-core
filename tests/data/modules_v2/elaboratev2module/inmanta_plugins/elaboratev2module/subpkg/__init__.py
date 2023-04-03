from inmanta.plugins import plugin


@plugin("subpkg_plugin")
def subpkg_plugin(message: "string"):
    print(message)
