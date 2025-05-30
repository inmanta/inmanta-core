"""
Copyright 2025 Inmanta

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

# This trick is used in tests/deploy/e2e/test_autostarted.py in the test_code_install_success_code_load_error test.
# It ensures
#   - success during code compilation and upload
#   - failure during code loading by the executor
try:
    a = b
except NameError:
    if "executors/code" in __file__:
        raise
    else:
        pass


import json
import os.path

from inmanta import resources, const
from inmanta.agent.handler import provider, CRUDHandler, HandlerContext, LoggerABC
from inmanta.plugins import plugin
from inmanta.references import reference, Reference


@resources.resource("minimalinstallfailuremodule::CodeInstallErrorResource", agent="agent", id_attribute="name")
class CodeInstallErrorResource(resources.PurgeableResource):
    """
    This resource's handler will raise an exception during code installation installed
    """

    name: str
    agent: str

    fields = ("name", "agent")


@provider("minimalinstallfailuremodule::CodeInstallErrorResource", name="wait_for_file")
class CodeInstallErrorResourceHandler(CRUDHandler):

    def execute(self, ctx: HandlerContext, resource: CodeInstallErrorResource, dry_run: bool = False) -> None:

        ctx.set_status(const.ResourceState.deployed)


@reference("minimalinstallfailuremodule::FooReference")
class FooReference(Reference[str]):
    """A reference to the 'foo' string"""

    def __init__(self, base: str | Reference[str]) -> None:
        """
        :param name: The name of the environment variable.
        """
        super().__init__()
        self.base = base

    def resolve(self, logger: LoggerABC) -> str:
        """Resolve the reference"""
        return self.resolve_other(self.base, logger) + "foo"


@plugin
def create_my_ref(base: str | Reference[str]) -> Reference[str]:
    """Create an environment reference

    :return: A reference to what can be resolved to a string
    """
    return FooReference(base)
