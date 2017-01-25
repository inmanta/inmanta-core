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

import pytest

LOGGER = logging.getLogger(__name__)


@pytest.mark.gen_test(timeout=60)
def test_form(client, environment):
    """
        Test creating and updating forms
    """
    form_id = "cwdemo::forms::ClearwaterSize"
    form_data = {
        'attributes': {
            'bono': {'default': 1,
                     'options': {'min': 1, 'max': 100, 'widget': 'slider', 'help': 'help'},
                     'type': 'number'},
            'ralf': {'default': 1,
                     'options': {'min': 1, 'max': 100, 'widget': 'slider', 'help': 'help'},
                     'type': 'number'}
        },
        'options': {'title': 'VNF replication', 'help': 'help', 'record_count': 1},
        'type': 'cwdemo::forms::ClearwaterSize'
    }
    result = yield client.put_form(tid=environment, id=form_id, form=form_data)
    assert(result.code == 200)

    result = yield client.get_form(environment, form_id)
    assert(result.code == 200)

    result = yield client.list_forms(environment)
    assert(result.code == 200)
    assert(len(result.result["forms"]) == 1)
    assert(result.result["forms"][0]["form_type"] == form_id)


@pytest.mark.gen_test(timeout=60)
def test_update_form(client, environment):
    """
        Test creating and updating forms
    """
    form_id = "cwdemo::forms::ClearwaterSize"
    form_data = {
        'attributes': {
            'bono': {'default': 1,
                     'options': {'min': 1, 'max': 100, 'widget': 'slider', 'help': 'help'},
                     'type': 'number'},
            'ralf': {'default': 1,
                     'options': {'min': 1, 'max': 100, 'widget': 'slider', 'help': 'help'},
                     'type': 'number'}
        },
        'options': {'title': 'VNF replication', 'help': 'help', 'record_count': 1},
        'type': 'cwdemo::forms::ClearwaterSize'
    }
    result = yield client.put_form(tid=environment, id=form_id, form=form_data)
    assert(result.code == 200)

    result = yield client.get_form(environment, form_id)
    assert(result.code == 200)
    assert(len(result.result["form"]["field_options"]) == 2)

    form_data["attributes"]["sprout"] = {'default': 1, 'options': {'min': 1, 'max': 100, 'widget': 'slider', 'help': 'help'},
                                         'type': 'number'}
    result = yield client.put_form(tid=environment, id=form_id, form=form_data)
    assert(result.code == 200)

    result = yield client.get_form(environment, form_id)
    assert(result.code == 200)
    assert(len(result.result["form"]["field_options"]) == 3)


@pytest.mark.gen_test(timeout=60)
def test_records(client, environment):
    """
        Test creating and updating forms
    """
    form_id = "FormType"
    result = yield client.put_form(tid=environment, id=form_id,
                                   form={'attributes': {'field1': {'default': 1, 'options': {'min': 1, 'max': 100},
                                                                   'type': 'number'},
                                                        'field2': {'default': "", 'options': {}, 'type': 'string'}},
                                         'options': {},
                                         'type': form_id}
                                   )
    assert(result.code == 200)

    result = yield client.create_record(tid=environment, form_type=form_id, form={"field1": 10, "field2": "value"})
    assert(result.code == 200)

    record_id = result.result["record"]["id"]
    result = yield client.update_record(tid=environment, id=record_id, form={"field1": 20, "field2": "value2"})
    assert(result.code == 200)

    result = yield client.get_record(tid=environment, id=record_id)
    assert(result.code == 200)

    result = yield client.list_records(tid=environment, form_type=form_id)
    assert(result.code == 200)
    assert(len(result.result["records"]) == 1)

    yield client.create_record(tid=environment, form_type=form_id, form={"field1": 10, "field2": "value"})
    result = yield client.list_records(tid=environment, form_type=form_id, include_record=True)
    assert(result.code == 200)
    assert(len(result.result["records"]) == 2)
    assert("field1" in result.result["records"][0]["fields"])

    result = yield client.delete_record(tid=environment, id=record_id)
    assert(result.code == 200)
