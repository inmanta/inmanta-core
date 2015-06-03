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
from concurrent import futures
import logging

from impera import config
from impera.server import Server
from impera.agent import Agent
from impera import protocol
from impera import methods

from nose import tools


def test_discovery():
    """ Test discovery of new nodes using a direct transport
    """
    protocol.Transport.offline = True
    protocol.DirectTransport.connections = [("client", "agent"), ("client", "server"),
                                            ("server_client", "agent"), ("agent_client", "server")]
    server_obj = None
    agent_obj1 = None
    agent_obj2 = None
    try:
        state_dir = tempfile.mkdtemp()
        config.Config.load_config()
        config.Config.set("config", "state-dir", state_dir)

        executor = futures.ThreadPoolExecutor(max_workers=10)

        server_obj = Server(code_loader=False)
        server_future = executor.submit(server_obj.start)

        agent_obj1 = Agent(code_loader=False, hostname="testhost1")
        agent_obj1._node_name = "testnode1"
        agent_future1 = executor.submit(agent_obj1.start)

        agent_obj2 = Agent(code_loader=False, hostname="testhost2")
        agent_obj2._node_name = "testnode2"
        agent_future2 = executor.submit(agent_obj2.start)

        print("Server and agent are running")
        conn = protocol.Client("client", "client", [protocol.DirectTransport])
        conn.start()

        result = conn.call(methods.PingMethod, destination="*")

        result.wait(timeout=1)
        tools.assert_true(result.available())
        tools.assert_equal(len(result.result), 3, "Should return two agents and a server as results.")

        conn.stop()

    finally:
        if server_obj is not None:
            server_obj.stop()
            server_future.result()

        if agent_obj1 is not None:
            agent_obj1.stop()
            agent_future1.result()

        if agent_obj2 is not None:
            agent_obj2.stop()
            agent_future2.result()

        shutil.rmtree(state_dir)


if __name__ == "__main__":
    stream = logging.StreamHandler()
    stream.setLevel(logging.DEBUG)

    logging.root.handlers = []
    logging.root.addHandler(stream)
    logging.root.setLevel(logging.DEBUG)

    test_discovery()