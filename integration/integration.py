from inmanta.config import Config

import inmanta.protocol
from tornado.ioloop import IOLoop
from tornado import gen
import logging
from uuid import UUID
from inmanta.module import gitprovider, Module
from inmanta import module
import shutil
from os import makedirs
from os.path import os
from inmanta.compiler import do_compile
from inmanta.ast import RuntimeException
import sys
import subprocess
from subprocess import CalledProcessError
import re
import datetime
from datetime import timedelta
import dateutil.parser
from time import sleep
from shutil import rmtree
from inmanta.config import TransportConfig
import tempfile
from inmanta.server.agentmanager import AgentManager
import time


LOGGER = logging.getLogger(__name__)


def gate_async(item):
    out = IOLoop.current().run_sync(item.test)
    if not out:
        raise Exception("failed gate")


def wait_async(item):
    while True:
        out = IOLoop.current().run_sync(item.test)
        if out:
            return
        sleep(5)


def run_async(func):
    return IOLoop.current().run_sync(func)


def unwrap(result):
    if result.code != 200:
        raise Exception("call returned bad error code: %d" % result.code)
    return result.get_result()


def patch(dir, patch):
    bpatch = patch.encode()
    if subprocess.run(["patch", "-R", "-p1", "--dry-run"], input=bpatch, cwd=dir).returncode != 0:
        subprocess.run(["patch", "-p1"], input=bpatch, cwd=dir).check_returncode()


class Server(object):

    def __init__(self, path, host, auth=False, ssl=False, autostart="iaas_*"):
        path = os.path.abspath(path)
        print("server root @:", path)
        makedirs(path, exist_ok=True)

        if ssl:
            if not os.path.exists("/etc/pki/tls/certs/server.crt"):
                raise Exception("Create server cert @ /etc/pki/tls/certs/server.crt")
            if not os.path.exists("/etc/pki/tls/certs/server.open.key"):
                raise Exception("Create server private key @/etc/pki/tls/certs/server.open.key")

        with open(os.path.join(path, ".inmanta"), "w") as file:
            file.write("""
[config]
state-dir=%s/state
heartbeat-interval = 60
log-dir=%s/logs

[server]
fact-expire = 600
fact-renew = 200
no-recompile = true
auto-recompile-wait = 10
server_address= %s
agent-autostart = %s
""" % (path, path, host, autostart))
            if auth:
                file.write("""
username=jos
password=raienvnWAVbaerMSZ
""")
            if ssl:
                file.write("""
ssl_cert_file = /etc/pki/tls/certs/server.crt
ssl_key_file = /etc/pki/tls/certs/server.open.key
""")
            file.write("""
[server_rest_transport]
port = 8888

[dashboard]
# Host the dashboard from within the server. The server does not (yet) override the config.js file
# of the dashboard. This will need to be configured manually. The dashboard will be available
# on the server under /dashboard/
enabled=true
# The path where the dashboard is installed
path=/home/wouter/projects/inmanta-dashboard/dist""")

        app = os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py"))
        inmanta_path = [sys.executable, app]
        args = inmanta_path + ["-v", "--log-file", os.path.join(path, "log"), "--log-file-level", "4", "server"]
        self.proc = subprocess.Popen(args, cwd=path, env=os.environ.copy())
        if host != "127.0.0.1" and host != "localhost":
            self.tunnel = subprocess.Popen(
                ["ssh", "-R", "*:8888:127.0.0.1:8888", "fedora@%s" % host], cwd=path, env=os.environ.copy())
        else:
            self.tunnel = None

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        self.proc.terminate()
        if self.tunnel is not None:
            self.tunnel.terminate()


class Connection(object):

    def __init__(self, server, auth=False, ssl=False):
        self.server = server
        TransportConfig("autotest")
        Config.set("autotest_rest_transport", "host", self.server)
        Config.set("autotest_rest_transport", "port", "8888")
        Config.set("compiler_rest_transport", "host", self.server)
        Config.set("compiler_rest_transport", "port", "8888")

        if auth:
            Config.set("autotest_rest_transport", "username", "jos")
            Config.set("autotest_rest_transport", "password", "raienvnWAVbaerMSZ")
            Config.set("compiler_rest_transport", "username", "jos")
            Config.set("compiler_rest_transport", "password", "raienvnWAVbaerMSZ")

        if ssl:
            Config.set("autotest_rest_transport", "ssl", "true")
            Config.set("compiler_rest_transport", "ssl", "true")
            Config.set("autotest_rest_transport", "ssl_ca_cert_file", "/etc/pki/tls/certs/server.crt")
            Config.set("compiler_rest_transport", "ssl_ca_cert_file", "/etc/pki/tls/certs/server.crt")

        self._client = inmanta.protocol.Client("autotest")
        self.auth = auth
        self.ssl = ssl

    @gen.coroutine
    def test(self):
        res = yield self._client.list_projects()
        # print(res.code)
        return res.code == 200


