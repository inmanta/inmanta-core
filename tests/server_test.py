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


from mongobox.unittest import MongoTestCase
from impera import config
from impera.server import Server


class ServerTest(MongoTestCase):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.state_dir = None
        self.server_future = None
        self.server = None

    def setUp(self):
        self.state_dir = tempfile.mkdtemp()
        config.Config.load_config()
        config.Config.set("config", "state-dir", self.state_dir)

        mongo_port = os.getenv('MONGOBOX_PORT')
        if mongo_port is None:
            raise Exception("MONGOBOX_PORT env variable not available. Make sure test are executed with --with-mongobox")

        self.server = Server(database_host="localhost", database_port=int(mongo_port))

        executor = futures.ThreadPoolExecutor(max_workers=2)
        self.server_future = executor.submit(self.server.start)

    def tearDown(self):
        self.server.stop()
        self.server_future.result()
        self.purge_database()
        shutil.rmtree(self.state_dir)
