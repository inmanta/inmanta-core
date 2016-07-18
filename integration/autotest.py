from integration import Project, Environment, Connection, run_async, SetForm, Server, wait_async

from inmanta.config import Config
from tornado import httpclient
import logging
from subprocess import CalledProcessError
from time import sleep
from tornado.escape import json_decode
from tornado.httpclient import HTTPRequest

import os

LOGGER = logging.getLogger(__name__)


##################
# Pre setup
##################

Config.load_config()

stream = logging.StreamHandler()
stream.setLevel(logging.INFO)

logging.root.handlers = []
logging.root.addHandler(stream)
logging.root.setLevel(logging.DEBUG)


def get_os_credentials():
    keytoenv = {"connection_url": "OS_AUTH_URL",
                "password": "OS_PASSWORD",
                "username": "OS_USERNAME",
                "tenant": "OS_TENANT_NAME"}

    env = os.environ

    for envname in keytoenv.values():
        if envname not in env:
            raise Exception("Env var %s is not set" % envname)

    out = {k: env[v] for k, v in keytoenv.items()}

    out["network_name"] = out["tenant"] + "_lab"
    return out


def setup(env):
    # clone project
    project = Project("git@git.inmanta.com:demo/impera-demo.git", "/tmp/autotest/demo")
    project.init()

    try:
        LOGGER.info("Starting first compile run")
        project.compile(env, "/tmp/autotest/demo/compile1.log")
        LOGGER.info("Done first compile run, flawless")
    except CalledProcessError:
        LOGGER.info("Done first compile run")

    # patch for repo

    # export to env

    # fill forms
    LOGGER.info("Filling forms")
    run_async(SetForm(env, "demo::ApplicationForm", {"size": 1}).init)
    run_async(SetForm(env, "demo::CloudProvider", {"provider": "Openstack"}).init)

    LOGGER.info("Starting second compile run")
    project.compile(env, "/tmp/autotest/demo/compile2.log")

    LOGGER.info("Filling more forms")
    run_async(SetForm(env, "demo::OpenStackForm", get_os_credentials()).init)

    LOGGER.info("Starting first export")
    # export to env
    version = project.export(env, "/tmp/autotest/demo/export1.log")

    LOGGER.info("Starting first deploy")
    # deploy version
    run_async(lambda: env.deploy(version))

    LOGGER.info("Waiting for hosts to be deployed")
    # wait for deploy to finish
    run_async(lambda: env.waitForDeploy(version, 4))

    LOGGER.info("Waiting for agents to be up")
    # wait for agents
    run_async(lambda: env.waitForAgents(5))

    LOGGER.info("Sleep 20s, to wait for facts")
    sleep(20)

    LOGGER.info("Starting second export")
    version = project.export(env, "/tmp/autotest/demo/export2.log")

    LOGGER.info("Starting second deploy")
    run_async(lambda: env.deploy(version))

    LOGGER.info("Waiting for everything to be deployed")
    run_async(lambda: env.waitForDeploy(version))
    LOGGER.info("Deploy done")


def verify_endpoints(env):
    # verify endpoints
    LOGGER.info("Getting Endpoints")
    endpoints = run_async(env.get_endpoints)
    http_client = httpclient.HTTPClient()
    for endpoint in endpoints.values():
        try:
            LOGGER.info("Fetching %s", endpoint)
            http_client.fetch(endpoint)
            LOGGER.info("Success for %s", endpoint)
        except Exception:
            LOGGER.info("Failure for %s", endpoint, exc_info=True)

    http_client.close()


def test_restore(env):
    http_client = httpclient.HTTPClient()

    LOGGER.info("Getting Endpoints")
    endpoints = run_async(env.get_endpoints)

    main_ep = endpoints["Application loadbalancer"]
    LOGGER.info("Found main endpoint at %s", main_ep)

    LOGGER.info("Getting wines")
    response = http_client.fetch(main_ep + "/wines")
    wines = json_decode(response.body)

    LOGGER.info("Got %d wines", len(wines))

    LOGGER.info("Making snapshot")
    snap = run_async(env.snapshot)
    LOGGER.info("Waiting for snapshot")
    run_async(lambda: env.wait_for_snapshot(snap))
    LOGGER.info("Snapshot done")

    LOGGER.info("Deleting first wine")
    http_client.fetch(HTTPRequest(main_ep + "/wines/" + wines[0]["_id"], method="DELETE"))
    LOGGER.info("Getting wines")
    newwines = json_decode(http_client.fetch(main_ep + "/wines").body)
    LOGGER.info("Got %d wines", len(newwines))

    assert len(wines) == len(newwines) + 1

    LOGGER.info("Starting restore")
    res = run_async(lambda: env.restore(snap))
    LOGGER.info("Waiting for restore")
    run_async(lambda: env.wait_for_restore(res))
    LOGGER.info("Restore done")

    LOGGER.info("Getting wines")
    response = http_client.fetch(main_ep + "/wines")
    oldwines = json_decode(response.body)
    LOGGER.info("Got %d wines", len(oldwines))

    assert wines == oldwines

    http_client.close()


def run_test(auth, ssl):
    with Server("/tmp/autotest/server", "172.17.3.106", auth=auth, ssl=ssl) as server:
        connection = Connection("172.17.3.106", auth, ssl)
        wait_async(connection)

        env = Environment(connection, "autotest", "demo")
        run_async(env.init)

        setup(env)
        LOGGER.info("Waiting 30s for service to become active")
        sleep(30)
        verify_endpoints(env)
        test_restore(env)
        LOGGER.info("Breaking it down")
        run_async(env.purge)
        LOGGER.info("Success")

if __name__ == '__main__':
    run_test(False, False)
