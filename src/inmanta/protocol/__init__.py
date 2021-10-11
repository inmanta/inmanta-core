# Copyright 2019 Inmanta
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Contact: code@inmanta.com

"""
The protocol module contains all the code related handle communication between Inmanta components. This documentation
describes its structure. Communication is performed with a central server component. Clients connect to this central
server either with a normal call or with a calls over a session. Session based clients can communicate also receive
calls from the server.

.. uml:: structure.puml
    :align: center


AgentEndpoint and Server, Session and SessionManager implement a reverse channel using a heartbeat mechanism and a
queue of futures for the Server to call methods on the Agent. The Server queues up requests and returns them in a
agent heartbeat. The AgentEndpoint process the returned calls and executes them with RESTBase._execute_call using
the same semantics as the Server for a normal http call.

Generic protocol code structure
-------------------------------

    * common: Classes and helper methods used by various protocol modules. The logic to transform a function to a REST
              call is located in this module. Mainly in :class:`~inmanta.protocol.common.MethodProperties`
    * decorators: Contains the decorator to add API method calls to endpoints and the decorator to register handlers
                  on an endpoint.
    * endpoints: Endpoint base class and multiple types of client endpoints. The server endpoint is defined in
                 inmanta.server.protocol
    * exceptions: Excpetions to signal errors over REST.
    * methods: This module defines the signature of each available API call handled with protocol

    * inmanta.server.protocol contains the session management and the logic required to communicate in the reverse direction
      over a session.

REST specific
------------------
All communication is over REST (including two-way communication). The rest package contains all the code related
to REST transport with Tornado, together with the code in :module:`~inmanta.server.protocol`

"""

# flake8: noqa: F401, F403

from . import methods, methods_v2
from .common import Response, Result, decode_token, encode_token, gzipped_json, json_encode
from .decorators import handle, method, typedmethod
from .endpoints import Client, SessionClient, SessionEndpoint, SyncClient, VersionMatch

__all__ = [
    "Response",
    "Result",
    "decode_token",
    "encode_token",
    "gzipped_json",
    "json_encode",
    "Client",
    "SessionClient",
    "SessionEndpoint",
    "SyncClient",
    "VersionMatch",
    "handle",
    "method",
    "typedmethod",
]
