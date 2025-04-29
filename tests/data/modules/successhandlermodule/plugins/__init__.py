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

import json
import os.path

from inmanta import resources, const
from inmanta.agent.handler import provider, CRUDHandler, HandlerContext


@resources.resource("successhandlermodule::SuccessResource", agent="agent", id_attribute="name")
class SuccessResource(resources.PurgeableResource):
    """
    This resource's handler will always succeed
    """

    name: str
    agent: str

    fields = ("name", "agent")


@provider("successhandlermodule::SuccessResource", name="wait_for_file")
class SuccessResourceHandler(CRUDHandler):

    def execute(self, ctx: HandlerContext, resource: SuccessResource, dry_run: bool = False) -> None:

        ctx.set_status(const.ResourceState.deployed)
