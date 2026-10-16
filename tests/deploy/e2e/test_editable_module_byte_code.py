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
import py_compile
import uuid

import pytest

from deploy.e2e.test_autostarted import wait_for_resources_in_state
from inmanta import const
from inmanta.env import LocalPackagePath
from utils import module_from_template

PYTHON_CODE = """
from inmanta import const, resources
from inmanta.agent.handler import CRUDHandler, HandlerContext, provider
from inmanta.plugins import plugin

VARIANT = "{variant}"


@plugin
def variant() -> str:
    return VARIANT


@resources.resource("pycmod::Test", agent="agent", id_attribute="name")
class Test(resources.PurgeableResource):
    fields = ("name", "agent", "path")


@provider("pycmod::Test", name="test")
class TestHandler(CRUDHandler):
    def execute(self, ctx: HandlerContext, resource: Test, dry_run: bool = False) -> None:
        with open(resource.path, "w") as fh:
            fh.write(VARIANT)
        ctx.set_status(const.ResourceState.deployed)
"""

MODEL_CODE = """
entity Test extends std::PurgeableResource:
    string name
    string agent
    string path
end

implement Test using std::none
"""


@pytest.mark.slowtest
@pytest.mark.parametrize("auto_start_agent", (True,))  # this overrides a fixture to allow the agent to fork!
async def test_pyc_next_to_py_in_editable_module(
    snippetcompiler,
    server,
    client,
    environment,
    auto_start_agent: bool,
    modules_v2_dir: str,
    local_module_package_index: str,
    tmp_path,
) -> None:
    """
    An editable V2 module ships inmanta_plugins/pycmod/__init__.py next to an __init__.pyc compiled from different code.
    The compiler and the agent both run the .py file, which python imports over the .pyc.
    """
    module_dir = str(tmp_path / "pycmod")
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        module_dir,
        new_name="pycmod",
        new_content_init_cf=MODEL_CODE,
        new_content_init_py=PYTHON_CODE.format(variant="py"),
    )
    plugin_dir = os.path.join(module_dir, const.PLUGINS_PACKAGE, "pycmod")
    pyc_source = str(tmp_path / "pyc_source.py")
    with open(pyc_source, "w") as fh:
        fh.write(PYTHON_CODE.format(variant="pyc"))
    py_compile.compile(file=pyc_source, cfile=os.path.join(plugin_dir, "__init__.pyc"), doraise=True)

    deployed_file = str(tmp_path / "deployed")
    snippetcompiler.setup_for_snippet(
        f"""
import pycmod
pycmod::Test(name=pycmod::variant(), agent="agent1", path="{deployed_file}")
        """,
        autostd=True,
        index_url=local_module_package_index,
        install_project=True,
        install_v2_modules=[LocalPackagePath(path=module_dir, editable=True)],
    )
    version, resources_by_id = await snippetcompiler.do_export_and_deploy()
    (compiler_variant,) = [resource_id.attribute_value for resource_id in resources_by_id]
    result = await client.release_version(environment, version, push=False)
    assert result.code == 200
    await wait_for_resources_in_state(client, uuid.UUID(environment), nr_of_resources=1, state=const.ResourceState.deployed)

    with open(deployed_file) as fh:
        agent_variant = fh.read()
    assert (compiler_variant, agent_variant) == (
        "py",
        "py",
    ), f"the compiler ran the {compiler_variant} file, the agent the {agent_variant} file"
