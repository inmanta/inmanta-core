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
import random
import base64

import pytest


@pytest.mark.gen_test
def test_client_files(client):
    file_name = str(random.randint(0, 10000))
    body = base64.b64encode(b"Hello world\n").decode("ascii")

    # Check if the file exists
    result = yield client.stat_file(id="test" + file_name)
    assert result.code == 404

    # Create the file
    result = yield client.upload_file(id="test" + file_name, content=body)
    assert result.code == 200

    # Get the file
    result = yield client.get_file(id="test" + file_name)
    assert result.code == 200
    assert "content" in result.result
    assert result.result["content"] == body

    file_names = []
    i = 0
    while i < 10:
        file_name = "test%d" % random.randint(0, 10000)
        if file_name not in file_names:
            file_names.append(file_name)
            result = yield client.upload_file(id=file_name, content="")
            assert result.code == 200
            i += 1

    result = yield client.stat_files(files=file_names)
    assert len(result.result["files"]) == 0

    other_files = ["testtest"]
    result = yield client.stat_files(files=file_names + other_files)
    assert len(result.result["files"]) == len(other_files)


@pytest.mark.gen_test
def test_diff(client):
    result = yield client.upload_file(id="a", content=base64.b64encode(b"Hello world\n").decode("ascii"))
    assert(result.code == 200)

    result = yield client.upload_file(id="b", content=base64.b64encode(b"Bye bye world\n").decode("ascii"))
    assert(result.code == 200)

    diff = yield client.diff("a", "b")
    assert(diff.code == 200)
    assert(len(diff.result["diff"]) == 5)

    diff = yield client.diff(0, "b")
    assert(diff.code == 200)
    assert(len(diff.result["diff"]) == 4)

    diff = yield client.diff("a", 0)
    assert(diff.code == 200)
    assert(len(diff.result["diff"]) == 4)
