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
import os
from typing import Iterable, List, cast

from inmanta.protocol import handle, methods
from inmanta.protocol.exceptions import BadRequest, NotFound, ServerError
from inmanta.server import SLICE_FILE, SLICE_SERVER, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.server.server import Server
from inmanta.types import Apireturn
from inmanta.util import hash_file

LOGGER = logging.getLogger(__name__)


class FileService(protocol.ServerSlice):
    """Slice serving and managing files"""

    server_slice: Server

    def __init__(self) -> None:
        super(FileService, self).__init__(SLICE_FILE)

    def get_dependencies(self) -> List[str]:
        return [SLICE_SERVER]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        await super().prestart(server)
        self.server_slice = cast(Server, server.get_slice(SLICE_SERVER))

    @handle(methods.upload_file, file_hash="id")
    async def upload_file(self, file_hash: str, content: str) -> Apireturn:
        self.upload_file_internal(file_hash, base64.b64decode(content))
        return 200

    def upload_file_internal(self, file_hash: str, content: bytes) -> None:
        file_name = os.path.join(self.server_slice._server_storage["files"], file_hash)

        if os.path.exists(file_name):
            raise ServerError("A file with this id already exists.")

        if hash_file(content) != file_hash:
            raise BadRequest("The hash does not match the content")

        with open(file_name, "wb+") as fd:
            fd.write(content)

    @handle(methods.stat_file, file_hash="id")
    async def stat_file(self, file_hash: str) -> Apireturn:
        file_name = os.path.join(self.server_slice._server_storage["files"], file_hash)

        if os.path.exists(file_name):
            return 200
        else:
            return 404

    @handle(methods.get_file, file_hash="id")
    async def get_file(self, file_hash: str) -> Apireturn:
        content = self.get_file_internal(file_hash)
        return 200, {"content": base64.b64encode(content).decode("ascii")}

    def get_file_internal(self, file_hash: str) -> bytes:
        """get_file, but on return code 200, content is not encoded"""

        file_name = os.path.join(self.server_slice._server_storage["files"], file_hash)

        if not os.path.exists(file_name):
            raise NotFound()

        with open(file_name, "rb") as fd:
            content = fd.read()
            actualhash = hash_file(content)
            if actualhash == file_hash:
                return content

            # handle corrupt file
            if opt.server_delete_currupt_files.get():
                LOGGER.error(
                    "File corrupt, expected hash %s but found %s at %s, Deleting file", file_hash, actualhash, file_name
                )
                try:
                    os.remove(file_name)
                except OSError:
                    LOGGER.exception("Failed to delete file %s", file_name)
                    raise ServerError(
                        f"File corrupt, expected hash {file_hash} but found {actualhash}. Failed to delete file, please "
                        "contact the server administrator"
                    )

                raise ServerError(
                    f"File corrupt, expected hash {file_hash} but found {actualhash}. "
                    "Deleting file, please re-upload the corrupt file."
                )
            else:
                LOGGER.error("File corrupt, expected hash %s but found %s at %s", file_hash, actualhash, file_name)
                raise ServerError(
                    f"File corrupt, expected hash {file_hash} but found {actualhash}, please contact the server administrator"
                )

    @handle(methods.stat_files)
    async def stat_files(self, files: List[str]) -> Apireturn:
        """
        Return which files in the list exist on the server
        """
        return 200, {"files": self.stat_file_internal(files)}

    def stat_file_internal(self, files: Iterable[str]) -> List[str]:
        """
        Return which files in the list don't exist on the server
        """
        response: List[str] = []
        for f in files:
            f_path = os.path.join(self.server_slice._server_storage["files"], f)
            if not os.path.exists(f_path):
                response.append(f)

        return response

    @handle(methods.diff)
    async def file_diff(self, a: str, b: str) -> Apireturn:
        """
        Diff the two files identified with the two hashes
        """
        if a == "" or a == "0":
            a_lines: List[str] = []
        else:
            a_path = os.path.join(self.server_slice._server_storage["files"], a)
            if not os.path.exists(a_path):
                raise NotFound()

            with open(a_path, "r", encoding="utf-8") as fd:
                a_lines = fd.readlines()

        if b == "" or b == "0":
            b_lines: List[str] = []
        else:
            b_path = os.path.join(self.server_slice._server_storage["files"], b)
            if not os.path.exists(b_path):
                raise NotFound()

            with open(b_path, "r", encoding="utf-8") as fd:
                b_lines = fd.readlines()

        try:
            diff = difflib.unified_diff(a_lines, b_lines, fromfile=a, tofile=b)
        except FileNotFoundError:
            raise NotFound()

        return 200, {"diff": list(diff)}
