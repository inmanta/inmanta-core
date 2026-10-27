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

from inmanta import const
from inmanta.agent.handler import CRUDHandler, HandlerContext, provider

# A plain module: `.` is the relativeimportmodulev2 package
from . import helpers, sub


@provider("relativeimportmodulev2::RelativeImportResource", name="relative_import")
class RelativeImportHandler(CRUDHandler):
    def execute(self, ctx: HandlerContext, resource: object, dry_run: bool = False) -> None:
        assert sub.GREETING == helpers.GREETING
        ctx.set_status(const.ResourceState.deployed)