class SetForm(object):

    def __init__(self, env, name, fields):
        self.connection = env.connection
        self.env = env
        self.name = name
        self.fields = fields

    @gen.coroutine
    def init(self):
        records = yield self.connection._client.list_records(self.env.envid, self.name, True)
        done = False
        for record in records.get_result()["records"]:
            if record["fields"] == self.fields and not done:
                done = True
            else:
                yield self.connection._client.delete_record(self.env.envid, record["record_id"])

        if not done:
            yield self.connection._client.create_record(self.env.envid,  self.name, self.fields)
            LOGGER.info("set form %s to %s", self.name, self.fields)


class Environment(object):

    def __init__(self, connection, project, env, purge=False):
        self.connection = connection
        self.project = project
        self.env = env
        self.auth = connection.auth
        self.ssl = connection.ssl
        self.purge_if_exists = purge

    @gen.coroutine
    def init(self):
        projects = yield self.connection._client.list_projects()
        idx = {x["name"]: x for x in projects.get_result()["projects"]}
        if self.project in idx:
            projectID = idx[self.project]["id"]
            LOGGER.info("found project %s %s", self.project, projectID)
        else:
            project = yield self.connection._client.create_project(self.project)
            projectID = project.get_result()["project"]["id"]
            LOGGER.info("created project %s %s", self.project, projectID)

        envs = yield self.connection._client.list_environments()
        envs = envs.get_result()["environments"]

        idx = {x["name"]: x for x in envs if x["project"] == projectID}

        if self.env in idx:
            envID = idx[self.env]["id"]
            LOGGER.info("found env %s %s", self.env, envID)
            if self.purge_if_exists:
                yield self._destroy(envID)
                envID = yield self._create(projectID, self.env)
        else:
            envID = yield self._create(projectID, self.env)

        self.envid = envID

    @gen.coroutine
    def _create(self, projectID, env_name):
        env = yield self.connection._client.create_environment(UUID(projectID), env_name)
        envID = env.get_result()["environment"]["id"]
        LOGGER.info("created env %s in %s", envID, projectID)
        return envID

    @gen.coroutine
    def _destroy(self, envID):
        yield self.connection._client.clear_environment(envID)
        yield self.connection._client.delete_environment(envID)

    @gen.coroutine
    def deploy(self, version):
        yield self.connection._client.release_version(self.envid, version, True)

    @gen.coroutine
    def dryrun(self, version):
        result = yield self.connection._client.dryrun_request(self.envid, version)
        result = unwrap(result)
        return result["dryrun"]["id"]

    @gen.coroutine
    def wait_for_dryrun(self, id):
        while True:
            result = yield self.connection._client.dryrun_report(self.envid, id)
            result = unwrap(result)
            if result["dryrun"]["todo"] == 0:
                return
            yield gen.sleep(2)

    @gen.coroutine
    def waitForDeploy(self, version, total=None):
        while True:
            result = yield self.connection._client.get_version(self.envid, version)
            result = unwrap(result)
            if total is None:
                total = result["model"]["total"]
            if "model" not in result:
                return
            done = result["model"]["done"]
            if done >= total:
                return
            else:
                yield gen.sleep(5)

    @gen.coroutine
    def waitForAgents(self, total):
        while True:
            result = yield self.connection._client.list_agents(self.envid)
            result = unwrap(result)
            agents = [x for x in result["agents"] if x["state"] == "up"]
            if len(agents) >= total:
                return
            else:
                yield gen.sleep(5)

    @gen.coroutine
    def waitAgentTimeout(self):
        print("waiting for agents to timeout")
        xtime = time.time()
        waiting = True
        while waiting:
            result = yield self.connection._client.list_agents(self.envid)
            result = unwrap(result)
            agents = [x for x in result["agents"] if x["state"] == "up"]
            if len(agents) == 0:
                waiting = False
            else:
                yield gen.sleep(5)
        print("waited %s" % (time.time() - xtime))

    @gen.coroutine
    def get_endpoints(self):
        result = yield self.connection._client.list_params(self.envid)
        result = unwrap(result)
        print(result)
        reports = {x["name"]: x["value"]
                   for x in result["parameters"] if "metadata" in x and x["metadata"] is not None and "type" in x["metadata"] and x["metadata"]["type"] == "report"}
        return reports

    @gen.coroutine
    def snapshot(self):
        result = yield self.connection._client.create_snapshot(self.envid, "TestShot")
        result = unwrap(result)
        return result["snapshot"]["id"]

    @gen.coroutine
    def restore(self, id):
        result = yield self.connection._client.restore_snapshot(self.envid, id)
        result = unwrap(result)
        return result["restore"]["id"]

    @gen.coroutine
    def wait_for_snapshot(self, id):
        while True:
            result = yield self.connection._client.get_snapshot(self.envid, id)
            result = unwrap(result)
            if result["snapshot"]["finished"] is not None:
                return
            yield gen.sleep(5)

    @gen.coroutine
    def wait_for_restore(self, id):
        while True:
            result = yield self.connection._client.get_restore_status(self.envid, id)
            result = unwrap(result)
            if result["restore"]["finished"] is not None:
                return
            yield gen.sleep(5)

    @gen.coroutine
    def purge(self):
        result = yield self.connection._client.decomission_environment(self.envid)
        result = unwrap(result)
        version = result["version"]
        yield(self.deploy(version))
        yield(self.waitForDeploy(version))

    @gen.coroutine
    def clear(self):
        yield self.connection._client.clear_environment(self.envid)

    def start_agent(self, base_path, agent, agentmap):
        base_path = os.path.abspath(os.path.join(base_path, agent))
        os.makedirs(base_path, exist_ok=True)

        cfg = """
[config]
heartbeat-interval = 60
state-dir=%s

agent-names = %s
environment=%s
agent-map=%s

agent-interval = 60
agent-splay = 2

agent-run-at-start=true
""" % (base_path, ",".join(agentmap.keys()), self.envid, ",".join(["%s=%s" % (k, v) for (k, v) in agentmap.items()]))

        config_path = os.path.join(base_path, "agent.cfg")
        with open(config_path, "w+") as fd:
            fd.write(cfg)

        app = os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py"))
        inmanta_path = [sys.executable, app]
        args = inmanta_path + ["-vvvv", "--timed-logs", "--config", config_path, "agent"]

        outfile = os.path.join(base_path, "out.log")
        err = os.path.join(base_path, "err.log")

        with open(outfile, "wb+") as outhandle:
            with open(err, "wb+") as errhandle:
                return subprocess.Popen(args, stdout=outhandle, stderr=errhandle, cwd=base_path, env=os.environ.copy())


