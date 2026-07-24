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

# main_module_x reuses plugin code from dependency_module_y. This module-level import is the
# crux of the scenario: any agent that loads main_module_x's handler code must be able to
# import dependency_module_y, even if it never deploys a dependency_module_y resource.
from inmanta_plugins.dependency_module_y import DEPENDENCY_MARKER, dependency_marker


@resources.resource("main_module_x::MainResource", agent="agent", id_attribute="name")
class MainResource(resources.PurgeableResource):
    name: str
    agent: str

    fields = ("name", "agent")


@provider("main_module_x::MainResource", name="main_handler")
class MainResourceHandler(CRUDHandler):
    def execute(self, ctx: HandlerContext, resource: MainResource, dry_run: bool = False) -> None:
        # Actually call into dependency_module_y's code while deploying, so the deployment only
        # succeeds if that module's source is genuinely available on this agent.
        if dependency_marker() != DEPENDENCY_MARKER:
            raise Exception("Unexpected return value from dependency_module_y::dependency_marker")
        ctx.set_status(const.ResourceState.deployed)
