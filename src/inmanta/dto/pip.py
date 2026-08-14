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

import os
from collections.abc import Sequence
from typing import ClassVar, Optional

from pydantic import ConfigDict

from inmanta.stable_api import stable_api
from inmanta.types import BaseModel as BaseModel


def hyphenize(field: str) -> str:
    """Alias generator to convert python names (with `_`) to config file name (with `-`)"""
    return field.replace("_", "-")


@stable_api
# This is part of both the config file schema and the api schema
class PipConfig(BaseModel):
    """
    Base class to represent pip config internally

    :param index_url: one pip index url for this project.
    :param extra_index_url:  additional pip index urls for this project. This is generally only
        recommended if all configured indexes are under full control of the end user to protect against dependency
        confusion attacks. See the `pip install documentation <https://pip.pypa.io/en/stable/cli/pip_install/>`_ and
        `PEP 708 (draft) <https://peps.python.org/pep-0708/>`_ for more information.
    :param pre:  allow pre-releases when installing Python packages, i.e. pip --pre.
        Defaults to None.
        When None and pip.use-system-config=true we follow the system config.
        When None and pip.use-system-config=false, we don't allow pre-releases.
    :param use_system_config: defaults to false.
        When true, sets the pip index url, extra index urls and pre according to the respective settings outlined above
        but otherwise respect any pip environment variables and/or config in the pip config file,
        including any extra-index-urls.

        If no indexes are configured in pip.index-url/pip.extra-index-url
        with this option enabled means to fall back to pip's default behavior:
        use the pip index url from the environment, the config file, or PyPi, in that order.

        For development, it is recommended to set this option to false, both for portability
        (and related compatibility with tools like pytest-inmanta-lsm) and for security
        (dependency confusion attacks could affect users that aren't aware that inmanta installs Python packages).
    """

    # Config needs to be in the top-level object, because is also affect serialization/deserialization
    model_config: ClassVar[ConfigDict] = ConfigDict(
        # use alias generator have `-` in names
        alias_generator=hyphenize,
        # allow use of aliases
        populate_by_name=True,
        extra="ignore",
    )

    index_url: Optional[str] = None
    # Singular to be consistent with pip itself
    extra_index_url: Sequence[str] = []
    pre: Optional[bool] = None
    use_system_config: bool = False

    def has_source(self) -> bool:
        """Can this config get packages from anywhere?"""
        return bool(self.index_url) or self.use_system_config

    def get_index_args(self) -> list[str]:
        """
        Returns the index-related arguments that should be used to run a pip command
        with this pip config.
        """
        index_args: list[str] = []
        if self.index_url:
            index_args.append("--index-url")
            index_args.append(self.index_url)
        elif not self.use_system_config:
            # If the config doesn't set index url
            # and we are not using system config,
            # then we need to disable the index.
            # This can only happen if paths is also set.
            index_args.append("--no-index")
        for extra_index_url in self.extra_index_url:
            index_args.append("--extra-index-url")
            index_args.append(extra_index_url)
        return index_args

    def get_environment_variables(self) -> dict[str, str]:
        """
        Returns the environment variables that should be used to run a pip command
        with this pip config.
        """
        sub_env = os.environ.copy()
        if not self.use_system_config:
            # If we don't use system config, unset env vars
            for key in ("PIP_EXTRA_INDEX_URL", "PIP_INDEX_URL", "PIP_PRE", "PIP_NO_INDEX"):
                sub_env.pop(key, None)

            # setting this env_var to os.devnull disables the loading of all pip configuration file
            sub_env["PIP_CONFIG_FILE"] = os.devnull
        if self.pre is not None:
            # Make sure that IF pip pre is set, we enforce it
            # The `--pre` option can only enable it
            # The env var can both enable and disable
            sub_env["PIP_PRE"] = str(self.pre)
        return sub_env


LEGACY_PIP_DEFAULT = PipConfig(use_system_config=True)
