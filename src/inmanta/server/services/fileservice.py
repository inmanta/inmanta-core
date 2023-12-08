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
import base64
import difflib
import logging
from collections.abc import Iterable
from typing import Optional

from asyncpg.exceptions import UniqueViolationError

from inmanta.data import File
from inmanta.protocol import handle, methods
from inmanta.protocol.exceptions import BadRequest, NotFound, ServerError
from inmanta.server import SLICE_DATABASE, SLICE_FILE, SLICE_TRANSPORT, protocol
from inmanta.server.server import Server
from inmanta.types import Apireturn
from inmanta.util import hash_file

LOGGER = logging.getLogger(__name__)


class FileService(protocol.ServerSlice):
    """Slice serving and managing files"""

    server_slice: Server

    def __init__(self) -> None:
        super().__init__(SLICE_FILE)

    def get_dependencies(self) -> list[str]:
        return [SLICE_DATABASE]

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    @handle(methods.upload_file, file_hash="id")
    async def upload_file(self, file_hash: str, content: str) -> Apireturn:
        await self.upload_file_internal(file_hash, base64.b64decode(content))
        return 200

    async def upload_file_internal(self, file_hash: str, content: bytes) -> None:
        if hash_file(content) != file_hash:
            raise BadRequest("The hash does not match the content")

        try:
            await File(content_hash=file_hash, content=content).insert()
        except UniqueViolationError:
            raise ServerError("A file with this id already exists.")

    @handle(methods.stat_file, file_hash="id")
    async def stat_file(self, file_hash: str) -> Apireturn:
        if await File.has_file_with_hash(file_hash):
            return 200
        else:
            return 404

    @handle(methods.get_file, file_hash="id")
    async def get_file(self, file_hash: str) -> Apireturn:
        content = await self.get_file_internal(file_hash)
        return 200, {"content": base64.b64encode(content).decode("ascii")}

    async def get_file_internal(self, file_hash: str) -> bytes:
        """get_file, but on return code 200, content is not encoded"""
        file: Optional[File] = await File.get_one(content_hash=file_hash)
        if not file:
            raise NotFound()
        return file.content

    @handle(methods.stat_files)
    async def stat_files(self, files: list[str]) -> Apireturn:
        """
        Return which files in the list exist on the server
        """
        return 200, {"files": await self.stat_file_internal(files)}

    async def stat_file_internal(self, files: Iterable[str]) -> list[str]:
        """
        Return which files in the list don't exist on the server
        """
        return list(await File.get_non_existing_files(files))

    @handle(methods.diff)
    async def file_diff(self, file_id_1: str, file_id_2: str) -> Apireturn:
        """
        Diff the two files identified with the two hashes
        """

        async def _get_lines_for_file(content_hash: str) -> list[str]:
            if content_hash == "" or content_hash == "0":
                return []
            else:
                file = await File.get_one(content_hash=content_hash)
                if not file:
                    raise NotFound()

                file_content = file.content.decode(encoding="utf-8")
                # keepends for backwards compatibility with <file_handle>.readlines()
                return file_content.splitlines(keepends=True)

        file_1_lines = await _get_lines_for_file(content_hash=file_id_1)
        file_2_lines = await _get_lines_for_file(content_hash=file_id_2)
        try:
            diff = difflib.unified_diff(file_1_lines, file_2_lines, fromfile=file_id_1, tofile=file_id_2)
        except FileNotFoundError:
            raise NotFound()

        return 200, {"diff": list(diff)}
