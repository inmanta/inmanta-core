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

import logging
from pathlib import Path
from typing import cast

from inmanta import const, data
from inmanta.data import get_session, model
from inmanta.data.sqlalchemy import FilesInModule, Module
from inmanta.loader import convert_relative_path_to_module
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.common import ReturnValue
from inmanta.protocol.exceptions import BadRequest, NotFound, ServerError
from inmanta.server import SLICE_CODE, SLICE_DATABASE, SLICE_FILE, SLICE_TRANSPORT, protocol
from inmanta.server.services.fileservice import FileService
from inmanta.types import Apireturn, JsonType
from sqlalchemy.dialects.postgresql import insert

LOGGER = logging.getLogger(__name__)


class CodeService(protocol.ServerSlice):
    """Slice serving and managing code"""

    file_slice: FileService

    def __init__(self) -> None:
        super().__init__(SLICE_CODE)

    def get_dependencies(self) -> list[str]:
        return [SLICE_FILE, SLICE_DATABASE]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.file_slice = cast(FileService, server.get_slice(SLICE_FILE))

    @handle(methods_v2.upload_modules, env="tid")
    async def upload_modules(self, env: data.Environment, modules_data: JsonType) -> ReturnValue[None]:
        """

        :param modules_data: dict with key module name and value loader.PythonModule
        :return:
        """
        LOGGER.debug(f"{env=}")
        # LOGGER.debug(f"{modules_data=}")
        module_stmt = insert(Module).on_conflict_do_nothing()

        files_in_module_stmt = insert(FilesInModule).on_conflict_do_nothing()

        if not modules_data:
            raise BadRequest("No modules were provided")
        module_data = []
        files_in_module_data = []
        for module_name, python_module in modules_data.items():

            requirements: set[str] = set()

            for file in python_module["files_in_module"]:
                parts = Path(file["path"]).parts
                if const.PLUGINS_PACKAGE in parts:
                    file_path = str(Path(*parts[parts.index(const.PLUGINS_PACKAGE) :]))
                else:
                    relative_path = Path(*parts[parts.index(module_name) :])
                    file_path = convert_relative_path_to_module(str(relative_path))

                file_in_module = {
                    "module_name": module_name,
                    "module_version": python_module["version"],
                    "environment": env.id,
                    "file_content_hash": file["hash"],
                    "file_path": file_path,
                }
                requirements.update(file["requires"])
                files_in_module_data.append(file_in_module)

            module = {
                "name": module_name,
                "version": python_module["version"],
                "environment": env.id,
                "requirements": requirements,
            }

            module_data.append(module)

        async with get_session() as session:
            await session.execute(module_stmt, module_data)
            await session.execute(files_in_module_stmt, files_in_module_data)
            await session.commit()

        return ReturnValue(response=None)


