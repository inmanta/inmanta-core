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
The protocol module contains all the code related to communication between Inmanta components. This documentation
describes its structure. Communication is performed with a central server component. Clients connect to this central
server either with a normal REST call or over a websocket session. Websocket-based clients can also receive
calls from the server.

.. uml:: structure.puml
    :align: center


AgentEndpoint and Server use websocket sessions for bidirectional communication. The server can call methods on
the agent by sending messages over the websocket connection. The AgentEndpoint processes incoming calls and executes
them with RESTBase._execute_call using the same semantics as the Server for a normal http call.

Generic protocol code structure
-------------------------------

    * common: Classes and helper methods used by various protocol modules. The logic to transform a function to a REST
              call is located in this module. Mainly in :class:`~inmanta.protocol.common.MethodProperties`
    * decorators: Contains the decorator to add API method calls to endpoints and the decorator to register handlers
                  on an endpoint.
    * endpoints: Endpoint base class and multiple types of client endpoints. The server endpoint is defined in
                 inmanta.server.protocol
    * exceptions: Exceptions to signal errors over REST.
    * methods: This module defines the signature of each available API call handled with protocol
    * websocket: Contains the websocket session management and bidirectional communication logic.

    * inmanta.server.protocol contains the server-side session management.

REST and WebSocket
------------------
Client-to-server communication uses REST. Bidirectional communication (server-to-agent) uses websockets.
The rest package contains all the code related to REST transport with Tornado, together with the code in
:module:`~inmanta.server.protocol`

"""

# flake8: noqa: F401, F403

from inmanta.protocol import methods, methods_v2
from inmanta.protocol.auth.auth import decode_token, encode_token
from inmanta.protocol.common import Response, Result, gzipped_json, json_encode
from inmanta.protocol.decorators import handle, method, typedmethod
from inmanta.protocol.endpoints import Client, SyncClient, TypedClient, VersionMatch
from inmanta.protocol.websocket import Session, SessionEndpoint, SessionListener

__all__ = [
    "Response",
    "Result",
    "gzipped_json",
    "json_encode",
    "Client",
    "SessionEndpoint",
    "SyncClient",
    "VersionMatch",
    "handle",
    "method",
    "typedmethod",
    "decode_token",
    "encode_token",
    "TypedClient",
    "Session",
    "SessionListener",
]
