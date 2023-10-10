"""
    Copyright 2023 Inmanta

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
from asyncpg import Connection

from inmanta import data


def convert_setting_to_str(setting: str) -> str:
    # The ->> operator gets the JSON object field as text
    return f"""
    UPDATE environment
    SET settings=jsonb_set(settings, '{{{setting}}}'::TEXT[], to_jsonb(settings->>'{setting}'), FALSE)
    WHERE settings ? '{setting}'
    """


async def update(connection: Connection) -> None:
    """
    Update the type of the autostart_agent_repair_interval and autostart_agent_deploy_interval from int to str
    """
    await connection.execute(convert_setting_to_str(data.AUTOSTART_AGENT_REPAIR_INTERVAL))
    await connection.execute(convert_setting_to_str(data.AUTOSTART_AGENT_DEPLOY_INTERVAL))
