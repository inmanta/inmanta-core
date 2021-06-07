"""
    Copyright 2020 Inmanta

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

DISABLED = False


async def update(connection: Connection) -> None:
    await connection.execute(
        """
ALTER TABLE public.compile DROP CONSTRAINT compile_substitute_compile_id_fkey;
ALTER TABLE public.compile
    ADD CONSTRAINT compile_substitute_compile_id_fkey
    FOREIGN KEY (substitute_compile_id) REFERENCES public.compile (id)
    ON DELETE CASCADE;

        """
    )