class Project(object):

    def __init__(self, repo, target, purge, inplace=False):
        self.repo = repo
        self.target = target
        self.purge = purge
        self.inplace = inplace

    def init(self):
        if self.inplace:
            self.target = os.path.abspath(self.target)
            if not os.path.exists(self.target):
                raise Exception("Project not found", self.target)
        else:
            if os.path.exists(self.target) and self.purge:
                rmtree(self.target)
            makedirs(self.target, exist_ok=True)
            if not os.path.exists(os.path.join(self.target, ".git")):
                gitprovider.clone(self.repo, self.target)
                LOGGER.info("created project")
            else:
                gitprovider.fetch(self.target)
                LOGGER.info("updated project")
        self.project = module.Project(self.target)
        module.Project.set(self.project)

    def compile(self, env, logfile=None, envvars=None):
        Config.set("config", "environment", env.envid)
        # reset compiler state
        # do_compile()

        apppath = os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py"))
        args = [sys.executable, apppath]

        if logfile is not None:
            args += ["--log-file", logfile, "--log-file-level", "3", "-v"]
        else:
            args += ["-vvv"]

        args = args + ["compile",  "-e", env.envid,
                       "--server_address", env.connection.server, "--server_port", "8888"]

        if env.auth:
            args += ["--username", "jos", "--password", "raienvnWAVbaerMSZ"]

        if env.ssl:
            args += ["--ssl", "--ssl-ca-cert", "/etc/pki/tls/certs/server.crt"]
        try:
            env = os.environ.copy()
            if envvars is not None:
                for k, v in envvars.items():
                    env[k] = v
            subprocess.check_output(args, cwd=self.target, env=env)
        except CalledProcessError as e:
            print(e.output)
            raise e

    def export(self, env, logfile, envvars=None):
        Config.set("config", "environment", env.envid)
        # reset compiler state
        # do_compile()

        app = os.path.abspath(os.path.join(__file__, "../../src/inmanta/app.py"))

        inmanta_path = [sys.executable, app]
        args = inmanta_path
        if logfile is None:
            logfile = tempfile.mktemp()
        logfile = os.path.abspath(logfile)

        args += ["--log-file", logfile, "--log-file-level", "3"]

        args = args + ["-v", "export",  "-e", env.envid,
                       "--server_address", env.connection.server, "--server_port", "8888"]

        if env.auth:
            args += ["--username", "jos", "--password", "raienvnWAVbaerMSZ"]

        if env.ssl:
            args += ["--ssl", "--ssl-ca-cert", "/etc/pki/tls/certs/server.crt"]

        try:
            env = os.environ.copy()
            if envvars is not None:
                for k, v in envvars.items():
                    env[k] = v
            subprocess.check_call(args, cwd=self.target, env=env, stderr=subprocess.STDOUT)
            out = subprocess.check_output(
                ["grep", "Committed resources with version", logfile], env=os.environ.copy(), universal_newlines=True)

            return re.search(r'Committed resources with version ([0-9]+)', out).group(1)
        except CalledProcessError as e:
            print(e.output.decode("utf-8"))
            raise e
