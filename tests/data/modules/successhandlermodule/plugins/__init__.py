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
from inmanta.agent.handler import provider, CRUDHandler, HandlerContext, LoggerABC

from inmanta.plugins import plugin
from inmanta.references import reference, Reference, mutator, Mutator


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


@resources.resource("successhandlermodule::SuccessResourceWithReference", agent="agent", id_attribute="name")
class SuccessResourceWithReference(resources.PurgeableResource):
    """
    This resource's handler will always succeed
    """

    name: str
    agent: str
    my_attr: str

    fields = ("name", "agent", "my_attr")


@provider("successhandlermodule::SuccessResourceWithReference", name="wait_for_file")
class SuccessResourceWithReferenceHandler(CRUDHandler):

    def execute(self, ctx: HandlerContext, resource: SuccessResourceWithReference, dry_run: bool = False) -> None:

        ctx.set_status(const.ResourceState.deployed)


@reference("successhandlermodule::FooReference")
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


@mutator(name="foo::Mutator")
class FooMutator(Mutator):

    def run(self, logger: "handler.LoggerABC") -> None:
        return
