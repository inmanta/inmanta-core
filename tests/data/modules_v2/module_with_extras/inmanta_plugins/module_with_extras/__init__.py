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

A module that defines one reference per extra: the used submodule only defines module_with_extras::UsedRef when the "used"
extra is installed, the unused submodule only defines module_with_extras::UnusedRef when the "unused" extra is installed.
"""

import importlib.metadata

from inmanta import const, resources
from inmanta.agent.handler import CRUDHandler, HandlerContext, provider
from inmanta.references import reference

USED_VALUE = "used"

# The python packages each extra installs, besides this module itself.
USED_EXTRA_PACKAGES = ("module-with-extras-used-dep", "inmanta-module-module-with-extras-used-mod")
UNUSED_EXTRA_PACKAGES = ("module-with-extras-unused-dep", "inmanta-module-module-with-extras-unused-mod")


def is_installed(package_name: str) -> bool:
    try:
        importlib.metadata.distribution(package_name)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


@resources.resource("module_with_extras::Probe", agent="agent", id_attribute="name")
class Probe(resources.PurgeableResource):
    name: str
    agent: str
    value: str

    fields = ("name", "agent", "value")


@provider("module_with_extras::Probe", name="probe_handler")
class ProbeHandler(CRUDHandler):
    def execute(self, ctx: HandlerContext, resource: Probe, dry_run: bool = False) -> None:
        problems: list[str] = []
        if resource.value != USED_VALUE:
            problems.append(f"value resolved to {resource.value!r} instead of {USED_VALUE!r}")
        reference_types = {name for name, _ in reference.get_references()}
        if "module_with_extras::UsedRef" not in reference_types:
            problems.append("module_with_extras::UsedRef is not registered")
        if "module_with_extras::UnusedRef" in reference_types:
            problems.append("module_with_extras::UnusedRef is registered")
        problems.extend(f"{package} is not installed" for package in USED_EXTRA_PACKAGES if not is_installed(package))
        problems.extend(f"{package} is installed" for package in UNUSED_EXTRA_PACKAGES if is_installed(package))
        if problems:
            raise Exception(
                f"Agent {resource.agent} does not match the 'used' extra of module_with_extras: {'; '.join(problems)}"
            )
        ctx.set_status(const.ResourceState.deployed)
