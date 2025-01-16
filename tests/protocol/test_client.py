"""
    Copyright 2024 Inmanta

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

import logging

import utils


async def test_request_too_long(environment, client, caplog):
    caplog.set_level(logging.INFO)
    result = await client.get_facts(environment, "a" * 100000)
    assert result.code == 599
    assert "Stream closed header is too long (estimated size " in result.result["message"]
    utils.log_contains(
        caplog,
        "tornado.general",
        logging.INFO,
        r"Unsatisfiable read, closing connection: delimiter re.compile(b'\r?\n\r?\n') not found within 65536 bytes",
    )
    utils.log_contains(
        caplog, "inmanta.protocol.rest.client", logging.ERROR, r"Failed to send request, header is too long (estimated size "
    )
