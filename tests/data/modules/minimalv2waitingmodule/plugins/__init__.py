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

from inmanta import resources
from inmanta.agent.handler import provider, CRUDHandler, HandlerContext


@resources.resource("minimalv2waitingmodule::Sleep", agent="agent", id_attribute="name")
class SleepResource(resources.ManagedResource):
    """
    This class represents a service on a system.
    """

    name: str
    agent: str
    time_to_sleep: int

    fields = ("name", "agent", "time_to_sleep")


@provider("minimalv2waitingmodule::Sleep", name="mysleephandler")
class SleepHandler(CRUDHandler):
    def read_resource(self, ctx: HandlerContext, resource: SleepResource) -> None:
        time.sleep(resource.time_to_sleep)

    def create_resource(self, ctx: HandlerContext, resource: SleepResource) -> None:
        time.sleep(resource.time_to_sleep)

    def delete_resource(self, ctx: HandlerContext, resource: SleepResource) -> None:
        time.sleep(resource.time_to_sleep)

    def update_resource(self, ctx: HandlerContext, changes: dict, resource: SleepResource) -> None:
        time.sleep(resource.time_to_sleep)
