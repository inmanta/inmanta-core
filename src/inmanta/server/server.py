"""
    Copyright 2018 Inmanta

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
import json
import logging
import os
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional, Union, cast

from tornado import routing, web

from inmanta import data
from inmanta.const import ApiDocsFormat
from inmanta.data.model import FeatureStatus, SliceStatus, StatusResponse
from inmanta.protocol import exceptions, handle, methods, methods_v2
from inmanta.protocol.common import HTML_CONTENT_WITH_UTF8_CHARSET, ReturnValue, attach_warnings
from inmanta.protocol.openapi.converter import OpenApiConverter
from inmanta.protocol.openapi.model import OpenAPI
from inmanta.server import SLICE_COMPILER, SLICE_DATABASE, SLICE_SERVER, SLICE_TRANSPORT
from inmanta.server import config as opt
from inmanta.server import protocol
from inmanta.types import Apireturn, JsonType, Warnings

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inmanta.server.services.compilerservice import CompilerService

DBLIMIT = 100000


class Server(protocol.ServerSlice):
    """
    The central Inmanta server that communicates with clients and agents and persists configuration
    information
    """

    _server_storage: Dict[str, str]
    compiler: "CompilerService"
    _server: protocol.Server

    def __init__(self) -> None:
        super().__init__(name=SLICE_SERVER)
        LOGGER.info("Starting server endpoint")

    def get_dependencies(self) -> List[str]:
        return [SLICE_DATABASE, SLICE_COMPILER]

    def get_depended_by(self) -> List[str]:
        return [SLICE_TRANSPORT]

    async def prestart(self, server: protocol.Server) -> None:
        self._server = server
        self._server_storage: Dict[str, str] = self.check_storage()
        self.compiler: "CompilerService" = cast("CompilerService", server.get_slice(SLICE_COMPILER))
        self._handlers.append(routing.Rule(routing.PathMatches(r"/dashboard"), web.RedirectHandler, dict(url=r"/console")))
        self._handlers.append(
            routing.Rule(routing.PathMatches(r"/dashboard/(.*)"), web.RedirectHandler, dict(url=r"/console/{0}"))
        )

    def check_storage(self) -> Dict[str, str]:
        """
        Check if the server storage is configured and ready to use.
        """

        def _ensure_directory_exist(directory: str, *subdirs: str) -> str:
            directory = os.path.join(directory, *subdirs)
            if not os.path.exists(directory):
                os.mkdir(directory)
            return directory

        state_dir = opt.state_dir.get()
        server_state_dir = os.path.join(state_dir, "server")
        dir_map = {"server": _ensure_directory_exist(state_dir, "server")}
        dir_map["files"] = _ensure_directory_exist(server_state_dir, "files")
        dir_map["environments"] = _ensure_directory_exist(server_state_dir, "environments")
        dir_map["agents"] = _ensure_directory_exist(server_state_dir, "agents")
        dir_map["logs"] = _ensure_directory_exist(opt.log_dir.get())
        return dir_map

    @handle(methods.notify_change_get, env="id")
    async def notify_change_get(self, env: data.Environment, update: bool) -> Apireturn:
        result = await self.notify_change(env, update, {})
        return result

    @handle(methods.notify_change, env="id")
    async def notify_change(self, env: data.Environment, update: bool, metadata: JsonType) -> Apireturn:
        LOGGER.info("Received change notification for environment %s", env.id)
        if "type" not in metadata:
            metadata["type"] = "api"

        if "message" not in metadata:
            metadata["message"] = "Recompile trigger through API call"

        warnings = await self._async_recompile(env, update, metadata=metadata)

        return attach_warnings(200, None, warnings)

    async def _async_recompile(self, env: data.Environment, update_repo: bool, metadata: JsonType = {}) -> Warnings:
        """
        Recompile an environment in a different thread and taking wait time into account.
        """
        _, warnings = await self.compiler.request_recompile(
            env=env, force_update=update_repo, do_export=True, remote_id=uuid.uuid4(), metadata=metadata
        )
        return warnings

    @handle(methods.get_server_status)
    async def get_server_status(self) -> StatusResponse:
        product_metadata = self.feature_manager.get_product_metadata()
        if product_metadata.version is None:
            raise exceptions.ServerError(
                "Could not find version number for the inmanta compiler."
                "Is inmanta installed? Use setuptools install or setuptools dev to install."
            )

        slices = []
        for slice_name, slice in self._server.get_slices().items():
            try:
                slices.append(SliceStatus(name=slice_name, status=await slice.get_status()))
            except Exception:
                LOGGER.error(
                    f"The following error occured while trying to determine the status of slice {slice_name}",
                    exc_info=True,
                )

        response = StatusResponse(
            product=product_metadata.product,
            edition=product_metadata.edition,
            version=product_metadata.version,
            license=product_metadata.license,
            extensions=self.get_extension_statuses(list(self._server.get_slices().values())),
            slices=slices,
            features=[
                FeatureStatus(slice=feature.slice, name=feature.name, value=self.feature_manager.get_value(feature))
                for feature in self.feature_manager.get_features()
            ],
        )

        return response

    @handle(methods_v2.get_api_docs)
    async def get_api_docs(self, format: Optional[ApiDocsFormat] = ApiDocsFormat.swagger) -> ReturnValue[Union[OpenAPI, str]]:
        url_map = self._server._transport.get_global_url_map(self._server.get_slices().values())
        feature_manager = self.feature_manager
        openapi = OpenApiConverter(url_map, feature_manager)
        # Get rid of none values with custom json encoder
        openapi_json_str = openapi.generate_openapi_json()
        if format == ApiDocsFormat.openapi:
            openapi_dict = json.loads(openapi_json_str)
            return ReturnValue(response=openapi_dict)

        swagger_html = openapi.get_swagger_html(openapi_json_str)
        return ReturnValue(content_type=HTML_CONTENT_WITH_UTF8_CHARSET, response=swagger_html)
