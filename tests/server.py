"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""

import tempfile
import shutil
import time
from concurrent import futures

from impera import config
from impera import server
from impera import protocol
from impera import methods

from nose import tools


def test_version_removal():
    """ Test auto removal of older deploy model versions
    """
    protocol.Transport.offline = True
    protocol.DirectTransport.connections = [("client", "server"), ("server_client", "agent"), ("agent_client", "server")]
    try:
        state_dir = tempfile.mkdtemp()
        config.Config.load_config()
        config.Config.set("config", "state-dir", state_dir)

        executor = futures.ThreadPoolExecutor(max_workers=2)

        server_obj = server.Server(code_loader=False)
        server_future = executor.submit(server_obj.start)

        conn = protocol.Client("client", "client", [protocol.RESTTransport, protocol.DirectTransport])
        conn.start()
        version = int(time.time())
        for _i in range(20):
            version += 1
            conn.call(methods.VersionMethod, operation="PUT", id=version, version=version, resources=[])
            tools.assert_less_equal(len(server_obj._db.filter(server.persistence.Version, {})), 2)

        conn.stop()
    finally:
        server_obj.stop()
        server_future.result()
        shutil.rmtree(state_dir)
