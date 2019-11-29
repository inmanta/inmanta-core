"""
    Copyright 2019 Inmanta

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
import datetime
import logging
import uuid
from typing import List, cast

from inmanta import data
from inmanta.ast import type
from inmanta.protocol import exceptions, methods
from inmanta.protocol.common import attach_warnings
from inmanta.protocol.exceptions import NotFound
from inmanta.server import SLICE_DATABASE, SLICE_FORM, SLICE_SERVER, SLICE_TRANSPORT, protocol
from inmanta.server.extensions import Feature, BoolFeature
from inmanta.server.server import Server
from inmanta.types import Apireturn, JsonType

LOGGER = logging.getLogger(__name__)


forms_feature = BoolFeature(slice=SLICE_FORM, name="forms", description="Custom forms and records for external parameters.")


class FormService(protocol.ServerSlice):
    """Slice for form functionality"""

    server_slice: Server

    def __init__(self) -> None:
        super(FormService, self).__init__(SLICE_FORM)

    def get_dependencies(self) -> List[str]:
        return [SLICE_SERVER, SLICE_DATABASE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.server_slice = cast(Server, server.get_slice(SLICE_SERVER))

    def define_features(self) -> List[Feature]:
        return [forms_feature]

    @protocol.handle(methods.put_form, form_id="id", env="tid")
    async def put_form(self, env: data.Environment, form_id: str, form: JsonType) -> Apireturn:
        if not self.feature_manager.enabled(forms_feature):
            raise exceptions.Forbidden()

        form_doc = await data.Form.get_form(environment=env.id, form_type=form_id)
        fields = {k: v["type"] for k, v in form["attributes"].items()}
        defaults = {k: v["default"] for k, v in form["attributes"].items() if "default" in v}
        field_options = {k: v["options"] for k, v in form["attributes"].items() if "options" in v}

        if form_doc is None:
            form_doc = data.Form(
                environment=env.id,
                form_type=form_id,
                fields=fields,
                defaults=defaults,
                options=form["options"],
                field_options=field_options,
            )
            await form_doc.insert()

        else:
            # update the definition
            form_doc.fields = fields
            form_doc.defaults = defaults
            form_doc.options = form["options"]
            form_doc.field_options = field_options

            await form_doc.update()

        return 200, {"form": {"id": form_doc.form_type}}

    @protocol.handle(methods.get_form, form_id="id", env="tid")
    async def get_form(self, env: data.Environment, form_id: str) -> Apireturn:
        if not self.feature_manager.enabled(forms_feature):
            raise exceptions.Forbidden()

        form = await data.Form.get_form(environment=env.id, form_type=form_id)

        if form is None:
            return 404

        return 200, {"form": form}

    @protocol.handle(methods.list_forms, env="tid")
    async def list_forms(self, env: data.Environment) -> Apireturn:
        if not self.feature_manager.enabled(forms_feature):
            raise exceptions.Forbidden()

        forms = await data.Form.get_list(environment=env.id)
        return 200, {"forms": [{"form_id": x.form_type, "form_type": x.form_type} for x in forms]}

    @protocol.handle(methods.list_records, env="tid")
    async def list_records(self, env: data.Environment, form_type: str, include_record: bool) -> Apireturn:
        if not self.feature_manager.enabled(forms_feature):
            raise exceptions.Forbidden()

        form_type_obj = await data.Form.get_form(environment=env.id, form_type=form_type)
        if form_type_obj is None:
            raise NotFound("No form is defined with id %s" % form_type)

        records = await data.FormRecord.get_list(form=form_type_obj.form_type)

        if not include_record:
            return 200, {"records": [{"id": r.id, "changed": r.changed} for r in records]}

        else:
            return 200, {"records": records}

    @protocol.handle(methods.get_record, record_id="id", env="tid")
    async def get_record(self, env: data.Environment, record_id: uuid.UUID) -> Apireturn:
        if not self.feature_manager.enabled(forms_feature):
            raise exceptions.Forbidden()

        record = await data.FormRecord.get_by_id(record_id)
        if record is None:
            return 404, {"message": "The record with id %s does not exist" % record_id}

        return 200, {"record": record}

    @protocol.handle(methods.update_record, record_id="id", env="tid")
    async def update_record(self, env: data.Environment, record_id: uuid.UUID, form: JsonType) -> Apireturn:
        if not self.feature_manager.enabled(forms_feature):
            raise exceptions.Forbidden()

        record = await data.FormRecord.get_by_id(record_id)
        if record is None or record.environment != env.id:
            raise NotFound("The record with id %s does not exist" % record_id)

        form_def = await data.Form.get_one(environment=env.id, form_type=record.form)

        record.changed = datetime.datetime.now()

        for k, _v in form_def.fields.items():
            if k in form_def.fields and k in form:
                value = form[k]
                field_type = form_def.fields[k]
                if field_type in type.TYPES:
                    type_obj = type.TYPES[field_type]
                    record.fields[k] = type_obj.cast(value)
                else:
                    LOGGER.warning("Field %s in record %s of form %s has an invalid type." % (k, record_id, form))

        await record.update()

        metadata = {
            "message": "Recompile model because a form record was updated",
            "type": "form",
            "records": [str(record_id)],
            "form": form,
        }

        warnings = await self.server_slice._async_recompile(env, False, metadata=metadata)
        return attach_warnings(200, {"record": record}, warnings)

    @protocol.handle(methods.create_record, env="tid")
    async def create_record(self, env: data.Environment, form_type: str, form: JsonType) -> Apireturn:
        if not self.feature_manager.enabled(forms_feature):
            raise exceptions.Forbidden()

        form_obj = await data.Form.get_form(environment=env.id, form_type=form_type)

        if form_obj is None:
            raise NotFound(f"The form {env.id} does not exist in env {form_type}")

        record = data.FormRecord(environment=env.id, form=form_obj.form_type, fields={})
        record.changed = datetime.datetime.now()

        for k, _v in form_obj.fields.items():
            if k in form:
                value = form[k]
                field_type = form_obj.fields[k]
                if field_type in type.TYPES:
                    type_obj = type.TYPES[field_type]
                    record.fields[k] = type_obj.cast(value)
                else:
                    LOGGER.warning("Field %s in form %s has an invalid type." % (k, form_type))

        await record.insert()
        metadata = {
            "message": "Recompile model because a form record was inserted",
            "type": "form",
            "records": [str(record.id)],
            "form": form,
        }
        warnings = await self.server_slice._async_recompile(env, False, metadata=metadata)

        return attach_warnings(200, {"record": record}, warnings)

    @protocol.handle(methods.delete_record, record_id="id", env="tid")
    async def delete_record(self, env: data.Environment, record_id: uuid.UUID) -> Apireturn:
        if not self.feature_manager.enabled(forms_feature):
            raise exceptions.Forbidden()

        record = await data.FormRecord.get_by_id(record_id)
        if record is None:
            raise NotFound()
        await record.delete()

        metadata = {
            "message": "Recompile model because a form record was removed",
            "type": "form",
            "records": [str(record.id)],
            "form": record.form,
        }

        warnings = await self.server_slice._async_recompile(env, False, metadata=metadata)

        return attach_warnings(200, None, warnings)
