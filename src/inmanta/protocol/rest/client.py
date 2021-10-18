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
import re
from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, AnyStr, Dict, List, Optional, Set, Tuple
from urllib.parse import unquote

from tornado.httpclient import AsyncHTTPClient, HTTPError, HTTPRequest, HTTPResponse

from inmanta import config as inmanta_config
from inmanta.protocol import common
from inmanta.protocol.rest import RESTBase

if TYPE_CHECKING:
    from inmanta.protocol.endpoints import Endpoint

LOGGER: logging.Logger = logging.getLogger(__name__)


class RESTClient(RESTBase):
    """ "
    A REST (json body over http) client transport. Only methods that operate on resource can use all
    HTTP verbs. For other methods the POST verb is used.
    """

    def __init__(self, endpoint: "Endpoint", connection_timout: int = 120) -> None:
        super().__init__()
        self.__end_point: "Endpoint" = endpoint
        self.daemon: bool = True
        self.token: Optional[str] = inmanta_config.Config.get(self.id, "token", None)
        self.connection_timout: int = connection_timout
        self.headers: Set[str] = set()
        self.request_timeout: int = inmanta_config.Config.get(self.id, "request_timeout", 120)

    @property
    def endpoint(self) -> "Endpoint":
        return self.__end_point

    @property
    def id(self) -> str:
        """
        Returns a unique id for a transport on an endpoint
        """
        return "%s_rest_transport" % self.__end_point.name

    def match_call(self, url: str, method: str) -> Tuple[Optional[Dict[str, AnyStr]], Optional[common.UrlMethod]]:
        """
        Get the method call for the given url and http method. This method is used for return calls over long poll
        """
        for target in self.endpoint.call_targets:
            url_map = target.get_op_mapping()
            for url_re, handlers in url_map.items():
                if not url_re.endswith("$"):
                    url_re += "$"
                match = re.match(url_re, url)
                if match and method in handlers:
                    return {unquote(k): unquote(v) for k, v in match.groupdict().items()}, handlers[method]

        return None, None

    def _get_client_config(self) -> str:
        """
        Load the configuration for the client
        """
        LOGGER.debug("Getting config in section %s", self.id)

        port: int = inmanta_config.Config.get(self.id, "port", 8888)
        host: str = inmanta_config.Config.get(self.id, "host", "localhost")

        if inmanta_config.Config.getboolean(self.id, "ssl", False):
            protocol = "https"
        else:
            protocol = "http"

        return "%s://%s:%d" % (protocol, host, port)

    async def call(
        self, properties: common.MethodProperties, args: List[object], kwargs: Optional[Dict[str, Any]] = None
    ) -> common.Result:
        if kwargs is None:
            kwargs = {}

        base_request = properties.build_call(args, kwargs)

        url_host = self._get_client_config()
        url = url_host + base_request.url

        headers = base_request.headers
        if self.token is not None:
            headers["Authorization"] = "Bearer " + self.token

        body = base_request.body
        if body is not None:
            zipped, body = common.gzipped_json(body)
            if zipped:
                headers["Content-Encoding"] = "gzip"

        ca_certs = inmanta_config.Config.get(self.id, "ssl_ca_cert_file", None)
        LOGGER.debug("Calling server %s %s", properties.operation, url)

        try:
            request = HTTPRequest(
                url=url,
                method=base_request.method,
                headers=headers,
                body=body,
                connect_timeout=self.connection_timout,
                request_timeout=self.request_timeout,
                ca_certs=ca_certs,
                decompress_response=True,
            )
            client = AsyncHTTPClient()
            response = await client.fetch(request)
        except HTTPError as e:
            if e.response is not None and e.response.body is not None and len(e.response.body) > 0:
                try:
                    result = self._decode(e.response.body)
                except ValueError:
                    result = {}
                return common.Result(code=e.code, result=result)

            return common.Result(code=e.code, result={"message": str(e)})
        except CancelledError:
            raise
        except Exception as e:
            LOGGER.exception("Failed to send request")
            return common.Result(code=500, result={"message": str(e)})

        return self._decode_response(response)

    def _decode_response(self, response: HTTPResponse):
        content_type = response.headers.get(common.CONTENT_TYPE, None)

        if content_type is None or content_type == common.JSON_CONTENT:
            return common.Result(code=response.code, result=self._decode(response.body))
        elif content_type == common.HTML_CONTENT:
            return common.Result(code=response.code, result=response.body.decode(common.HTML_ENCODING))
        elif content_type == common.HTML_CONTENT_WITH_UTF8_CHARSET:
            return common.Result(code=response.code, result=response.body.decode(common.UTF8_ENCODING))
        else:
            # Any other content-type will leave the encoding unchanged
            return common.Result(code=response.code, result=response.body)
