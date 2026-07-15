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

from asyncpg import Connection


async def update(connection: Connection) -> None:
    """
    These new columns are nullable on purpose for now:
      - for all model versions deployed after the orchestrator was upgraded to iso 10 (The iso version
      containing the agent code install improvement feature), the code exporter will set these columns and the
      code loader will read these **NON-NULL** values and use the "New-style" code install.
      - But, we still need to be able to run dry-runs for old model versions deployed before the orchestrator
      was upgraded to iso 10. Setting the values of these columns would require a full compile for each
      of these versions, which is out of the question. Instead, if the code loader encounters null values
      for these columns, it will use the "Old-style" code install.

    In the next major (iso 11) these columns can be made 'NOT NULL' and the code loader can use
    the "New-style" only.

    """
    schema = """
    -- Add the 'editable_install' column

    ALTER TABLE public.inmanta_module
    ADD COLUMN editable_install boolean;

    -- Add the 'load_module_on_agent' column
    ALTER TABLE public.agent_modules
    ADD COLUMN load_module_on_agent boolean;
    """
    await connection.execute(schema)
