import os


def test_multi_excn(snippetcompiler, modules_dir):
    snippetcompiler.setup_for_error(
        """
entity Repo:
    string name
end

entity Host:
    string name
end

entity OS:
    string name
end

Repo.host [1] -- Host
Host.os [1] -- OS

host = Host(name="x")

Repo(host=host,name="epel")

implement Host using std::none
implement Repo using std::none when host.os.name=="os"
""",
        """Reported 2 errors
error 0:
  The object __config__::Host (instantiated at {dir}/main.cf:17) is not complete: attribute os ({dir}/main.cf:15:6) is not set
error 1:
  Unable to select implementation for entity Repo (reported in __config__::Repo (instantiated at {dir}/main.cf:19) ({dir}/main.cf:19))""",  # noqa: E501
        libs_dir=modules_dir,
    )


def test_module_error(snippetcompiler, modules_dir):
    modpath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "modules", "badmodule")
    snippetcompiler.setup_for_error(
        "import badmodule",
        """could not find module badmodule (reported in import badmodule ({dir}/main.cf:1))
caused by:
  Could not load module badmodule
  caused by:
    inmanta.module.InvalidModuleException: Module %s is not a valid inmanta configuration module. Make sure that a model/_init.cf file exists and a module.yml definition file.
"""  # noqa: E501
        % modpath,
        libs_dir=modules_dir,
    )
