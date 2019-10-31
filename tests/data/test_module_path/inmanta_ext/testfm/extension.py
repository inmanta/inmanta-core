"""
    Copyright 2019 Inmanta

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
from typing import List

from inmanta.server import SLICE_AGENT_MANAGER, SLICE_SERVER
from inmanta.server.extensions import ApplicationContext, FeatureManager
from inmanta.server.protocol import ServerSlice


class CustomManager(FeatureManager):
    def enabled(self, feature):
        return False


def setup(application: ApplicationContext) -> None:
    application.set_feature_manager(CustomManager())
