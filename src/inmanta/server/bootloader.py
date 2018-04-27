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
from tornado.ioloop import IOLoop
from inmanta.server import server
from inmanta.server.protocol import RESTServer
from inmanta.server.agentmanager import AgentManager


class InmantaBootloader(object):

    def __init__(self, agent_no_log=False):
        self.restserver = RESTServer()
        self.agent_no_log = agent_no_log

    def get_server_slice(self):
        io_loop = IOLoop.current()
        return server.Server(io_loop, agent_no_log=self.agent_no_log)

    def get_agent_manager_slice(self):
        return AgentManager(self.restserver)

    def get_server_slices(self):
        return [self.get_server_slice(), self.get_agent_manager_slice()]

    def start(self):
        for mypart in self.get_server_slices():
            self.restserver.add_endpoint(mypart)
        self.restserver.start()

    def stop(self):
        self.restserver.stop()
