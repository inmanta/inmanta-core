"""
    Copyright 2017 Inmanta

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
import re
import urllib
import logging

from . import local, remote
from inmanta.agent.cache import AgentCache


LOGGER = logging.getLogger(__name__)


def parse_agent_uri(uri: str) -> (str, dict):
    """
        Parse an agent uri and return the settings

        :attr uri: The uri to parse
        :return: (scheme, config)
    """
    parts = urllib.parse.urlparse(uri)
    config = {}
    scheme = "local"

    if parts.query != "":
        items = urllib.parse.parse_qs(parts.query)
        for key, values in items.items():
            config[key] = values[0]

    if parts.scheme != "":
        scheme = parts.scheme

    if parts.netloc != "":
        match = re.search(r"^(?:(?P<user>[^\s@]+)@)?(?P<host>[^\s:]+)(?::(?P<port>[\d]+))?", parts.netloc)
        if match is None:
            raise ValueError()
        config.update(match.groupdict())

    if parts.path != "" and parts.scheme == "" and parts.netloc == "":
        if parts.path == "localhost":
            scheme = "local"
        else:
            scheme = "ssh"
            config.update({"host": parts.path, "port": None, "user": None})

    return scheme, config


def _get_io_class(scheme) -> local.IOBase:
    """
        Get an IO instance.
    """
    if scheme == "local":
        return local.LocalIO

    elif scheme == "ssh":
        return remote.SshIO


def _get_io_instance(uri):
    scheme, config = parse_agent_uri(uri)
    io_class = _get_io_class(scheme)
    LOGGER.debug("Using io class %s for uri %s (%s, %s)", io_class, uri, scheme, config)
    io = io_class(uri, config)
    return io


def get_io(cache: AgentCache, uri: str, version: int):
    """
        Get an IO instance for the given uri and version
    """
    if cache is None:
        io = _get_io_instance(uri)
    else:
        io = cache.get_or_else(uri, lambda version: _get_io_instance(uri), call_on_delete=lambda x: x.close(), version=version)
    return io
