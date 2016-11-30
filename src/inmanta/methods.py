"""
    Copyright 2016 Inmanta

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

from functools import wraps
import uuid
import datetime

from inmanta.data import ACTIONS, LOGLEVEL
from tornado import gen


def protocol(index=False, id=False, broadcast=False, operation="POST", data_type="message", reply=True, destination="",
             mt=False, timeout=None, api=None, server_agent=False, agent_server=False, validate_sid=None):
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
        :param timeout nr of seconds before request it terminated
        :param api This is a call from the client to the Server (True if not server_agent and not agent_server)
        :param server_agent This is a call from the Server to the Agent
        :param agent_server This is a call from the Agent to the Server
        :param validate_sid This call requires a valid session, true by default if agent_server and not api
    """
    if api is None:
        api = not server_agent and not agent_server
    if validate_sid is None:
        validate_sid = agent_server and not api

    properties = {
        "index": index,
        "id": id,
        "reply": reply,
        "broadcast": broadcast,
        "operation": operation,
        "data_type": data_type,
        "destination": destination,
        "mt": mt,
        "timeout": timeout,
        "api": api,
        "server_agent": server_agent,
        "agent_server": agent_server,
        "validate_sid": validate_sid
    }

    def wrapper(func):
        """
            Return the wrapper method so it can be used to do RPC calls. Additionally it adds the protocol properties of the
            decorator to the method.
        """
        @wraps(func)
        @gen.coroutine
        def wrapped_method(self, *args, **kwargs):
            """
                This wrapper will first call the original method to validate the arguments passed and possible custom
                validation logic in the method itself.
            """
            func(self, *args, **kwargs)

            result = yield self._call(args=args, kwargs=kwargs, protocol_properties=properties)
            return result

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


class Decommision(Method):
    """
        Decomission an environment
    """
    __method_name__ = "decommission"

    @protocol(operation="POST", id=True)
    def decomission_environment(self, id: uuid.UUID):
        """
            Decommision an environment. This is done by uploading an empty model to the server and let purge_on_delete handle
            removal.
        """

    @protocol(operation="DELETE", id=True)
    def clear_environment(self, id: uuid.UUID):
        """
            Clear all data from this environment
        """


class HeartBeatMethod(Method):
    """
        Send a heartbeat to indicate that an agent is alive
    """
    __method_name__ = "heartbeat"

    @protocol(operation="POST", mt=True, agent_server=True, validate_sid=False)
    def heartbeat(self, sid: uuid.UUID, tid: uuid.UUID, endpoint_names: list, nodename: str):
        """
            Send a heartbeat to the server

            :paran sid The session ID used by this agent at this moment
            :param tid The environment this node and its agents belongs to
            :param endpoint_names The names of the endpoints on this node
            :param nodename The name of the node from which the heart beat comes

            also registered as API method, because it is called with an invalid SID the first time
        """

    @protocol(operation="PUT", agent_server=True)
    def heartbeat_reply(self, sid: uuid.UUID, reply_id: uuid.UUID, data: dict):
        """
            Send a reply back to the server

            :param sid The session ID used by this agent at this moment
            :param reply_id The id data is a reply to
            :param data The data as a response to the reply
        """


