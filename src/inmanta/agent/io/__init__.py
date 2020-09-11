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
import logging
import re
import typing
import urllib
from typing import Dict, Optional

from inmanta.agent.cache import AgentCache

from . import local, remote

if typing.TYPE_CHECKING:
    from inmanta.agent.io.local import IOBase


LOGGER = logging.getLogger(__name__)


def parse_agent_uri(uri: str) -> typing.Tuple[str, Dict[str, Optional[str]]]:
    """
    Parse an agent uri and return the settings

    :attr uri: The uri to parse
    :return: (scheme, config)
    """
    parts = urllib.parse.urlparse(uri)
    config: Dict[str, Optional[str]] = {}
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


def _get_io_class(scheme: str) -> typing.Type[local.IOBase]:
    """
    Get an IO instance.
    """
    if scheme == "local":
        return local.LocalIO

    elif scheme == "ssh":
        return remote.SshIO

    raise Exception("%s scheme is not supported" % scheme)


def _get_io_instance(uri: str) -> "IOBase":
    scheme, config = parse_agent_uri(uri)
    io_class = _get_io_class(scheme)
    LOGGER.debug("Using io class %s for uri %s (%s, %s)", io_class, uri, scheme, config)
    io = io_class(uri, config)
    return io


def get_io(cache: AgentCache, uri: str, version: int) -> "IOBase":
    """
    Get an IO instance for the given uri and version
    """
    if cache is None:
        io = _get_io_instance(uri)
    else:
        io = cache.get_or_else(uri, lambda version: _get_io_instance(uri), call_on_delete=lambda x: x.close(), version=version)
    return io
