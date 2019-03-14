# Adapted from pyformance

import asyncio
import time
import base64
import logging

from pyformance import global_registry
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPError
from urllib.parse import quote

LOGGER = logging.getLogger(__name__)

DEFAULT_INFLUX_SERVER = "127.0.0.1"
DEFAULT_INFLUX_PORT = 8086
DEFAULT_INFLUX_DATABASE = "metrics"
DEFAULT_INFLUX_USERNAME = None
DEFAULT_INFLUX_PASSWORD = None
DEFAULT_INFLUX_PROTOCOL = "http"


class AsyncReporter(object):
    def __init__(self, registry=None, reporting_interval=30, clock=None):
        self.registry = registry or global_registry()
        self.reporting_interval = reporting_interval
        self.clock = clock or time
        self._stopped = False
        self._handle = False

    def start(self):
        if self._stopped:
            return False
        self._handle = asyncio.get_event_loop().create_task(self._loop())
        return True

    def stop(self):
        self._stopped = True
        self._handle.cancel()

    async def _loop(self):
        loop = asyncio.get_event_loop()
        next_loop_time = loop.time()
        while not self._stopped:
            try:
                await self.report_now(self.registry)
            except Exception:
                LOGGER.warning("Could not send metrics report", exc_info=True)
            next_loop_time += self.reporting_interval
            wait = max(0, next_loop_time - time.time())
            await asyncio.sleep(wait)

    async def report_now(self, registry=None, timestamp=None):
        raise NotImplementedError(self.report_now)


class InfluxReporter(AsyncReporter):

    """
    InfluxDB reporter using native http api
    (based on https://influxdb.com/docs/v1.1/guides/writing_data.html)
    """

    def __init__(
        self,
        registry=None,
        reporting_interval=5,
        prefix="",
        database=DEFAULT_INFLUX_DATABASE,
        server=DEFAULT_INFLUX_SERVER,
        username=DEFAULT_INFLUX_USERNAME,
        password=DEFAULT_INFLUX_PASSWORD,
        port=DEFAULT_INFLUX_PORT,
        protocol=DEFAULT_INFLUX_PROTOCOL,
        autocreate_database=False,
        clock=None,
        tags={},
    ):
        super(InfluxReporter, self).__init__(registry, reporting_interval, clock)
        self.prefix = prefix
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        self.protocol = protocol
        self.server = server
        self.autocreate_database = autocreate_database
        self._did_create_database = False
        self.tags = {}
        self.key = "metrics"
        if self.tags:
            tagstring = ",".join("%s=%s" % (key, value) for key, value in self.tags)
            self.key = "%s%,s" % (self.key, tagstring)
        self.key = "%s,key=" % self.key

    async def _create_database(self, http_client):
        url = "%s://%s:%s/query" % (self.protocol, self.server, self.port)
        q = quote("CREATE DATABASE %s" % self.database)
        request = HTTPRequest(url + "?q=" + q)
        if self.username:
            auth = _encode_username(self.username, self.password)
            request.headers.add("Authorization", "Basic %s" % auth.decode("utf-8"))
        try:
            response = await http_client.fetch(request)
            response.rethrow()
            # Only set if we actually were able to get a successful response
            self._did_create_database = True
        except HTTPError as err:
            LOGGER.warning(
                "Cannot create database %s to %s: %s",
                self.database,
                self.server,
                err.reason,
            )

    async def report_now(self, registry=None, timestamp=None):
        http_client = AsyncHTTPClient()

        if self.autocreate_database and not self._did_create_database:
            await self._create_database(http_client)
        timestamp = timestamp or int(round(self.clock.time()))
        metrics = (registry or self.registry).dump_metrics()
        post_data = []
        for key, metric_values in metrics.items():
            table = self.key + key
            values = ",".join(
                [
                    "%s=%s" % (k, v if type(v) is not str else '"{}"'.format(v))
                    for (k, v) in metric_values.items()
                ]
            )
            line = "%s %s %s" % (table, values, timestamp)
            post_data.append(line)
        post_data = "\n".join(post_data)
        path = "/write?db=%s&precision=s" % self.database
        url = "%s://%s:%s%s" % (self.protocol, self.server, self.port, path)
        request = HTTPRequest(url, method="POST", body=post_data.encode("utf-8"))
        if self.username:
            auth = _encode_username(self.username, self.password)
            request.headers.add("Authorization", "Basic %s" % auth.decode("utf-8"))
        try:
            response = await http_client.fetch(request)
            response.rethrow()
        except HTTPError:
            LOGGER.warning("Cannot write to %s", self.server, exc_info=1)


def _encode_username(username, password):
    auth_string = ("%s:%s" % (username, password)).encode()
    return base64.b64encode(auth_string)
