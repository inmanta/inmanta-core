import os

from inmanta.module import ModuleV1
from inmanta.moduletool import ModuleConverter


def test_module_conversion(tmpdir):
    path = os.path.normpath(os.path.join(__file__, os.pardir, os.pardir, "data", "modules", "elaboratev1module"))
    module_in = ModuleV1(None, path)

    print(tmpdir)
    ModuleConverter(module_in).convert(tmpdir)
    print("x")
