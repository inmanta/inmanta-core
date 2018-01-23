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
from inmanta.util import hash_file
from inmanta.server import config as opt
import os


def make_random_file():
    randomvalue = str(random.randint(0, 10000))

    content = ("Hello world %s\n" % (randomvalue)).encode()
    hash = hash_file(content)

    body = base64.b64encode(content).decode("ascii")

    return(hash, content, body)


@pytest.mark.gen_test
def test_client_files(client):
    (hash, content, body) = make_random_file()

    # Check if the file exists
    result = yield client.stat_file(id=hash)
    assert result.code == 404

    # Create the file
    result = yield client.upload_file(id=hash, content=body)
    assert result.code == 200

    # Get the file
    result = yield client.get_file(id=hash)
    assert result.code == 200
    assert "content" in result.result
    assert result.result["content"] == body


@pytest.mark.gen_test
def test_client_files_stat(client):

    file_names = []
    i = 0
    while i < 10:
        (hash, content, body) = make_random_file()
        if hash not in file_names:
            file_names.append(hash)
            result = yield client.upload_file(id=hash, content=body)
            assert result.code == 200
            i += 1

    result = yield client.stat_files(files=file_names)
    assert len(result.result["files"]) == 0

    other_files = ["testtest"]
    result = yield client.stat_files(files=file_names + other_files)
    assert len(result.result["files"]) == len(other_files)


@pytest.mark.gen_test
def test_diff(client):
    ca = "Hello world\n".encode()
    ha = hash_file(ca)
    result = yield client.upload_file(id=ha, content=base64.b64encode(ca).decode("ascii"))
    assert(result.code == 200)

    cb = "Bye bye world\n".encode()
    hb = hash_file(cb)
    result = yield client.upload_file(id=hb, content=base64.b64encode(cb).decode("ascii"))
    assert(result.code == 200)

    diff = yield client.diff(ha, hb)
    assert(diff.code == 200)
    assert(len(diff.result["diff"]) == 5)

    diff = yield client.diff(0, hb)
    assert(diff.code == 200)
    assert(len(diff.result["diff"]) == 4)

    diff = yield client.diff(ha, 0)
    assert(diff.code == 200)
    assert(len(diff.result["diff"]) == 4)


@pytest.mark.gen_test
def test_client_files_bad(client):
    (hash, content, body) = make_random_file()
    # Create the file
    result = yield client.upload_file(id=hash + "a", content=body)
    assert result.code == 400


@pytest.mark.gen_test
def test_client_files_corrupt(client):
    (hash, content, body) = make_random_file()
    # Create the file
    result = yield client.upload_file(id=hash, content=body)
    assert result.code == 200

    state_dir = opt.state_dir.get()

    file_dir = os.path.join(state_dir, "server", "files")

    file_name = os.path.join(file_dir, hash)

    with open(file_name, "wb+") as fd:
        fd.write("Haha!".encode())

    opt.server_delete_currupt_files.set("false")
    result = yield client.get_file(id=hash)
    assert result.code == 500

    result = yield client.upload_file(id=hash, content=body)
    assert result.code == 500

    opt.server_delete_currupt_files.set("true")
    result = yield client.get_file(id=hash)
    assert result.code == 500

    result = yield client.upload_file(id=hash, content=body)
    assert result.code == 200