class FileMethod(Method):
    """
        Upload, retrieve and check for file. A file is identified by a hash of its content.
    """
    __method_name__ = "file"

    @protocol(operation="PUT", id=True, data_type="blob", api=True, agent_server=True)
    def upload_file(self, id: str, content: str):
        """
            Upload a new file

            :param id The id of the file
            :param content The base64 encoded content of the file
        """

    @protocol(operation="HEAD", id=True, agent_server=True, api=True)
    def stat_file(self, id: str):
        """
            Does the file exist

            :param id The id of the file to check
        """

    @protocol(operation="GET", id=True, data_type="blob", api=True, agent_server=True)
    def get_file(self, id: str):
        """
            Retrieve a file

            :param id The id of the file to retrieve
        """

    @protocol(api=True)
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

    @protocol(operation="GET", id=True, mt=True, agent_server=True, api=True, validate_sid=False)
    def get_resource(self, tid: uuid.UUID, id: str, logs: bool=None, status: bool=None):
        """
            Return a resource with the given id.

            :param tid The id of the environment this resource belongs to
            :param id Get the resource with the given id
            :param logs Include the logs in the response
            :param status return only resou
        """

    @protocol(operation="GET", mt=True, index=True, agent_server=True)
    def get_resources_for_agent(self, tid: uuid.UUID, agent: str, version: int=None):
        """
            Return the most recent state for the resources associated with agent, or the version requested

            :param tid The id of the environment this resource belongs to
            :param agent The agent
            :param version The version to retrieve. If none, the latest available version is returned. With a specific version
                           that version is returned, even if it has not been released yet.
        """

    @protocol(operation="POST", mt=True, id=True, agent_server=True)
    def resource_updated(self, tid: uuid.UUID, id: str, level: str, action: str, message: str, status: str, extra_data: dict):
        """
            Send a resource update to the server

            :param tid The id of the environment this resource belongs to
            :param id Get the status of the resource with the given id from the agent
            :param level The loglevel of the update
            :param action The action performed
            :param message The log message
            :param status The current status of the resource (if known)
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
    def put_version(self, tid: uuid.UUID, version: int, resources: list, unknowns: list=None, version_info: dict=None):
        """
            Store a new version of the configuration model

            :param tid The id of the environment
            :param version The version of the configuration model
            :param resources A list of all resources in the configuration model (deployable)
            :param unknowns A list of unknown parameters that caused the model to be incomplete
            :param version_info Module version information
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
    def dryrun_report(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Create a dryrun report

            :param tid The id of the environment
            :param id The version dryrun to report
        """

    @protocol(operation="PUT", mt=True, id=True, agent_server=True)
    def dryrun_update(self, tid: uuid.UUID, id: uuid.UUID, resource: str, changes: dict, log_msg: str=None):
        """
            Store dryrun results at the server

            :param tid The id of the environment
            :param id The version dryrun to report
            :param resource The id of the resource
            :param changes The required changes
            :param log_msg An optional log message (for example to report an error)
        """


class AgentDryRun(Method):
    """
        Method for requesting a dryrun from an agent
    """
    __method_name__ = "agent_dryrun"

    @protocol(operation="POST", mt=True, id=True, server_agent=True, timeout=5)
    def do_dryrun(self, tid: uuid.UUID, id: uuid.UUID, agent: str, version: int):
        """
            Do a dryrun on an agent

            :param tid The environment id
            :param id The id of the dryrun
            :param agent The agent to do the dryrun for
            :param version The version of the model to dryrun
        """


class NotifyMethod(Method):
    """
        Method to notify the server of changes in the configuration model source code
    """
    __method_name__ = "notify"

    @protocol(operation="GET", id=True)
    def notify_change(self, id: uuid.UUID, update: int=1):
        """
            Notify the server that the repository of the environment with the given id, has changed.

            :param id The id of the environment
            :param update Update the model code and modules. Default value is true (1)
        """

    @protocol(operation="HEAD", id=True)
    def is_compiling(self, id: uuid.UUID):
        """
           Is a compiler running for the given environment

           :param id The environment id
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

    @protocol(operation="PUT", mt=True, id=True)
    def set_param(self, tid: uuid.UUID, id: str, source: str, value: str, resource_id: str=None, metadata: dict={}):
        """
            Set a parameter on the server

            :param tid The id of the environment
            :param id The name of the parameter
            :param resource_id Optionally, scope the parameter to resource (fact)
            :param source The source of the parameter, this can be the user, agent, plugin, compiler, ...
            :param value The value of the parameter
            :param metadata metadata about the parameter
        """

    @protocol(operation="POST", index=True, mt=True)
    def list_params(self, tid: uuid.UUID, query: dict={}):
        """
            List the parameter of this environment

            :param tid The id of the environment
            :param query A query to match against metadata
        """


class ParametersMethod(Method):
    """
        Get and set parameters on the server
    """
    __method_name__ = "parameters"

    @protocol(operation="PUT", mt=True, index=True, agent_server=True)
    def set_parameters(self, tid: uuid.UUID, parameters: list):
        """
            Set a parameter on the server

            :param tid The id of the environment
            :param parameters A list of dicts with the following keys:
                - id The name of the parameter
                - source The source of the parameter, this can be the user, agent, plugin, compiler, ...
                - value The value of the parameter
                - resource_id Optionally, scope the parameter to resource (fact)
                - metadata metadata about the parameter
        """


class AgentParameterMethod(Method):
    """
        Get parameters from the agent
    """
    __method_name__ = "agent_parameter"

    @protocol(operation="POST", mt=True, server_agent=True, timeout=5)
    def get_parameter(self, tid: uuid.UUID, agent: str, resource: dict):
        """
            Get all parameters/facts known by the agents for the given resource

            :param tid The environment
            :param agent The agent get the parameters froms
            :param resource The resource to query the parameters from
        """


class FormMethod(Method):
    """
        Methods for creating and manipulating forms
    """
    __method_name__ = "form"

    @protocol(operation="GET", mt=True, index=True)
    def list_forms(self, tid: uuid.UUID):
        """
            List all available forms in an environment
        """

    @protocol(operation="GET", mt=True, id=True)
    def get_form(self, tid: uuid.UUID, id: str):
        """
            Get a form
        """

    @protocol(operation="PUT", mt=True, id=True)
    def put_form(self, tid: uuid.UUID, id: str, form: dict):
        """
            Upload a form
        """


class FormRecords(Method):
    """
        Methods for working with form records
    """
    __method_name__ = "records"

    @protocol(operation="GET", mt=True, index=True)
    def list_records(self, tid: uuid.UUID, form_type: str, include_record: bool=False):
        """
            Get a list of all records of a specific form

            :param tid The id of the environment
            :param form_type The type of the form
            :param include_record Include all the data contained in the record as well
        """

    @protocol(operation="GET", mt=True, id=True)
    def get_record(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Get a record from the server

            :param tid The id of the environment
            :param record_id The id of the record
        """

    @protocol(operation="PUT", mt=True, id=True)
    def update_record(self, tid: uuid.UUID, id: uuid.UUID, form: dict):
        """
            Update a record

            :param tid The id of the environment
            :param id The id of the record
            :param form The values of each field
        """

    @protocol(operation="POST", mt=True, index=True)
    def create_record(self, tid: uuid.UUID, form_type: str, form: dict):
        """
            Get a list of all records of a specific form

            :param tid The id of the environment
            :param form_type The type of the form
            :param form The values for each field
        """

    @protocol(operation="DELETE", mt=True, id=True)
    def delete_record(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Delete a record

            :param tid The id of the environment
            :param id The id of the record
        """


class CodeMethod(Method):
    """
        Upload code to the server
    """
    __method_name__ = "code"

    @protocol(operation="PUT", id=True, mt=True)
    def upload_code(self, tid: uuid.UUID, id: int, resource: str, sources: dict):
        """
            Upload the supporting code to the server

            :param tid The environment the code belongs to
            :param id The id (version) of the configuration model
            :param sources The source files that contain handlers and inmanta plug-ins
        """

    @protocol(operation="GET", id=True, mt=True, agent_server=True)
    def get_code(self, tid: uuid.UUID, id: int, resource: str):
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


class Snapshot(Method):
    """
        Methods to create and restore snapshots
    """
    __method_name__ = "snapshot"

    @protocol(operation="GET", index=True, mt=True)
    def list_snapshots(self, tid: uuid.UUID):
        """
            Create a list of all snapshots
        """

    @protocol(operation="GET", id=True, mt=True)
    def get_snapshot(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Get details about a snapshot and a list of resources that can be snapshotted
        """

    @protocol(operation="POST", mt=True, index=True)
    def create_snapshot(self, tid: uuid.UUID, name: str=None):
        """
            Request a new snapshot
        """

    @protocol(operation="PUT", mt=True, id=True, agent_server=True)
    def update_snapshot(self, tid: uuid.UUID, id: uuid.UUID, resource_id: str, snapshot_data: str, error: bool, success: bool,
                        start: datetime.datetime, stop: datetime.datetime, size: int, msg: str=None):
        """
            Update a snapshot with the details of a specific resource

            :param tid The environment the snapshot is created in
            :param id The id of the snapshot to update
            :param resource_id The id of the resource of which a snapshot was created
            :param snapshot_data The hash of the snapshot data that was uploaded to the fileserver
            :param start The time when the snapshot was started
            :param stop The time the snapshot ended
            :param size The size of the snapshot in bytes
            :param msg An optional message about the snapshot
        """

    @protocol(operation="DELETE", mt=True, id=True)
    def delete_snapshot(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Delete a snapshot
        """


class AgentSnapshot(Method):
    """
        Snapshot operations performed on the agent
    """
    __method_name__ = "agent_snapshot"

    @protocol(operation="POST", mt=True, server_agent=True, timeout=5)
    def do_snapshot(self, tid: uuid.UUID, agent: str, snapshot_id: uuid.UUID, resources: list):
        """
            Create a snapshot of the requested resource

            :param tid The environment the snapshot is created in
            :param agent The name of the agent
            :param snapshot_id The id of the snapshot to create
            :param resource A list of resources to snapshot
        """


class RestoreSnapshot(Method):
    """
        Restore a snapshot
    """
    __method_name__ = "restore"

    @protocol(operation="POST", mt=True, index=True)
    def restore_snapshot(self, tid: uuid.UUID, snapshot: uuid.UUID):
        """
            Restore a snapshot

            :param tid The environment the snapshot is created in
            :param snapshot The id of the snapshot to restore
        """

    @protocol(operation="POST", mt=True, id=True, agent_server=True)
    def update_restore(self, tid: uuid.UUID, id: uuid.UUID, resource_id: str, success: bool, error: bool, msg: str,
                       start: datetime.datetime, stop: datetime.datetime):
        """
            Update the status of a restore

            :param tid The environment to restore the snapshot in
            :param id The id of the restore
            :param resource_id The state id of the resource that was restored.
        """

    @protocol(operation="GET", mt=True, index=True)
    def list_restores(self, tid: uuid.UUID):
        """
            List finished and ongoing restores
        """

    @protocol(operation="GET", mt=True, id=True)
    def get_restore_status(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Get the status of a restore
        """

    @protocol(operation="DELETE", mt=True, id=True)
    def delete_restore(self, tid: uuid.UUID, id: uuid.UUID):
        """
            Cancel a restore
        """


class AgentRestore(Method):
    """
        Snapshot operations performed on the agent
    """
    __method_name__ = "agent_restore"

    @protocol(operation="POST", mt=True, server_agent=True, timeout=5)
    def do_restore(self, tid: uuid.UUID, agent: str, restore_id: uuid.UUID, snapshot_id: uuid.UUID, resources: list):
        """
            Create a snapshot of the requested resource

            :param tid The environment the snapshot is created in
            :param agent The name of the agent
            :parma restore_id THe id of the restore operation
            :param snapshot_id The id of the snapshot to restore
            :param resource A list of resources to restore
        """


class NodeMethod(Method):
    """
        Get a list of all agents
    """
    __method_name__ = "agentproc"

    @protocol(operation="GET", index=True)
    def list_agent_processes(self, environment: uuid.UUID=None, expired: bool=True):
        """
            Return a list of all nodes and the agents for these nodes

            :param environment An optional environment. If set, only the agents that belong to this environment are returned
            :param all  Optional, also show expired.
            :return A list of nodes
        """

    @protocol(operation="GET", id=True)
    def get_agent_process(self, id: uuid.UUID):
        """
            Return a detailed report for a node

            :param agentid The id of the node
            :return The requested node
        """


class ServerAgentApiMethod(Method):
    """
        Get a list of all agents
    """
    __method_name__ = "agent"

    @protocol(operation="POST", id=True, mt=True, api=True, timeout=5)
    def trigger_agent(self, tid: uuid.UUID, id: str):
        """
            Request the server to reload an agent

            :param tid The environment this agent is defined in
            :param id The name of the agent
            :return The requested node
        """

    @protocol(operation="GET", mt=True, api=True, timeout=5)
    def list_agents(self, tid: uuid.UUID):
        """
            List all agent for an environment

            :param tid The environment the agents are defined in
        """


class AgentReporting(Method):
    """
        Reporting by the agent to the server
    """
    __method_name__ = "status"

    @protocol(operation="GET", server_agent=True, timeout=5)
    def get_status(self):
        """
            Report status to the server
        """


class AgentState(Method):
    """
        Methods to allow the server to set the agents state
    """
    __method_name__ = "agentstate"

    @protocol(operation="POST", server_agent=True, timeout=5)
    def set_state(self, agent: str, enabled: bool):
        """
            Set the state of the agent.
        """

    @protocol(operation="POST", id=True, mt=True, server_agent=True, timeout=5)
    def trigger(self, tid: uuid.UUID, id: str):
        """
            Request an agent to reload resources

            :param tid The environment this agent is defined in
            :param id The name of the agent
        """


class AgentResourceEvent(Method):
    """
        Methods to send event to the server
    """
    __method_name__ = "event"

    @protocol(operation="PUT", id=True, mt=True, server_agent=True, timeout=5)
    def resource_event(self, tid: uuid.UUID, id: str, resource: str, state: str):
        """
            Tell an agent a resource it waits for has been updated

            :param tid The environment this agent is defined in
            :param id The name of the agent
            :param resource The resource ID of the resource being updated
            :param state State the resource acquired (deployed, skipped, canceled)
        """


class AgentRecovery(Method):
    """
        Methods for the agent to get its initial state from the server
    """
    __method_name__ = "agentrecovery"

    @protocol(operation="GET", mt=True, agent_server=True)
    def get_state(self, tid: uuid.UUID, sid: uuid.UUID, agent: str):
        """
            Get the state for this agent.

            returns a map
            {
             enabled: bool
            }
        """
