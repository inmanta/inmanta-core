"""
Copyright 2025 Inmanta

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
    Add and populate last_deploy_compliant on rps table
    """
    schema = """
    ALTER TABLE public.resource_persistent_state
        ADD COLUMN last_deploy_compliant BOOLEAN;

    -- NEW will remain as NULL
    UPDATE public.resource_persistent_state
    SET last_deploy_compliant=
        CASE
            WHEN last_deploy_result='DEPLOYED' THEN TRUE
            WHEN last_deploy_result='FAILED' OR last_deploy_result='SKIPPED' THEN FALSE
        END;

    -- Add 'non_compliant' to resource_state state machines
    ALTER TYPE non_deploying_resource_state ADD VALUE 'non_compliant';

    ALTER TYPE resourcestate ADD VALUE 'non_compliant';
    """
    await connection.execute(schema)
