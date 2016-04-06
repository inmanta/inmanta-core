"""
    Copyright 2016 Impera

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

import os
import tempfile
from concurrent import futures
import shutil
from http import client
import time
import logging


from mongobox.unittest import MongoTestCase
from impera import config
from impera.server import Server

LOGGER = logging.getLogger(__name__)


class ServerTest(MongoTestCase):
    state_dir = None
    server_future = None
    server = None

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)

    @classmethod
    def setUpClass(cls):
        if cls.server is not None:
            LOGGER.error("Server is already started")
            return

        cls.state_dir = tempfile.mkdtemp()
        config.Config.load_config()
        config.Config.set("config", "state-dir", cls.state_dir)

        LOGGER.info("Starting server")
        mongo_port = os.getenv('MONGOBOX_PORT')
        if mongo_port is None:
            raise Exception("MONGOBOX_PORT env variable not available. Make sure test are executed with --with-mongobox")

        cls.server = Server(database_host="localhost", database_port=int(mongo_port))
        executor = futures.ThreadPoolExecutor(max_workers=1)
        cls.server_future = executor.submit(cls.server.start)

        attempts = 10
        while attempts > 0:
            attempts -= 1
            try:
                LOGGER.info("Waiting for server to become availabe")
                conn = client.HTTPConnection("localhost", 8888)
                conn.request("GET", "/")
                res = conn.getresponse()

                if res.status == 404:
                    return

            except ConnectionRefusedError:
                time.sleep(0.1)

    def tearDown(self):
        self.purge_database()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.server_future.result()
        shutil.rmtree(cls.state_dir)
        cls.server = None
        cls.server_future = None
