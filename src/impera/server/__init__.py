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

import datetime
import logging
import os
import difflib
from threading import RLock

from pymongo import Connection
from blitzdb.backends.mongo import Backend as MongoBackend
from blitzdb import FileBackend
import tornado.escape
from impera import methods
from impera import protocol
from impera import env
from impera.config import Config
from impera.loader import CodeLoader
from impera.protocol import AMQPTransport, RESTTransport, DirectTransport, ServerClientEndpoint
from impera.resources import Id
from impera.resources import Resource as Res
from impera.server.persistence import Node, Agent, Version, ResourceVersion, Resource, Fact


LOGGER = logging.getLogger(__name__)


class Server(ServerClientEndpoint):
    """
        The central Impera server that communicates with clients and agents and persists configuration
        information
    """
    __transports__ = [DirectTransport, AMQPTransport, RESTTransport]

    def __init__(self, code_loader=True):
        super().__init__("server", role="server")
        LOGGER.info("Starting server endpoint")
        self._server_storage = self.check_storage()

        db_type = Config.get("database", "type", "file")
        if db_type == "file":
            self._db = FileBackend(os.path.join(self._server_storage["db"]))
            LOGGER.info("Connected to filebackend database")
        elif db_type == "mongo":
            c = Connection()
            imp_db = c.imp_db
            self._db = MongoBackend(imp_db)
            LOGGER.info("Connected to mongodb database")

        else:
            raise Exception("%s databse type is not supported" % db_type)

        if code_loader:
            self._env = env.VirtualEnv(self._server_storage["env"])
            self._env.use_virtual_env()
            self._loader = CodeLoader(self._server_storage["code"])
        else:
            self._loader = None

        self._fact_expire = int(Config.get("config", "fact-expire", 3600))
        self.add_end_point_name(self.node_name)

        self._db_lock = RLock()

        self.schedule(self.renew_expired_facts, 60)

    def check_storage(self):
        """
            Check if the server storage is configured and ready to use.
        """
        if "config" not in Config.get() or "state-dir" not in Config.get()["config"]:
            raise Exception("The Impera server requires a state directory to be configured")

        state_dir = Config.get()["config"]["state-dir"]

        if not os.path.exists(state_dir):
            os.mkdir(state_dir)

        server_state_dir = os.path.join(state_dir, "server")

        if not os.path.exists(server_state_dir):
            os.mkdir(server_state_dir)

        dir_map = {"server": server_state_dir}

        file_dir = os.path.join(server_state_dir, "files")
        dir_map["files"] = file_dir
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)

        db_dir = os.path.join(server_state_dir, "database")
        dir_map["db"] = db_dir
        if not os.path.exists(db_dir):
            os.mkdir(db_dir)

        code_dir = os.path.join(server_state_dir, "code")
        dir_map["code"] = code_dir
        if not os.path.exists(code_dir):
            os.mkdir(code_dir)

        env_dir = os.path.join(server_state_dir, "env")
        dir_map["env"] = env_dir
        if not os.path.exists(env_dir):
            os.mkdir(env_dir)

        return dir_map

    def renew_expired_facts(self):
        """
            Send out requests to renew expired facts
        """
        resources = {}
        facts = self._db.filter(Fact, {'value_time': {'$lt': datetime.datetime.now().timestamp() + self._fact_expire}})

        for fact in facts:
            res = fact.resource
            if res.pk not in resources:  # query the facts again
                self.retrieve_facts(res.pk, res)
                resources[res.pk] = res

    def retrieve_facts(self, resource_id, resource):
        """
            Request facts about a resource
        """
        # get the latest resource we have for resource
        resource_list = list(self._db.filter(ResourceVersion, {"resource": resource}, limit=1).sort("pk"))

        if len(resource_list) > 0:
            parsed_id = Id.parse_id(resource_id)
            resource_data = resource_list[0]["data"]

            result = self._client.call(methods.RetrieveFacts, async=True, destination="host.agent.%s" % parsed_id.agent_name,
                                       resource_id=resource_id, resource=resource_data)

            def store_facts(result):
                # store the result (although multiple can be available we only store the first one
                if result._multiple:
                    body = result.result[0]
                else:
                    body = result.result

                if "facts" not in body:
                    return

                facts = body["facts"]

                values = {}
                with self._db_lock:
                    for name, value in facts.items():
                        fact = Fact.create(self._db, resource, parsed_id.entity_type, name, value,
                                           datetime.datetime.now().timestamp())
                        fact.save(self._db)
                        values[name] = value

                    self._db.commit()

                return values

            if result.available():
                return store_facts(result)

            else:
                result.callback(store_facts)

            return None

    @protocol.handle(methods.GetFact)
    def facts(self, operation, body):
        """
            Retrieve facts
        """
        if operation is None:
            with self._db_lock:
                if "resource_id" not in body or "fact_name" not in body:
                    raise Exception("The resource id and name of the fact is required")

                resource_id = body["resource_id"]
                fact_name = body["fact_name"]

                try:
                    resource = self._db.get(Resource, {"pk": resource_id})
                except Resource.DoesNotExist:
                    return 404

                try:
                    fact = self._db.get(Fact, {"pk": "%s_%s" % (resource.id, fact_name)})
                    if float(fact.value_time) + self._fact_expire > datetime.datetime.now().timestamp():
                        return 200, {"resource_id": resource_id, "fact_name": fact_name, "value": fact.value}

                except Fact.DoesNotExist:
                    pass

                result = self.retrieve_facts(resource_id, resource)
                if result is not None and fact_name in result:
                    return 200, {"resource_id": resource_id, "fact_name": fact_name, "value": result[fact_name]}

                return 404

        return 501

    @protocol.handle(methods.FileMethod)
    def handle_file(self, operation, body):
        """
            Handle files on the server
        """
        if body is None or "id" not in body:
            return 501

        else:
            rid = body["id"]
            file_name = os.path.join(self._server_storage["files"], rid)
            if operation == "GET":
                if not os.path.exists(file_name):
                    return 404

                else:
                    with open(file_name, "rb") as fd:
                        return 200, {"content": fd.read().decode()}

            elif operation == "HEAD":
                if os.path.exists(file_name):
                    return 200
                else:
                    return 404

            elif operation == "PUT":
                if "content" in body:
                    with open(file_name, "wb+") as fd:
                        fd.write(tornado.escape.utf8(body["content"]))

                    return 200
                else:
                    return 500

        return 501

    @protocol.handle(methods.StatMethod)
    def stat_files(self, operation, body):
        """
            Return which files in the list exist on the server
        """
        if "files" not in body:
            raise Exception("The stat method requires a list of files")

        files = body["files"]
        response = []
        for f in files:
            f_path = os.path.join(self._server_storage["files"], f)
            if not os.path.exists(f_path):
                response.append(f)

        return 200, {"files": response}

    @protocol.handle(methods.FileDiff)
    def file_diff(self, operation, body):
        """
            Diff the two files identified with the two hashes
        """
        if body["a"] == "" or body["a"] == 0:
            a_lines = []
        else:
            a_path = os.path.join(self._server_storage["files"], body["a"])
            with open(a_path, "r") as fd:
                a_lines = fd.readlines()

        if body["b"] == "" or body["b"] == 0:
            b_lines = []
        else:
            b_path = os.path.join(self._server_storage["files"], body["b"])
            with open(b_path, "r") as fd:
                b_lines = fd.readlines()

        try:
            diff = difflib.unified_diff(a_lines, b_lines, fromfile=body["a"], tofile=body["b"])
        except FileNotFoundError:
            return 404

        return 200, "".join(diff)

    @protocol.handle(methods.HeartBeatMethod)
    def heartbeat(self, operation, body):
        """
            Receive and store heartbeats
        """
        if "endpoint_names" not in body or "nodename" not in body:
            LOGGER.error("Invalid heartbeat")
            return 500

        with self._db_lock:
            now = datetime.datetime.now()
            node = Node.create(self._db, hostname=body["nodename"], lastseen=now)
            node.save(self._db)

            for nh in body["endpoint_names"]:
                agent = Agent.create(self._db, name=nh, node=node, role=body["role"],
                                     interval=body["interval"], lastseen=now)
                agent.save(self._db)

            self._db.commit()

        return 200

    @protocol.handle(methods.NodeMethod)
    def nodes(self, operation, body):
        with self._db_lock:
            try:
                if body is not None and "id" in body:
                    node = self._db.get(Node, {"pk": body["id"]})
                    agents = self._db.filter(Agent, {"node": node})
                    return 200, {"node": node.attributes, "agents": [{k: v for k, v in a.attributes.items()
                                                                      if k != "node"} for a in agents]}

                else:
                    return 200, {"nodes": [x.attributes for x in self._db.filter(Node, {})]}

            except (Node.DoesNotExist, Agent.DoesNotExist):
                return 404

        return 501

    @protocol.handle(methods.ResourceMethod)
    def resource(self, operation, body):
        resource_id = Id.parse_id(body["id"])

        if resource_id.version > 0:
            with self._db_lock:
                try:
                    resv = self._db.get(ResourceVersion, {"pk": "%s_%s" % (resource_id.resource_str(), resource_id.version)})

                    attributes = resv.attributes
                    del attributes["resource"]
                    del attributes["version"]

                    return 200, attributes
                except ResourceVersion.DoesNotExist:
                    return 404

        return 404

    @protocol.handle(methods.VersionMethod)
    def version(self, operation, body):
        if body is None or "id" not in body:
            if operation == "GET":
                with self._db_lock:
                    versions = self._db.filter(Version, {}).sort("date")
                return 200, {"versions": [v.attributes for v in versions]}

        else:
            v_id = int(body["id"])
            if operation == "GET":
                with self._db_lock:
                    try:
                        version = self._db.get(Version, {"pk": v_id})

                        ret_val = {"version": version.attributes,
                                   "resources": [{"id": x.resource.id, "updated": x.updated, "agent": x.resource.agent.name,
                                                  "status": x.status}
                                                 for x in self._db.filter(ResourceVersion, {"version": version})]}
                        ret_val["total_resources"] = len(ret_val["resources"])
                        ret_val["completed_resources"] = len(self._db.filter(ResourceVersion,
                                                                             {"version": version, "updated": True}))

                        return 200, ret_val
                    except Version.DoesNotExist:
                        return 404

            elif operation == "PUT":
                if "version" not in body or "resources" not in body:
                    raise Exception("A version and resources are required in the request")

                version_id = body["version"]
                resources = body["resources"]

                with self._db_lock:
                    try:
                        self._db.get(Version, {"pk": version_id})
                        raise Exception("This version already exists")

                    except Version.DoesNotExist:
                        pass

                    version = Version.create(self._db, version_id=version_id, date=datetime.datetime.now().timestamp())
                    version.save(self._db)

                    for res in resources:
                        resource = Res.deserialize(res)
                        res_version = ResourceVersion.create(self._db, resource_id=resource.id, version=version, data=res)
                        res_version.save(self._db)

                    self._db.commit()
                    LOGGER.debug("Successfully stored version %d" % v_id)

                return 200

        return 501

    @protocol.handle(methods.CodeMethod)
    def code(self, operation, body):
        if operation is None:
            version = body["version"]
            modules = body["sources"]
            requires = body["requires"]

            if self._loader is not None:
                self._env.install_from_list(requires)
                self._loader.deploy_version(int(version), modules, persist=True)
                self._client.call(methods.CodeDeploy, destination="host.agent", modules=modules, version=version,
                                  requires=requires)

            return 200

        return 501

    @protocol.handle(methods.DeployVersion)
    def deploy_version(self, operation, body):
        """
            Broadcast resource of the given version to all agents and start deploying them
        """
        LOGGER.debug("Requesting deploy of version %s" % body["version"])
        with self._db_lock:
            try:
                version = self._db.get(Version, {"pk": int(body["version"])})
                LOGGER.debug("Loaded version %s from database" % body["version"])
                resources = self._db.filter(ResourceVersion, {"version": version})
                LOGGER.debug("Loaded resources for version %s from database" % body["version"])
            except (Version.DoesNotExist, ResourceVersion.DoesNotExist):
                return 404

            dry_run = False
            if "dry_run" in body and body["dry_run"]:
                dry_run = True

            version.dry_run = dry_run
            version.deploy_started = datetime.datetime.now().timestamp()
            version.save(self._db)

            for resource in resources:
                agent = resource.resource.agent.name
                self._client.call(methods.ResourceUpdate, destination="host.agent.%s" % agent,
                                  resource=resource.data, version=version.pk, dry_run=dry_run)
                resource.sent = True
                self._db.save(resource)

            self._db.commit()

        return 200

    @protocol.handle(methods.ResourceUpdated)
    def resource_updated(self, operation, body):
        rid = body["id"]
        version = int(body["version"])
        status = body["status"]

        with self._db_lock:
            try:
                resource = self._db.get(Resource, {"pk": rid})
                version = self._db.get(Version, {"pk": version})
                resource_version = self._db.get(ResourceVersion, {"version": version, "resource": resource})

                resource_version.updated = True
                resource_version.status = status
                if len(body["changes"]) > 0:
                    resource_version.changes = body["changes"]

                self._db.save(resource_version)
                self._db.commit()

                # check if the deploy of this version is ready
                resources = [x for x in self._db.filter(ResourceVersion, {"version": version}) if x.status == "not handled"]
                if len(resources) > 0:
                    version.deploy_ready = datetime.datetime.now().timestamp()
                    self._db.save(version)
                    self._db.commit()

            except BaseException:
                LOGGER.exception("An error occured while saving a resource update")

        return 200
