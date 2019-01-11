from typing import Optional, Union, Dict, Any, ByteString, Callable, Awaitable

import ssl
import datetime

from tornado import httputil


class HTTPRequest(object):

    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: Union[Dict[str, str], httputil.HTTPHeaders] = None,
        body: Union[bytes, str] = None,
        auth_username: str = None,
        auth_password: str = None,
        auth_mode: str = None,
        connect_timeout: float = None,
        request_timeout: float = None,
        if_modified_since: Union[float, datetime.datetime] = None,
        follow_redirects: bool = None,
        max_redirects: int = None,
        user_agent: str = None,
        use_gzip: bool = None,
        network_interface: str = None,
        streaming_callback: Callable[[bytes], None] = None,
        header_callback: Callable[[str], None] = None,
        prepare_curl_callback: Callable[[Any], None] = None,
        proxy_host: str = None,
        proxy_port: int = None,
        proxy_username: str = None,
        proxy_password: str = None,
        proxy_auth_mode: str = None,
        allow_nonstandard_methods: bool = None,
        validate_cert: bool = None,
        ca_certs: str = None,
        allow_ipv6: bool = None,
        client_key: str = None,
        client_cert: str = None,
        body_producer: Callable[[Callable[[bytes], None]], "Future[None]"] = None,
        expect_100_continue: bool = False,
        decompress_response: bool = None,
        ssl_options: Union[Dict[str, Any], ssl.SSLContext] = None,
    ) -> None: ...


class HTTPResponse(object):
    code: int
    body: str


class AsyncHTTPClient:
    def fetch(
        self,
        request: Union[str, "HTTPRequest"],
        raise_error: bool = True,
        **kwargs: Any
    ) -> Awaitable["HTTPResponse"]: ...
