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

import os

from mongobox.unittest import MongoTestCase
from mongoengine.connection import connect, disconnect
from impera import data


class testDataObjects(MongoTestCase):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)

    @classmethod
    def setUpClass(cls):
        mongo_port = os.getenv('MONGOBOX_PORT')
        if mongo_port is None:
            raise Exception("MONGOBOX_PORT env variable not available. Make sure test are executed with --with-mongobox")

        connect(host="localhost", port=int(mongo_port))

    @classmethod
    def tearDownClass(cls):
        disconnect()

    def tearDown(self):
        MongoTestCase.tearDown(self)
        self.purge_database()

    def testEnvironment(self):
        pass