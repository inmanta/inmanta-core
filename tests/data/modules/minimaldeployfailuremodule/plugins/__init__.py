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


@resources.resource("minimaldeployfailuremodule::FailBasedOnFileContent", agent="agent", id_attribute="name")
class FailBasedOnFileContent(resources.PurgeableResource):
    """
    A resource that will succeed or fail its deploy based on the content of the file
    at `control_failure_file`.  This file is expected to be a json file with the
    `fail_deploy` key with a boolean value that controls the behaviour during a deploy.
    """

    name: str
    agent: str
    control_failure_file: str

    fields = ("name", "agent", "control_failure_file")


@provider("minimaldeployfailuremodule::FailBasedOnFileContent", name="wait_for_file")
class FailBasedOnFileContentHandler(CRUDHandler):

    def read_file(self, ctx: HandlerContext, control_file) -> dict[str, object]:
        if not os.path.exists(control_file):
            ctx.debug("Control file %(file)s not found", file=control_file)
            return {}

        with open(control_file) as fh:
            return json.load(fh)

    def execute(self, ctx: HandlerContext, resource: FailBasedOnFileContent, dry_run: bool = False) -> None:
        deploy_options = self.read_file(ctx, resource.control_failure_file)
        if not deploy_options or deploy_options.get("fail_deploy"):
            ctx.exception(
                "An error occurred during deployment of %(resource_id)s (exception: %(exception)s)",
                resource_id=resource.id,
                exception=f"Exception('')",
            )
            ctx.set_resource_state(const.HandlerResourceState.unavailable)
            return
        ctx.set_status(const.ResourceState.deployed)
