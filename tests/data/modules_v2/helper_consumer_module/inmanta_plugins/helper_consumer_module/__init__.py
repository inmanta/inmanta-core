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
from inmanta_plugins.helper_module import helper_marker


@resources.resource("helper_consumer_module::ConsumerResource", agent="agent", id_attribute="name")
class ConsumerResource(resources.PurgeableResource):
    name: str
    agent: str
    expected_marker: str

    fields = ("name", "agent", "expected_marker")


@provider("helper_consumer_module::ConsumerResource", name="consumer_handler")
class ConsumerResourceHandler(CRUDHandler):
    def execute(self, ctx: HandlerContext, resource: ConsumerResource, dry_run: bool = False) -> None:
        marker = helper_marker()
        if marker != resource.expected_marker:
            raise Exception(f"Imported the wrong copy of helper_module: expected {resource.expected_marker}, got {marker}")
        ctx.set_status(const.ResourceState.deployed)
