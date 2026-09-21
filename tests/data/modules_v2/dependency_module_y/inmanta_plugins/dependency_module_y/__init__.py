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

from inmanta import const, resources
from inmanta.agent.handler import CRUDHandler, HandlerContext, provider

DEPENDENCY_MARKER = "code-from-dependency-module-y"


def dependency_marker() -> str:
    """
    Helper function reused from the handler code of main_module_x. It allows main_module_x's
    handler to assert that this module's source code is actually available and importable on
    the agent that deploys main_module_x resources.
    """
    return DEPENDENCY_MARKER


@resources.resource("dependency_module_y::DepResource", agent="agent", id_attribute="name")
class DepResource(resources.PurgeableResource):
    name: str
    agent: str

    fields = ("name", "agent")


@provider("dependency_module_y::DepResource", name="dep_handler")
class DepResourceHandler(CRUDHandler):
    def execute(self, ctx: HandlerContext, resource: DepResource, dry_run: bool = False) -> None:
        ctx.set_status(const.ResourceState.deployed)
