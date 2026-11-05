"""
Copyright 2026 Inmanta

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Contact: code@inmanta.com
"""

import os
import pathlib
import shutil
import zipfile
from typing import Optional

from pytest import MonkeyPatch

from inmanta.moduletool import ModuleTool
from utils import build_module_package_index, module_from_template


def test_module_package_index_cache(tmp_path: pathlib.Path, modules_v2_dir: str, monkeypatch: MonkeyPatch) -> None:
    """
    build_module_package_index() rebuilds exactly the modules that were added or whose files changed since their wheel
    was built, and drops the wheels of removed modules.
    """
    modules_dir = tmp_path / "modules"
    cache_dir = tmp_path / "modules.cache"
    for name in ["mod_a", "mod_b"]:
        module_from_template(os.path.join(modules_v2_dir, "minimalv2module"), str(modules_dir / name), new_name=name)
    model_dir_a = modules_dir / "mod_a" / "model"

    built_modules: list[str] = []
    original_build = ModuleTool.build

    def recording_build(
        self: ModuleTool,
        path: Optional[str] = None,
        output_dir: Optional[str] = None,
        dev_build: bool = False,
        byte_code: bool = False,
        wheel: bool = False,
        sdist: bool = False,
    ) -> list[str]:
        assert path is not None
        built_modules.append(os.path.basename(path))
        return original_build(
            self, path=path, output_dir=output_dir, dev_build=dev_build, byte_code=byte_code, wheel=wheel, sdist=sdist
        )

    monkeypatch.setattr(ModuleTool, "build", recording_build)

    def build_index() -> list[str]:
        """
        Build the index and return the modules that were built.
        """
        built_modules.clear()
        index_dir = build_module_package_index(str(modules_dir), str(cache_dir))
        assert index_dir == str(cache_dir / "build" / "simple")
        return sorted(built_modules)

    def files_in_wheel(name: str) -> list[str]:
        """
        Return the model files in the wheel of the given module.
        """
        (wheel,) = (cache_dir / "build").glob(f"inmanta_module_{name}-*.whl")
        with zipfile.ZipFile(wheel) as zf:
            return sorted(os.path.basename(f) for f in zf.namelist() if f.startswith(f"inmanta_plugins/{name}/model/"))

    def modules_in_index() -> list[str]:
        return sorted(d.name for d in (cache_dir / "build" / "simple").iterdir() if d.name.startswith("inmanta-module-"))

    # Cold cache
    assert build_index() == ["mod_a", "mod_b"]
    assert modules_in_index() == ["inmanta-module-mod-a", "inmanta-module-mod-b"]
    assert files_in_wheel("mod_a") == ["_init.cf"]

    # Warm cache
    assert build_index() == []

    # Python bytecode is ignored
    pycache_dir = modules_dir / "mod_a" / "inmanta_plugins" / "mod_a" / "__pycache__"
    pycache_dir.mkdir(exist_ok=True)
    (pycache_dir / "__init__.cpython-312.pyc").write_bytes(b"bytecode")
    assert build_index() == []

    # A file with a newer modification time but the same content
    init_cf = model_dir_a / "_init.cf"
    init_cf.write_text(init_cf.read_text())
    assert build_index() == []

    # An added file
    (model_dir_a / "extra.cf").write_text("entity Extra:\nend\n")
    assert build_index() == ["mod_a"]
    assert files_in_wheel("mod_a") == ["_init.cf", "extra.cf"]

    # A renamed file, with the same content
    (model_dir_a / "extra.cf").rename(model_dir_a / "renamed.cf")
    assert build_index() == ["mod_a"]
    assert files_in_wheel("mod_a") == ["_init.cf", "renamed.cf"]

    # A deleted file
    (model_dir_a / "renamed.cf").unlink()
    assert build_index() == ["mod_a"]
    assert files_in_wheel("mod_a") == ["_init.cf"]

    # A removed module
    shutil.rmtree(modules_dir / "mod_b")
    assert build_index() == []
    assert modules_in_index() == ["inmanta-module-mod-a"]
    assert list((cache_dir / "build").glob("inmanta_module_mod_b-*.whl")) == []

    # A truncated wheels.json rebuilds the cache from scratch
    (cache_dir / "wheels.json").write_text('{"mod_a": {"wheel": ')
    assert build_index() == ["mod_a"]
    assert build_index() == []
