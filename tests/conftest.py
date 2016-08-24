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

from mongobox import MongoBox
import pytest

DEFAULT_PORT_ENVVAR = 'MONGOBOX_PORT'


@pytest.yield_fixture(scope="session", autouse=True)
def mongo_db():
    mongobox = MongoBox()
    port_envvar = DEFAULT_PORT_ENVVAR

    mongobox.start()
    os.environ[port_envvar] = str(mongobox.port)

    yield mongobox

    mongobox.stop()
    del os.environ[port_envvar]
