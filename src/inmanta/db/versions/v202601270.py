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
    Rename last_deploy_result to last_handler_run
    """
    schema = """
    ALTER TABLE public.resource_persistent_state RENAME COLUMN last_deploy_result TO last_handler_run;
    ALTER TABLE public.resource_persistent_state RENAME COLUMN last_deploy_compliant TO last_handler_run_compliant;
    ALTER TABLE public.resource_persistent_state RENAME COLUMN last_deploy TO last_handler_run_at;

    UPDATE public.resource_persistent_state
    SET last_handler_run='SUCCESSFUL'
    WHERE last_handler_run='DEPLOYED';
    """
    await connection.execute(schema)
