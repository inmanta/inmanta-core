"""
    Copyright 2017 Inmanta

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
from inmanta import protocol
import time


def test_jwt_create(inmanta_config):
    """
        Test creating, signing and verifying JWT with HS256 from the configuration
    """
    jot = protocol.encode_token(["api"])
    payload = protocol.decode_token(jot)

    assert "api" in payload["urn:inmanta:ct"]

    # test creating an idempotent token
    jot1 = protocol.encode_token(["agent"], idempotent=True)
    jot3 = protocol.encode_token(["agent"])
    time.sleep(1)
    jot2 = protocol.encode_token(["agent"], idempotent=True)
    jot4 = protocol.encode_token(["agent"])
    assert jot1 == jot2
    assert jot3 != jot4
    assert jot1 != jot3
    assert jot2 != jot3
