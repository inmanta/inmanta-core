"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contect: bart@impera.io
"""


class Method(object):
    """
        A decorator to add methods to the protocol
    """
    __method_name__ = None
    __reply__ = False
    __reply_name__ = None
    __resource__ = False
    __data_type__ = "message"
    __index__ = False


class HeartBeatMethod(Method):
    """
        Send a heartbeat to indicate that an agent is alive
    """
    __method_name__ = "heartbeat"


class PingMethod(Method):
    """
        Send a ping
    """
    __method_name__ = "ping"
    __reply__ = True


class FileMethod(Method):
    """
        Upload, retrieve and check for file. A file is identified by a hash of its content.
        The data is a send as a blob and can only be retrieved with rpc semantics
    """
    __method_name__ = "file"
    __data_type__ = "blob"
    __resource__ = True
    __reply__ = True
    __index__ = False


class StatMethod(Method):
    """
        Check a list of files for their existence on the server
    """
    __method_name__ = "stat"
    __reply__ = True


class ResourceMethod(Method):
    """
        Manage resources on the server
    """
    __method_name__ = "resource"
    __resource__ = True
    __reply__ = True


class VersionMethod(Method):
    """
        Manage resource versions
    """
    __method_name__ = "version"
    __resource__ = True
    __reply__ = True
    __index__ = True


class GetFact(Method):
    """
        Get a fact about a resource
    """
    __method_name__ = "fact"
    __reply__ = True


class RetrieveFacts(Method):
    """
        Retrieve all facts about a resource
    """
    __method_name__ = "facts"
    __reply__ = True


class NodeMethod(Method):
    """
        Get a list of all agents
    """
    __method_name__ = "node"
    __reply__ = True
    __resource__ = True
    __index__ = True


class GetQueue(Method):
    """
        Get the current queue of the agent
    """
    __method_name__ = "queue"
    __reply__ = True


class GetAgentInfo(Method):
    """
        Get information/stats about an agent
    """
    __method_name__ = "info"
    __reply__ = True


class DumpAgent(Method):
    """
        Dump information of the agent
    """
    __method_name__ = "dump"


class CodeMethod(Method):
    """
        Upload code to the server
    """
    __method_name__ = "code"
    __reply__ = True
    __resource__ = True


class CodeDeploy(Method):
    """
        Deploy code to the agents
    """
    __method_name__ = "code_deploy"


class DeployVersion(Method):
    """
        Deploy a specific version on all agents
    """
    __method_name__ = "deploy_version"


class StatusMethod(Method):
    """
        Request the current state of a particular resource
    """
    __method_name__ = "status"
    __reply__ = True
    __resource__ = True


class ResourceUpdate(Method):
    """
        Send a resource update to a(n) agent(s)
    """
    __method_name__ = "resource_update"


class ResourceUpdated(Method):
    """
        Broadcast that a resource is updated
    """
    __method_name__ = "resource_updated"


class FileDiff(Method):
    """
        Generate download the diff of two hashes
    """
    __method_name__ = "filediff"
    __reply__ = True
