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
    schema = """
    -- Add the 'editable_install' column

    ALTER TABLE public.inmanta_module
    ADD COLUMN editable_install boolean DEFAULT true;

    -- Add the 'load_module_on_agent' column
    ALTER TABLE public.agent_modules
    ADD COLUMN load_module_on_agent boolean DEFAULT true;
    """
    await connection.execute(schema)
