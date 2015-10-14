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

    Contact: bart@impera.io
"""

from functools import wraps
from impera.data import ROLES, ACTIONS, LOGLEVEL
import uuid


def protocol(index=False, id=False, broadcast=False, operation="POST", data_type="message", reply=True, destination="",
             mt=False):
    """
        Decorator to identify a method as a RPC call. The arguments of the decorator are used by each transport to build
        and model the protocol.

        :param index A method that returns a list of resources. The url of this method is only the method/resource name.
        :param id This method requires an id of a resource. The python function should have an id parameter.
        :param reply This method returns data
        :param operation The type of HTTP operation (verb)
        :param data_type The type of data (message or blob) (not used at the moment)
        :param destination If destination is empty only the server should get the message. When destination is *, the server
                           will forward it to all other clients as well.
        :param mt Is this a multi-tenant call? If it is multi-tenant a tenant id is required. This id is transported as an
                  HTTP header. The method that has mt=True, should have an attribute tid
    """
    properties = {
        "index": index,
        "id": id,
        "reply": reply,
        "broadcast": broadcast,
        "operation": operation,
        "data_type": data_type,
        "destination": destination,
        "mt": mt,
    }

    def wrapper(func):
        """
            Return the wrapper method so it can be used to do RPC calls. Additionally it adds the protocol properties of the
            decorator to the method.
        """
        @wraps(func)
        def wrapped_method(self, *args, **kwargs):
            """
                This wrapper will first call the original method to validate the arguments passed and possible custom
                validation logic in the method itself.
            """
            func(self, *args, **kwargs)

            return self._call(args=args, kwargs=kwargs, protocol_properties=properties)

        properties["method"] = func
        wrapped_method.__protocol_properties__ = properties
        return wrapped_method

    return wrapper


class Method(object):
    """
        A decorator to add methods to the protocol.
    """
    __method_name__ = None


class Project(Method):
    """
        Method for working with projects
    """
    __method_name__ = "project"

    @protocol(operation="PUT")
    def create_project(self, name):
        """
            Create a new project
        """

    @protocol(operation="POST", id=True)
    def modify_project(self, id: uuid.UUID, name: str):
        """
            Modify the given project
        """

    @protocol(operation="DELETE", id=True)
    def delete_project(self, id: uuid.UUID):
        """
            Delete the given project and all related data
        """

    @protocol(operation="GET", index=True)
    def list_projects(self):
        """
            Create a list of projects
        """

    @protocol(operation="GET", id=True)
    def get_project(self, id: uuid.UUID):
        """
            Get a project and a list of the ids of all environments
        """


class Environment(Method):
    """
        Method for working with environments
    """
    __method_name__ = "environment"

    @protocol(operation="PUT")
    def create_environment(self, project_id: uuid.UUID, name: str, repository: str=None, branch: str=None):
        """
            Create a new environment

            :param project_id The id of the project this environment belongs to
            :param name The name of the environment
            :param repository The url (in git form) of the repository
            :param branch The name of the branch in the repository
        """

    @protocol(operation="POST", id=True)
    def modify_environment(self, id: uuid.UUID, name: str, repository: str=None, branch: str=None):
        """
            Modify the given environment

            :param id The id of the environment
            :param name The name of the environment
            :param repository The url (in git form) of the repository
            :param branch The name of the branch in the repository
        """

    @protocol(operation="DELETE", id=True)
    def delete_environment(self, id: uuid.UUID):
        """
            Delete the given environment and all related data
        """

    @protocol(operation="GET", index=True)
    def list_environments(self):
        """
            Create a list of environments
        """

    @protocol(operation="GET", id=True)
    def get_environment(self, id: uuid.UUID, versions: int=None, resources: int=None):
        """
            Get an environment and all versions associated

            :param id The id of the environment to return
            :param versions Include this many available version for this environment.
            :param resources Include this many available resources for this environment.
        """


class HeartBeatMethod(Method):
    """
        Send a heartbeat to indicate that an agent is alive
    """
    __method_name__ = "heartbeat"

    @protocol(reply=False)
    def heartbeat(self, endpoint_names: list, nodename: str, role: str, interval: int, environment: uuid.UUID):
        """
            Broadcast a heart beat to everyone

            :param endpoint_names The names of the endpoints on this node
            :param nodename The name of the node from which the heart beat comes
            :param role The role of the compnent sending the heart beat
            :param interval The expected interval between heart beats
            :param environment The environment this agent belongs to
        """
        if role not in ROLES:
            raise Exception("Invalid agent role (%s) should be %s" % (role, ", ".join(ROLES)))


class FileMethod(Method):
    """
        Upload, retrieve and check for file. A file is identified by a hash of its content.
    """
    __method_name__ = "file"

    @protocol(operation="PUT", id=True, data_type="blob")
    def upload_file(self, id: str, content: str):
        """
            Upload a new file

            :param id The id of the file
            :param content The content of the file
        """

    @protocol(operation="HEAD", id=True)
    def stat_file(self, id: str):
        """
            Does the file exist

            :param id The id of the file to check
        """

    @protocol(operation="GET", id=True, data_type="blob")
    def get_file(self, id: str):
        """
            Retrieve a file

            :param id The id of the file to retrieve
        """

    @protocol()
    def stat_files(self, files: list):
        """
            Check which files exist in the given list

            :param files A list of file id to check
            :return A list of files that do not exist.
        """


class ResourceMethod(Method):
    """
        Manage resources on the server
    """
    __method_name__ = "resource"

    @protocol(operation="GET", id=True, mt=True)
    def get_resource(self, tid: uuid.UUID, id: str, logs: bool=None):
        """
            Return a resource with the given id.

            :param tid The id of the environment this resource belongs to
            :param id Get the resource with the given id
            :param logs Include the logs in the response
        """

    @protocol(operation="GET", mt=True, index=True)
    def get_resources_for_agent(self, tid: uuid.UUID, agent: str, version: int=None):
        """
            Return the most recent state for the resources associated with agent, or the version requested

            :param tid The id of the environment this resource belongs to
            :param agent The agent
            :param version The version to retrieve. If none, the latest available version is returned. With a specific version
                           that version is returned, even if it has not been released yet.
        """

    @protocol(operation="HEAD", mt=True, id=True, destination="agent")
    def get_resource_state(self, tid: uuid.UUID, id: str):
        """
            Get the status of the resource

            :param tid The id of the environment this resource belongs to
            :param id Get the status of the resource with the given id from the agent
        """

    @protocol(operation="POST", mt=True, id=True)
    def resource_updated(self, tid: uuid.UUID, id: str, level: str, action: str, message: str, extra_data: dict):
        """
            Send a resource update to the server

            :param tid The id of the environment this resource belongs to
            :param id Get the status of the resource with the given id from the agent
            :param level The loglevel of the update
            :param action The action performed
            :param message The log message
            :param extra_data A map with additional data
        """
        if level not in LOGLEVEL:
            raise Exception("Invalid resource update level (%s) should be %s" % (level, ", ".join(LOGLEVEL)))

        if action not in ACTIONS:
            raise Exception("Invalid resource update action (%s) should be %s" % (action, ", ".join(ACTIONS)))


class CMVersionMethod(Method):
    """
        Manage configuration model versions
    """
    __method_name__ = "cmversion"

    @protocol(index=True, operation="GET", mt=True)
    def list_versions(self, tid: uuid.UUID, start: int=None, limit: int=None):
        """
            Returns a list of all available versions

            :param tid The id of the environment
            :param start Optional, parameter to control the amount of results that are returned. 0 is the latest version.
            :param limit Optional, parameter to control the amount of results returned.
        """

    @protocol(operation="GET", id=True, mt=True)
    def get_version(self, tid: uuid.UUID, id: int, include_logs: bool=None, log_filter: str=None, limit: int=None):
        """
            Get a particular version and a list of all resources in this version

            :param tid The id of the environment
            :param id The id of the version to retrieve
            :param include_logs If true, a log of all operations on all resources is included
            :param log_filter Filter log to only include actions of the specified type
            :param limit The maximal number of actions to return per resource (starting from the latest)
        """

    @protocol(operation="DELETE", id=True, mt=True)
    def delete_version(self, tid: uuid.UUID, id: int):
        """
            Delete a particular version and resources

            :param tid The id of the environment
            :param id The id of the version to retrieve
        """

    @protocol(operation="PUT", mt=True)
    def put_version(self, tid: uuid.UUID, version: int, resources: list, unknowns: list=None):
        """
            Store a new version of the configuration model

            :param tid The id of the environment
            :param version The version of the configuration model
            :param resources A list of all resources in the configuration model (deployable)
            :param unknowns A list of unknown parameters that caused the model to be incomplete
        """

    @protocol(operation="POST", mt=True, id=True)
    def release_version(self, tid: uuid.UUID, id: int, push: bool):
        """
            Release version of the configuration model for deployment.

            :param tid The id of the environment
            :param id The version of the CM to deploy
            :param push Notify all agents to deploy the version
        """


class DryRunMethod(Method):
    """
        Method for requesting and quering a dryrun
    """
    __method_name__ = "dryrun"

    @protocol(operation="POST", mt=True, id=True)
    def dryrun_request(self, tid: uuid.UUID, id: int):
        """
            Do a dryrun

            :param tid The id of the environment
            :param id The version of the CM to deploy
        """

    @protocol(operation="GET", mt=True)
    def dryrun_list(self, tid: uuid.UUID, version: int=None):
        """
            Create a list of dry runs

            :param tid The id of the environment
            :param version Only for this version
        """

    @protocol(operation="GET", mt=True, id=True)
    def dryrun_report(self, tid: uuid.UUID, id: int):
        """
            Create a dryrun report

            :param tid The id of the environment
            :param id The version dryrun to report
        """

    @protocol(operation="PUT", mt=True, id=True)
    def dryrun_update(self, tid: uuid.UUID, id: int, resource: str, changes: dict, log_msg: str=None):
        """
            Store dryrun results at the server

            :param tid The id of the environment
            :param id The version dryrun to report
            :param resource The id of the resource
            :param changes The required changes
            :param log_msg An optional log message (for example to report an error)
        """


class NotifyMethod(Method):
    """
        Method to notify the server of changes in the configuration model source code
    """
    __method_name__ = "notify"

    @protocol(operation="GET", id=True)
    def notify_change(self, id: uuid.UUID):
        """
            Notify the server that the repository of the environment with the given id, has changed.

            :param id The id of the environment
        """

    @protocol(operation="HEAD", id=True)
    def is_compiling(self, id: uuid.UUID):
        """
           Is a compiler running for the given environment
        """


class ParameterMethod(Method):
    """
        Get and set parameters on the server
    """
    __method_name__ = "parameter"

    @protocol(operation="GET", mt=True, id=True)
    def get_param(self, tid: uuid.UUID, id: str, resource_id: str=None):
        """
            Get a parameter from the server.

            :param tid The id of the environment
            :param id The name of the parameter
            :param resource_id Optionally, scope the parameter to resource (fact)
            :return Returns the following status codes:
                    200: The parameter content is returned
                    404: The parameter is not found and unable to find it because its resource is not known to the server
                    410: The parameter has expired
                    503: The parameter is not found but its value is requested from an agent
        """

    @protocol(operation="POST", mt=True, id=True)
    def set_param(self, tid: uuid.UUID, id: str, source: str, value: str, resource_id: str=None):
        """
            Set a parameter on the server

            :param tid The id of the environment
            :param id The name of the parameter
            :param resource_id Optionally, scope the parameter to resource (fact)
            :param source The source of the parameter, this can be the user, agent, plugin, compiler, ...
            :param value The value of the parameter
        """

    @protocol(operation="GET", index=True, mt=True)
    def list_params(self, tid: uuid.UUID):
        """
            List the parameter of this environment

            :param tid The id of the environment
        """


class NodeMethod(Method):
    """
        Get a list of all agents
    """
    __method_name__ = "agent"

    @protocol(operation="GET", index=True)
    def list_agents(self, environment: uuid.UUID=None):
        """
            Return a list of all nodes and the agents for these nodes

            :param environment An optional environment. If set, only the agents that belong to this environment are returned
            :return A list of nodes
        """

    @protocol(operation="GET", id=True, mt=True)
    def get_agent(self, tid: uuid.UUID, id: str):
        """
            Return the node and the agents on this node for the given id

            :param tid The environment this agent is defined in
            :param id The name of the agent
            :return The requested node
        """

    @protocol(operation="POST", id=True, mt=True)
    def trigger_agent(self, tid: uuid.UUID, id: str):
        """
            Request an agent to reload resources

            :param tid The environment this agent is defined in
            :param id The name of the agent
            :return The requested node
        """


class CodeMethod(Method):
    """
        Upload code to the server
    """
    __method_name__ = "code"

    @protocol(operation="PUT", id=True, mt=True)
    def upload_code(self, tid: uuid.UUID, id: int, sources: str, requires: list):
        """
            Upload the supporting code to the server

            :param tid The environment the code belongs to
            :param id The id (version) of the configuration model
            :param sources The source files that contain handlers and impera plug-ins
            :param requires The requires (dependencies) for the source code (installed with pip)
        """

    @protocol(operation="GET", id=True, mt=True)
    def get_code(self, tid: uuid.UUID, id: int):
        """
            Get the code for a given version of the configuration model

            :param tid The environment the code belongs to
            :param id The id (version) of the configuration model
        """


class FileDiff(Method):
    """
        Generate download the diff of two hashes
    """
    __method_name__ = "filediff"

    @protocol()
    def diff(self, a: str, b: str):
        """
            Returns the diff of the files with the two given ids
        """


class CompileReport(Method):
    """
        Get a list of compile reports
    """
    __method_name__ = "compilereport"

    @protocol(operation="GET", index=True)
    def get_reports(self, environment: uuid.UUID=None, start: str=None, end: str=None, limit: int=None):
        """
            Return compile reports newer then start

            :param environment The id of the environment to get a report from
            :param start Reports after start
            :param end Reports before end
            :param limit Maximum number of results
        """
