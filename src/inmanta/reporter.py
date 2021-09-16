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
# Adapted from pyformance

import asyncio
import base64
import logging
import time
from asyncio import Task
from typing import Dict, Optional
from urllib.parse import quote

from pyformance import MetricsRegistry, global_registry
from tornado.httpclient import AsyncHTTPClient, HTTPError, HTTPRequest

LOGGER = logging.getLogger(__name__)

DEFAULT_INFLUX_SERVER = "127.0.0.1"
DEFAULT_INFLUX_PORT = 8086
DEFAULT_INFLUX_DATABASE = "metrics"
DEFAULT_INFLUX_USERNAME = None
DEFAULT_INFLUX_PASSWORD = None
DEFAULT_INFLUX_PROTOCOL = "http"


class AsyncReporter(object):
    def __init__(self, registry: Optional[MetricsRegistry] = None, reporting_interval: int = 30) -> None:
        self.registry = registry or global_registry()
        self.reporting_interval = reporting_interval
        self._stopped = False
        self._handle: Optional[Task[None]] = None

    def start(self) -> bool:
        if self._stopped:
            return False
        self._handle = asyncio.get_event_loop().create_task(self._loop())
        return True

    def stop(self) -> None:
        self._stopped = True
        if self._handle is not None:
            self._handle.cancel()

    async def _loop(self) -> None:
        loop = asyncio.get_event_loop()
        next_loop_time = loop.time()
        while not self._stopped:
            try:
                await self.report_now(self.registry)
            except Exception:
                LOGGER.warning("Could not send metrics report", exc_info=True)
            next_loop_time += self.reporting_interval
            wait = max(0, next_loop_time - loop.time())
            await asyncio.sleep(wait)

    async def report_now(self, registry: Optional[MetricsRegistry] = None, timestamp: Optional[float] = None) -> None:
        raise NotImplementedError(self.report_now)


class InfluxReporter(AsyncReporter):

    """
    InfluxDB reporter using native http api
    (based on https://influxdb.com/docs/v1.1/guides/writing_data.html)
    """

    def __init__(
        self,
        registry: Optional[MetricsRegistry] = None,
        reporting_interval: int = 5,
        database: str = DEFAULT_INFLUX_DATABASE,
        server: str = DEFAULT_INFLUX_SERVER,
        username: Optional[str] = DEFAULT_INFLUX_USERNAME,
        password: Optional[str] = DEFAULT_INFLUX_PASSWORD,
        port: int = DEFAULT_INFLUX_PORT,
        protocol: str = DEFAULT_INFLUX_PROTOCOL,
        autocreate_database: bool = False,
        tags: Dict[str, str] = {},
    ) -> None:
        super(InfluxReporter, self).__init__(registry, reporting_interval)
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        self.protocol = protocol
        self.server = server
        self.autocreate_database = autocreate_database
        self._did_create_database = False
        self.tags = tags
        self.key = "metrics"
        if self.tags:
            tagstring = ",".join("%s=%s" % (key, value) for key, value in self.tags.items())
            self.key = "%s,%s" % (self.key, tagstring)
        self.key = "%s,key=" % self.key

        if not self.server:
            raise Exception("Unable to start the metrics reporter without a server. Empty string given.")

    async def _create_database(self, http_client: AsyncHTTPClient) -> None:
        url = "%s://%s:%s/query" % (self.protocol, self.server, self.port)
        q = quote("CREATE DATABASE %s" % self.database)
        request = HTTPRequest(url + "?q=" + q)
        if self.username and self.password:
            auth = _encode_username(self.username, self.password)
            request.headers.add("Authorization", "Basic %s" % auth.decode("utf-8"))
        try:
            response = await http_client.fetch(request)
            response.rethrow()
            # Only set if we actually were able to get a successful response
            self._did_create_database = True
        except Exception:
            LOGGER.warning("Cannot create database %s to %s", self.database, self.server, exc_info=True)

    async def report_now(self, registry: Optional[MetricsRegistry] = None, timestamp: Optional[float] = None) -> None:
        http_client = AsyncHTTPClient()

        if self.autocreate_database and not self._did_create_database:
            await self._create_database(http_client)
        timestamp = timestamp or int(round(time.time()))
        metrics = (registry or self.registry).dump_metrics()
        post_data = []
        for key, metric_values in metrics.items():
            table = self.key + key
            values = ",".join(
                ["%s=%s" % (k, v if type(v) is not str else '"{}"'.format(v)) for (k, v) in metric_values.items()]
            )
            line = "%s %s %s" % (table, values, timestamp)
            post_data.append(line)
        post_data_all = "\n".join(post_data)
        path = "/write?db=%s&precision=s" % self.database
        url = "%s://%s:%s%s" % (self.protocol, self.server, self.port, path)
        request = HTTPRequest(url, method="POST", body=post_data_all.encode("utf-8"))
        if self.username and self.password:
            auth = _encode_username(self.username, self.password)
            request.headers.add("Authorization", "Basic %s" % auth.decode("utf-8"))
        try:
            response = await http_client.fetch(request)
            response.rethrow()
        except HTTPError:
            LOGGER.warning("Cannot write to %s", self.server, exc_info=True)


def _encode_username(username: str, password: str) -> bytes:
    auth_string = ("%s:%s" % (username, password)).encode()
    return base64.b64encode(auth_string)
