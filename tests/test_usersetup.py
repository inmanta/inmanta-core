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
import os

import inmanta
from inmanta.server import protocol
from inmanta.user_setup import cmd


async def test_user_setup(server: protocol.Server, tmpdir, postgres_db, database_name, cli):
    dot_inmanta_cfg_file = os.path.join(tmpdir, ".inmanta.cfg")
    with open(dot_inmanta_cfg_file, "w", encoding="utf-8") as f:
        f.write(
            f"""
[server]
auth=true
auth_method=database

[auth_jwt_default]
algorithm=HS256
sign=true
client_types=agent,compiler,api
key=eciwliGyqECVmXtIkNpfVrtBLutZiITZKSKYhogeHMM
expire=0
issuer=https://localhost:8888/
audience=https://localhost:8888/

[database]
name={database_name}
host=localhost
port={str(postgres_db.port)}
username={postgres_db.user}
password={postgres_db.password}
connection_timeout=3
        """
        )
    os.chdir(tmpdir)

    result = await cli.run(cmd, cli=inmanta.user_setup)

    print(result)
