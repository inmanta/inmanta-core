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
import logging
import uuid

import pytest
import yaml

from inmanta.config import feature_file_config

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def server_pre_start(tmp_path):
    feature_file = tmp_path / "features.yml"
    feature_file.write_text(yaml.dump({"slices": {"core.forms": {"forms": False}}}))
    feature_file_config.set(str(feature_file))


@pytest.mark.asyncio(timeout=60)
async def test_form_features(server_pre_start, client, environment):
    """
        Test creating and updating forms
    """
    form_id = "cwdemo::forms::ClearwaterSize"
    form_data = {
        "attributes": {
            "bono": {"default": 1, "options": {"min": 1, "max": 100, "widget": "slider", "help": "help"}, "type": "number"},
            "ralf": {"default": 1, "options": {"min": 1, "max": 100, "widget": "slider", "help": "help"}, "type": "number"},
        },
        "options": {"title": "VNF replication", "help": "help", "record_count": 1},
        "type": "cwdemo::forms::ClearwaterSize",
    }
    result = await client.put_form(tid=environment, id=form_id, form=form_data)
    assert result.code == 403

    result = await client.get_form(environment, form_id)
    assert result.code == 403

    result = await client.list_forms(environment)
    assert result.code == 403

    result = await client.list_records(environment, "cwdemo::forms::ClearwaterSize")
    assert result.code == 403

    result = await client.get_record(environment, uuid.uuid4())
    assert result.code == 403

    result = await client.update_record(environment, uuid.uuid4(), {})
    assert result.code == 403

    result = await client.create_record(environment, uuid.uuid4(), {})
    assert result.code == 403

    result = await client.delete_record(environment, uuid.uuid4())
    assert result.code == 403
