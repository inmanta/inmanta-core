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
import hashlib
import logging
from typing import cast

from sqlalchemy import insert

from inmanta import data
from inmanta.data import model, get_session
from inmanta.data.sqlalchemy import FilesInModule, ModuleRequirements
from inmanta.protocol import handle, methods, methods_v2
from inmanta.protocol.exceptions import BadRequest, NotFound, ServerError
from inmanta.server import SLICE_CODE, SLICE_DATABASE, SLICE_FILE, SLICE_TRANSPORT, protocol
from inmanta.server.services.fileservice import FileService
from inmanta.types import Apireturn, JsonType

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
    async def upload_modules(self, env: data.Environment, modules_data: JsonType) -> Apireturn:
        LOGGER.debug(f"{env=}")
        LOGGER.debug(f"{modules_data=}")
        module_requirements_stmt = insert(ModuleRequirements)
        files_in_module_stmt = insert(FilesInModule)

        module_requirements_data = []
        files_in_module_data = []
        for module_name, python_module in modules_data.items():

            requirements: set[str] = set()

            for file in python_module["files_in_module"]:
                file_in_module = {
                    "module_name": module_name,
                    "module_version": python_module["module_version"],
                    "environment": env.id,
                    "file_content_hash": file['hash'],
                    "file_path": file['path'],
                }
                requirements.update(file['requires'])
                files_in_module_data.append(file_in_module)

            module_requirements = {
                "module_name": module_name,
                "module_version": python_module["module_version"],
                "environment": env.id,
                "requirements": requirements,
            }

            module_requirements_data.append(module_requirements)

        async with get_session() as session:
            await session.execute(module_requirements_stmt, module_requirements_data)
            await session.execute(files_in_module_stmt, files_in_module_data)
            await session.commit()


    @handle(methods.upload_code_batched, code_id="id", env="tid")
    async def upload_code_batched(self, env: data.Environment, code_id: int, resources: JsonType) -> Apireturn:
        # raise NotImplementedError("Endpoint moved to methods_v2.upload_modules.")
        # validate
        for rtype, sources in resources.items():
            if not isinstance(rtype, str):
                raise BadRequest("All keys in the resources map must be strings")
            if not isinstance(sources, dict):
                raise BadRequest("All values in the resources map must be dicts")

            for name, refs in sources.items():
                if not isinstance(name, str):
                    raise BadRequest("All keys in the sources map must be strings")
                if not isinstance(refs, (list, tuple)):
                    raise BadRequest("All values in the sources map must be lists or tuple")
                if (
                    len(refs) != 3
                    or not isinstance(refs[0], str)
                    or not isinstance(refs[1], str)
                    or not isinstance(refs[2], list)
                ):
                    raise BadRequest("The values in the source map should be of the form (filename, module, [requirements])")

        # list of file hashes
        allrefs = [ref for sourcemap in resources.values() for ref in sourcemap.keys()]

        val = await self.file_slice.stat_file_internal(allrefs)

        if len(val) != 0:
            raise BadRequest("Not all file references provided are valid", details={"references": val})

        code = await data.Code.get_versions(environment=env.id, version=code_id)
        oldmap: dict[str, data.Code] = {c.resource: c for c in code}

        new = {k: v for k, v in resources.items() if k not in oldmap}
        conflict = [k for k, v in resources.items() if k in oldmap and oldmap[k].source_refs != v]

        if len(conflict) > 0:
            raise ServerError(
                "Some of these items already exists, but with different source files", details={"references": conflict}
            )

        newcodes = [
            data.Code(environment=env.id, version=code_id, resource=resource, source_refs=hashes)
            for resource, hashes in new.items()
        ]

        await data.Code.insert_many(newcodes)

        return 200

    @handle(methods_v2.get_source_code, env="tid")
    async def get_source_code(self, env: data.Environment, version: int, resource_type: str) -> list[model.Source]:
        code = await data.Code.get_version(environment=env.id, version=version, resource=resource_type)
        if code is None:
            raise NotFound(f"The version of the code does not exist. {resource_type}, {version}")

        sources = []

        # Get all module code pertaining to this env/version/resource
        if code.source_refs is not None:
            for code_hash, (file_name, module, requires) in code.source_refs.items():
                sources.append(
                    model.Source(
                        hash=code_hash, is_byte_code=file_name.endswith(".pyc"), module_name=module, requirements=requires
                    )
                )

        return sources

    @handle(methods_v2.get_module_source_for_agent, env="tid")
    async def get_module_source_for_agent(self, env: data.Environment, agent: str, model_version: int) -> list[model.Source]:
        # code = await data.Code.get_version(environment=env.id, version=version, resource=resource_type)
        # if code is None:
        #     raise NotFound(f"The version of the code does not exist. {resource_type}, {version}")
        #
        # sources = []
        #
        # # Get all module code pertaining to this env/version/resource
        # if code.source_refs is not None:
        #     for code_hash, (file_name, module, requires) in code.source_refs.items():
        #         sources.append(
        #             model.Source(
        #                 hash=code_hash, is_byte_code=file_name.endswith(".pyc"), module_name=module, requirements=requires
        #             )
        #         )
        #
        # return sources
        pass
