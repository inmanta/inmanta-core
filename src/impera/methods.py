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
    def modify_project(self, id, name):
        """
            Modify the given project
        """

    @protocol(operation="DELETE", id=True)
    def delete_project(self, id):
        """
            Delete the given project and all related data
        """

    @protocol(operation="GET", index=True)
    def list_projects(self):
        """
            Create a list of projects
        """

    @protocol(operation="GET", id=True)
    def get_project(self, id):
        """
            Get a project and a list of the ids of all environments
        """


class Environment(Method):
    """
        Method for working with environments
    """
    __method_name__ = "environment"

    @protocol(operation="PUT")
    def create_environment(self, project_id, name, repository=None, branch=None):
        """
            Create a new environment

            :param project_id The id of the project this environment belongs to
            :param name The name of the environment
            :param repository The url (in git form) of the repository
            :param branch The name of the branch in the repository
        """

    @protocol(operation="POST", id=True)
    def modify_environment(self, id, name, repository=None, branch=None):
        """
            Modify the given environment

            :param id The id of the project this environment belongs to
            :param name The name of the environment
            :param repository The url (in git form) of the repository
            :param branch The name of the branch in the repository
        """

    @protocol(operation="DELETE", id=True)
    def delete_environment(self, id):
        """
            Delete the given environment and all related data
        """

    @protocol(operation="GET", index=True)
    def list_environments(self):
        """
            Create a list of environments
        """

    @protocol(operation="GET", id=True)
    def get_environment(self, id):
        """
            Get an environment and all versions associated
        """


class HeartBeatMethod(Method):
    """
        Send a heartbeat to indicate that an agent is alive
    """
    __method_name__ = "heartbeat"

    @protocol(reply=False)
    def heartbeat(self, endpoint_names, nodename, role, interval, environment):
        """
            Broadcast a heart beat to everyone

            :param node The name of the node from which the heart beat comes
            :param endpoint_names The names of the endpoints on this node
            :param role The role of the compnent sending the heart beat
            :param interval The expected interval between heart beats
        """
        if role not in ROLES:
            raise Exception("Invalid agent role (%s) should be %s" % (role, ", ".join(ROLES)))


class FileMethod(Method):
    """
        Upload, retrieve and check for file. A file is identified by a hash of its content.
    """
    __method_name__ = "file"

    @protocol(operation="PUT", id=True, data_type="blob")
    def upload_file(self, id, content):
        """
            Upload a new file

            :param id The id of the file
            :param content The content of the file
        """

    @protocol(operation="HEAD", id=True)
    def stat_file(self, id):
        """
            Does the file exist

            :param id The id of the file to check
        """

    @protocol(operation="GET", id=True, data_type="blob")
    def get_file(self, id):
        """
            Retrieve a file

            :param id The id of the file to retrieve
        """

    @protocol()
    def stat_files(self, files):
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
    def get_resource(self, tid, id, logs=False):
        """
            Return a resource with the given id.

            :param tid The id of the environment this resource belongs to
            :param id Get the resource with the given id
            :param logs Include the logs in the response
        """

    @protocol(operation="GET", mt=True, index=True)
    def get_resources_for_agent(self, tid, agent):
        """
            Return the most recent state for the resources associated with agent

            :param tid The id of the environment this resource belongs to
            :param agent The agent
        """

    @protocol(operation="HEAD", mt=True, id=True, destination="agent")
    def get_resource_state(self, tid, id):
        """
            Get the status of the resource

            :param tid The id of the environment this resource belongs to
            :param id Get the status of the resource with the given id from the agent
        """

    @protocol(operation="POST", mt=True, id=True)
    def resource_updated(self, tid, id, level, action, message, extra_data):
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
    def list_versions(self, tid):
        """
            Returns a list of all available versions

            :param tid The id of the environment
        """

    @protocol(operation="GET", id=True, mt=True)
    def get_version(self, tid, id):
        """
            Get a particular version and a list of all resources in this version

            :param tid The id of the environment
            :param id The id of the version to retrieve
        """

    @protocol(operation="PUT", mt=True)
    def put_version(self, tid, version, resources, unknowns=None):
        """
            Store a new version of the configuration model

            :param tid The id of the environment
            :param version The version of the configuration model
            :param resources A list of all resources in the configuration model (deployable)
            :param unknowns A list of unknown parameters that caused the model to be incomplete
        """

    @protocol(operation="POST", mt=True, index=True)
    def release_version(self, tid, id, dryrun, push):
        """
            Release version of the configuration model for deployment.

            :param tid The id of the environment
            :param id The version of the CM to deploy
            :param dryrun Should this be a dry run
            :param push Notify all agents to deploy the version
        """


class NotifyMethod(Method):
    """
        Method to notify the server of changes in the configuration model source code
    """
    __method_name__ = "notify"

    @protocol(operation="GET", id=True)
    def notify_change(self, id):
        """
            Notify the server that the repository of the environment with the given id, has changed.

            :param id The id of the environment
        """


class ParameterMethod(Method):
    """
        Get and set parameters on the server
    """
    __method_name__ = "parameter"

    @protocol(operation="GET", mt=True, id=True)
    def get_param(self, tid, id, resource_id=None):
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
    def set_param(self, tid, id, source, value, resource_id=None):
        """
            Set a parameter on the server

            :param tid The id of the environment
            :param id The name of the parameter
            :param resource_id Optionally, scope the parameter to resource (fact)
            :param source The source of the parameter, this can be the user, agent, plugin, compiler, ...
            :param value The value of the parameter
        """

    @protocol(operation="GET", index=True, mt=True)
    def list_params(self, tid):
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
    def list_agents(self, environment=None):
        """
            Return a list of all nodes and the agents for these nodes

            :param environment An optional environment. If set, only the agents that belong to this environment are returned
            :return A list of nodes
        """

    @protocol(operation="GET", id=True, mt=True)
    def get_agent(self, tid, id):
        """
            Return the node and the agents on this node for the given id

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
    def upload_code(self, tid, id, sources, requires):
        """
            Upload the supporting code to the server

            :param tid The environment the code belongs to
            :param id The id (version) of the configuration model
            :param sources The source files that contain handlers and impera plug-ins
            :param requires The requires (dependencies) for the source code (installed with pip
        """

    @protocol(operation="GET", id=True, mt=True)
    def get_code(self, tid, id):
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
    def diff(self, a, b):
        """
            Returns the diff of the files with the two given ids
        """
