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

Only defines its reference and plugin when the "used" extra of dummy_future is installed.
"""

from inmanta.agent.handler import LoggerABC
from inmanta.plugins import plugin
from inmanta.references import Reference, reference
from inmanta_plugins.dummy_future import USED_EXTRA_PACKAGES, USED_VALUE, is_installed

if all(is_installed(package) for package in USED_EXTRA_PACKAGES):

    @reference("dummy_future::UsedRef")
    class UsedRef(Reference[str]):
        def resolve(self, logger: LoggerABC) -> str:
            return USED_VALUE

    @plugin
    def create_used_ref() -> Reference[str]:
        return UsedRef()
