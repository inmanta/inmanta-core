from integration import Project, Environment, Connection, run_async, SetForm, Server, wait_async, patch

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


def setup(env, purge=False):
    # clone project
    project = Project("git@git.inmanta.com:demo/impera-demo.git", "/tmp/autotest/demo", purge)
    project.init()
    do_patch(project.target)

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


def do_patch(dir):
    patch(os.path.join(dir, "libs/rabbitmq"), """diff --git a/requirements.txt b/requirements.txt
index f5c077a..265e832 100644
--- a/requirements.txt
+++ b/requirements.txt
@@ -1 +1 @@
-git+https://github.com/davidszotten/pyrabbit@permissions#pyrabbit
+pyrabbit~=1.1.0
""")

    patch(os.path.join(dir, "libs/demo"), """diff --git a/model/_init.cf b/model/_init.cf
index 2c18127..74f1040 100644
--- a/model/_init.cf
+++ b/model/_init.cf
@@ -180,8 +180,8 @@ implementation openstack for Iaas:
 
     self.provider.network = vm::Network(name=param::one("network_name", "demo::OpenStackForm"))
 
-    self.provider.image_id = "2f3f62f7-e707-4f98-8a32-b2546144a98b"
-    self.provider.image_os = redhat::fedora23
+    self.provider.image_id = "ca079514-52bf-4f11-832a-a5ee783349b1"
+    self.provider.image_os = redhat::fedora24
     self.provider.image_key = demo::wouter_key
 
     self.provider.small_flavor = "c1m1"
diff --git a/templates/user_data.tmpl b/templates/user_data.tmpl
index 190c236..8a1438b 100644
--- a/templates/user_data.tmpl
+++ b/templates/user_data.tmpl
@@ -3,17 +3,12 @@
 hostname {{ name }}
 setenforce 0
 
+dnf copr enable bartvanbrabant/inmanta -y
+
 cat > /etc/yum.repos.d/inmanta.repo <<EOF
-[config]
 [inmanta]
 name=Inmanta
-baseurl=https://packages.inmanta.com/rpms/inmanta/{{provider.branch}}/fedora/
-enabled=1
-gpgcheck=0
-
-[inmanta-deps]
-name=Inmanta deps
-baseurl=https://packages.inmanta.com/rpms/deps/fedora/
+baseurl=https://people.cs.kuleuven.be/~wouter.deborger/repo/
 enabled=1
 gpgcheck=0
 EOF

""")


def run_test(auth=False, ssl=False, purge_env=False, purge_project=False):
    with Server("/tmp/autotest/server", "172.17.3.106", auth=auth, ssl=ssl) as server:
        connection = Connection("172.17.3.106", auth, ssl)
        wait_async(connection)

        env = Environment(connection, "autotest", "demo", purge=purge_env)
        run_async(env.init)

        setup(env, purge_project)
        LOGGER.info("Waiting 30s for service to become active")
        sleep(30)
        verify_endpoints(env)
        test_restore(env)
        LOGGER.info("Breaking it down")
        #run_async(env.purge)
        LOGGER.info("Success")

if __name__ == '__main__':
    run_test(purge_env=False, purge_project=False)
