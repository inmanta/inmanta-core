import configparser
import os
import sys

from inmanta.module import DummyProject, ModuleV1, ModuleV2Metadata, Project
from inmanta.moduletool import ModuleConverter


def test_module_conversion(tmpdir):
    module_name = "elaboratev1module"
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", module_name))
    dummyproject = DummyProject()
    module_in = ModuleV1(dummyproject, path)

    assert module_in.get_all_requires() == ["mod1==1.0", "mod2", "std"]

    ModuleConverter(module_in).convert(tmpdir)

    assert os.path.exists(os.path.join(tmpdir, "setup.cfg"))
    assert os.path.exists(os.path.join(tmpdir, "model", "_init.cf"))
    assert os.path.exists(os.path.join(tmpdir, "files", "test.txt"))
    assert os.path.exists(os.path.join(tmpdir, "templates", "template.txt.j2"))
    assert os.path.exists(os.path.join(tmpdir, "model", "other.cf"))
    assert os.path.exists(os.path.join(tmpdir, "inmanta_plugins", module_name, "__init__.py"))
    assert os.path.exists(os.path.join(tmpdir, "inmanta_plugins", module_name, "other_module.py"))
    assert os.path.exists(os.path.join(tmpdir, "inmanta_plugins", module_name, "subpkg", "__init__.py"))

    with open(os.path.join(tmpdir, "setup.cfg"), "r") as fh:
        content = fh.read()
        meta = ModuleV2Metadata.parse(content)
        assert meta.name == "inmanta-module-" + module_name
        assert meta.version == "1.2"

        raw_content = configparser.ConfigParser()
        raw_content.read_string(content)
        raw_content.write(sys.stdout)
        assert (
            raw_content["options"]["install_requires"].strip()
            == """inmanta-module-mod1==1.0
inmanta-module-mod2
inmanta-module-std
jinja2"""
        )
