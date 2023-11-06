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


async def update(connection: Connection) -> None:
    """
    Add foreign key constraint from public.code (environment, version)
    to public.configurationmodel (environment, version).
    """
    schema = """
    ALTER TABLE public.code
    ADD CONSTRAINT code_configmodel_fk FOREIGN KEY (environment, version)
    REFERENCES public.configurationmodel(environment, version) ON DELETE CASCADE;
    """
    await connection.execute(schema)
    pass


# "errstream": "\n=============================== EXCEPTION TRACE ===============================\n
# Traceback (most recent call last):\n  File \"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/app.py\",
# line 671, in capture\n    yield self\n  File \"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/app.py\",
# line 627, in export\n    results = export.run(\n              ^^^^^^^^^^^\n  File \"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/export.py\",
# line 410, in run\n    self._version = self.commit_resources(\n                    ^^^^^^^^^^^^^^^^^^^^^^\n
# File \"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/export.py\", line 509, in commit_resources\n
# self.deploy_code(conn, tid, version)\n  File \"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/export.py\",
# line 482, in deploy_code\n
# upload_code(conn, tid, version, code_manager)\n  File \"/home/florent/Desktop/Inmanta/inmanta-core/src/inmanta/export.py\", line 98, in upload_code\n
# raise Exception(\"Unable to upload handler plugin code to the server (msg: %s)\" % res.result)\n
# Exception: Unable to upload handler plugin code to the server (msg: {'message': 'An unexpected error occurred in the server
# while processing the request: (\\'insert or update on table \"code\" violates foreign key constraint \"code_configmodel_fk\"\\',)'})
# \n\n================================ EXPORT FAILURE ================================\nError: Unable to upload handler plugin code to the server
# (msg: {'message': 'An unexpected error occurred in the server while processing the request: (\\'insert or update on table \"code\" violates foreign key constraint \"code_configmodel_fk\"\\',)'})\n",
