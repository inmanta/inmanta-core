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
from inmanta.server import server
from inmanta.server.protocol import Server, ServerSlice
from inmanta.server.agentmanager import AgentManager
from tornado import gen

from typing import List, Generator, Any


class InmantaBootloader(object):
    def __init__(self, agent_no_log: bool = False) -> None:
        self.restserver = Server()
        self.agent_no_log = agent_no_log

    def get_server_slice(self) -> server.Server:
        return server.Server(agent_no_log=self.agent_no_log)

    def get_agent_manager_slice(self) -> AgentManager:
        return AgentManager(self.restserver)

    def get_server_slices(self) -> List[ServerSlice]:
        return [self.get_server_slice(), self.get_agent_manager_slice()]

    @gen.coroutine
    def start(self) -> Generator[Any, None, None]:
        for mypart in self.get_server_slices():
            self.restserver.add_slice(mypart)
        yield self.restserver.start()

    @gen.coroutine
    def stop(self) -> Generator[Any, None, None]:
        yield self.restserver.stop()
