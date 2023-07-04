from inmanta.plugins import plugin


@plugin("cmd_submod")
def cmd_submod():
    print("Hello from complex_module_dependencies_submod")
