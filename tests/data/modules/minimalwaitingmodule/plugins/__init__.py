"""
Copyright 2024 Inmanta

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

import time
import os.path

from inmanta import resources
from inmanta.agent.handler import provider, CRUDHandler, HandlerContext, ResourcePurged


@resources.resource("minimalwaitingmodule::WaitForFileRemoval", agent="agent", id_attribute="name")
class WaitForFileRemoval(resources.PurgeableResource):
    """
    A resource that remains in the deploying state as long as the file at `path` exists.
    """

    name: str
    agent: str
    path: str

    fields = ("name", "agent", "path")


@provider("minimalwaitingmodule::WaitForFileRemoval", name="wait_for_file_removal")
class WaitForFileRemovalHandler(CRUDHandler):
    def read_resource(self, ctx: HandlerContext, resource: WaitForFileRemoval) -> None:
        if os.path.exists(resource.path):
            raise ResourcePurged()

    def create_resource(self, ctx: HandlerContext, resource: WaitForFileRemoval) -> None:
        file_exists = os.path.exists(resource.path)
        while file_exists:
            time.sleep(0.05)
            file_exists = os.path.exists(resource.path)
        ctx.set_created()
