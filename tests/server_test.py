"""
    Copyright 2016 Inmanta

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
import tempfile
import shutil
import logging
import string
import random

from mongobox.unittest import MongoTestCase
from inmanta import config
from inmanta.server import Server
from tornado.testing import AsyncTestCase

LOGGER = logging.getLogger(__name__)
PORT = "45678"


class ServerTest(MongoTestCase, AsyncTestCase):

    def __init__(self, methodName='runTest'):  # noqa: H803
        MongoTestCase.__init__(self, methodName)
        AsyncTestCase.__init__(self, methodName)

        self.state_dir = None
        self.server = None

    def setUp(self):
        MongoTestCase.setUp(self)
        AsyncTestCase.setUp(self)

        self.state_dir = tempfile.mkdtemp()
        cfg = os.path.join(self.state_dir, "inmanta.cfg")
        with open(cfg, "w"):
            pass
        config.Config.load_config(cfg)
        config.Config.get("database", "name", "inmanta-" + ''.join(random.choice(string.ascii_letters) for _ in range(10)))
        config.Config.set("config", "state-dir", self.state_dir)
        config.Config.set("config", "log-dir", os.path.join(self.state_dir, "logs"))
        config.Config.set("server_rest_transport", "port", PORT)
        config.Config.set("agent_rest_transport", "port", PORT)
        config.Config.set("compiler_rest_transport", "port", PORT)
        config.Config.set("client_rest_transport", "port", PORT)
        config.Config.set("cmdline_rest_transport", "port", PORT)
        config.Config.set("config", "executable", os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py")))
        config.Config.set("server", "agent-timeout", "2")

        LOGGER.info("Starting server")
        mongo_port = os.getenv('MONGOBOX_PORT')
        if mongo_port is None:
            raise Exception("MONGOBOX_PORT env variable not available. Make sure test are executed with --with-mongobox")

        self.server = Server(database_host="localhost", database_port=int(mongo_port), io_loop=self.io_loop)

    def tearDown(self):
        self.server.stop()
        # does not work with current pymongo
        for db_name in self.mongo_client.database_names():
            self.mongo_client.drop_database(db_name)
        # end fix
        shutil.rmtree(self.state_dir)

        AsyncTestCase.tearDown(self)
        MongoTestCase.tearDown(self)
