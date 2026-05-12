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

import logging

from inmanta import protocol
from inmanta.protocol import exceptions
from inmanta.server import SLICE_FEATURE, SLICE_TRANSPORT, extensions
from inmanta.server import protocol as server_protocol

LOGGER = logging.getLogger(__name__)


class FeatureService(server_protocol.ServerSlice):
    """Slice to request information about features that are enabled/disabled"""

    def __init__(self) -> None:
        super().__init__(SLICE_FEATURE)

    def get_dependencies(self) -> list[str]:
        return []

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    @protocol.handle(protocol.methods_v2.is_bool_feature_enabled)
    async def is_bool_feature_enabled(self, slice_name: str, feature_name: str) -> bool:
        try:
            feature: extensions.BoolFeature = self.feature_manager.get_feature(slice_name=slice_name, feature_name=feature_name)
        except KeyError:
            raise exceptions.NotFound(message=f"Feature with name {feature_name} not found for slice {slice_name}.")

        if not isinstance(feature, extensions.BoolFeature):
            raise exceptions.BadRequest(message=f"Feature {feature} is not a BoolFeature")

        return self.feature_manager.enabled(feature)
