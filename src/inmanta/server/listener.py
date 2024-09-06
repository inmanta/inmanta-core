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

from inmanta.data import model


class AutoStartedAgentManagerListener:
    """
    Base class for environment listeners
    Exceptions from the listeners are dropped, the listeners are responsible for handling them
    """

    async def environment_settings_changed(self, env: model.Environment) -> None:
        """
        Will be called when a new environment is created

        :param env: The new environment
        """

    async def environment_agent_map_changed(self, env: model.Environment) -> None:
        """
        Will be called when the environment is cleared

        :param env: The environment that is cleared
        """

    async def environment_halted(self, env: model.Environment) -> None:
        """
        Will be called when the environment is deleted

        :param env: The environment that is deleted
        """

    async def environment_action_updated(self, updated_env: model.Environment, original_env: model.Environment) -> None:
        """
        Will be called when an environment is updated
        :param updated_env: The updated environment
        :param original_env: The original environment
        """
