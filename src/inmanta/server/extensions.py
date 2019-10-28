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
import logging
import os
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional

import yaml

from inmanta.config import feature_file_config
from inmanta.util import get_compiler_version

if TYPE_CHECKING:
    from inmanta.server.protocol import ServerSlice


LOGGER = logging.getLogger(__name__)


class InvalidSliceNameException(Exception):
    """ This exception is raised when the name of the slice is not valid. For example when the extension and the slice name
        do not match.
    """


class InvalidFeature(Exception):
    """ This exception is raised when a feature is defined in another slice than it reports or the feature is not defined
        at all.
    """


class Feature:
    """ A feature offered by a slice """

    def __init__(self, slice: str, name: str, description: str = "") -> None:
        self._name: str = name
        self._slice: str = slice
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def slice(self) -> str:
        return self._slice

    def __str__(self) -> str:
        return f"{self._slice}:{self._name}"


class BoolFeature(Feature):
    """ A feature that is on or off.
    """


class FeatureManager:
    """ This class allows to verify whether a feature should be enabled or not. This is determined based on a configuration
        file that is set with config.feature-file in the config. This feature file is a yaml with the following structure:

        slices:
            slice_name:
                feature_name: bool

        When the feature specifies an int this implies a limit. 0 means that the feature is disabled. -1 means no limit.
    """

    def __init__(self) -> None:
        self._features: Dict[str, Dict[str, Feature]] = defaultdict(lambda: {})
        self._feature_config: Optional[Dict[str, Dict[str, bool]]] = self._load_feature_config()

    def set_feature_config(self, feature: Feature, value: bool) -> None:
        if feature.slice in self._features and feature.name in self._features[feature.slice]:
            self._feature_config[feature.slice][feature.name] = value

    def _load_feature_config(self) -> Optional[Dict[str, Dict[str, bool]]]:
        feature_file = feature_file_config.get()
        if feature_file is None:
            return defaultdict(lambda: {})

        if not os.path.exists(feature_file):
            LOGGER.warning("Feature file %s configured but file does not exist.", feature_file)
            return defaultdict(lambda: {})

        with open(feature_file) as fd:
            result = yaml.safe_load(fd)
        if "slices" in result:
            return result["slices"]
        return defaultdict(lambda: {})

    def get_product_metadata(self) -> Dict[str, str]:
        return {
            "product": "Inmanta Service Orchestator",
            "edition": "Open Source Edition",
            "license": "Apache Software License 2",
            "version": get_compiler_version(),
        }

    def add_slice(self, slice: "ServerSlice") -> None:
        for feature in slice.define_features():
            if feature.slice != slice.name:
                raise InvalidFeature(
                    f"Feature {feature.name} defines slice {feature.slice} but is defined by slice {slice.name}"
                )
            self._features[feature.slice][feature.name] = feature
        slice.feature_manager = self

    def _get_config(self, feature: Feature) -> Optional[bool]:
        if feature.slice not in self._features or feature.name not in self._features[feature.slice]:
            raise InvalidFeature(f"Feature {feature.name} in slice {feature.slice} is not defined.")

        if (
            self._feature_config is not None
            and feature.slice in self._feature_config
            and feature.name in self._feature_config[feature.slice]
        ):
            config = self._feature_config[feature.slice][feature.name]

            if isinstance(config, bool):
                return config

        return None

    def enabled(self, feature: Feature) -> bool:
        config = self._get_config(feature)
        if config is None:
            return True

        return config


class ApplicationContext:
    def __init__(self) -> None:
        self._slices: List[ServerSlice] = []
        self._feature_manager: Optional[FeatureManager] = None

    def register_slice(self, slice: "ServerSlice") -> None:
        assert slice is not None
        self._slices.append(slice)

    def get_slices(self) -> "List[ServerSlice]":
        return self._slices

    def set_feature_manager(self, feature_manager: FeatureManager):
        assert self._feature_manager is None
        self._feature_manager = feature_manager

    def get_feature_manager(self) -> FeatureManager:
        if self._feature_manager is None:
            self._feature_manager = FeatureManager()
        return self._feature_manager
