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
from typing import Dict, List, cast

from inmanta import data
from inmanta.protocol import handle, methods
from inmanta.protocol.exceptions import BadRequest, NotFound, ServerError
from inmanta.server import SLICE_CODE, SLICE_DATABASE, SLICE_FILE, SLICE_TRANSPORT, protocol
from inmanta.server.services.fileservice import FileService
from inmanta.types import Apireturn, JsonType
from inmanta.util import hash_file

LOGGER = logging.getLogger(__name__)


class CodeService(protocol.ServerSlice):
    """Slice serving and managing code"""

    file_slice: FileService

    def __init__(self) -> None:
        super(CodeService, self).__init__(SLICE_CODE)

    def get_dependencies(self) -> List[str]:
        return [SLICE_FILE, SLICE_DATABASE]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.file_slice = cast(FileService, server.get_slice(SLICE_FILE))

    @handle(methods.upload_code, code_id="id", env="tid")
    async def upload_code(self, env: data.Environment, code_id: int, resource: str, sources: JsonType) -> Apireturn:
        code = await data.Code.get_version(environment=env.id, version=code_id, resource=resource)
        if code is not None:
            raise ServerError("Code for this version has already been uploaded.")

        hasherrors = any((k != hash_file(content[2].encode()) for k, content in sources.items()))
        if hasherrors:
            return 400, {"message": "Hashes in source map do not match to source_code"}

        for file_hash in self.file_slice.stat_file_internal(sources.keys()):
            self.file_slice.upload_file_internal(file_hash, sources[file_hash][2].encode())

        compact = {code_hash: (file_name, module, req) for code_hash, (file_name, module, _, req) in sources.items()}

        code = data.Code(environment=env.id, version=code_id, resource=resource, source_refs=compact)
        await code.insert()

        return 200

    @handle(methods.upload_code_batched, code_id="id", env="tid")
    async def upload_code_batched(self, env: data.Environment, code_id: int, resources: JsonType) -> Apireturn:
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

        allrefs = [ref for sourcemap in resources.values() for ref in sourcemap.keys()]

        val = self.file_slice.stat_file_internal(allrefs)

        if len(val) != 0:
            raise BadRequest("Not all file references provided are valid", details={"references": val})

        code = await data.Code.get_versions(environment=env.id, version=code_id)
        oldmap: Dict[str, data.Code] = {c.resource: c for c in code}

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

    @handle(methods.get_code, code_id="id", env="tid")
    async def get_code(self, env: data.Environment, code_id: int, resource: str) -> Apireturn:
        code = await data.Code.get_version(environment=env.id, version=code_id, resource=resource)
        if code is None:
            raise NotFound("The version of the code does not exist.")

        sources = {}
        if code.source_refs is not None:
            for code_hash, (file_name, module, req) in code.source_refs.items():
                content = self.file_slice.get_file_internal(code_hash)
                sources[code_hash] = (file_name, module, content.decode(), req)

        return 200, {"version": code_id, "environment": env.id, "resource": resource, "sources": sources}
