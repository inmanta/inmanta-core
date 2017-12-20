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

import pytest
from tornado import gen


@pytest.mark.gen_test(timeout=10)
@pytest.mark.slowtest
def test_compile_report(server):
    from inmanta import protocol

    client = protocol.Client("client")
    result = yield client.create_project("env-test")
    assert result.code == 200
    project_id = result.result["project"]["id"]

    result = yield client.create_environment(project_id=project_id, name="dev")
    env_id = result.result["environment"]["id"]

    result = yield client.notify_change(id=env_id)
    assert result.code == 200

    while True:
        result = yield client.get_reports(tid=env_id)
        assert result.code == 200
        if len(result.result["reports"]) > 0:
            break

        yield gen.sleep(0.5)

    report = result.result["reports"][0]
    report_id = report["id"]

    result = yield client.get_report(report_id)
    assert result.code == 200
    assert len(result.result["report"]["reports"]) == 1
