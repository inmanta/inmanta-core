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

from concurrent import futures
from collections import defaultdict
import os
import sys
import time

from impera import methods
from impera import protocol
from impera.agent import Agent
from impera.compiler import do_compile
from impera.config import Config
from impera.export import Exporter
from impera.module import Project
from impera.server import Server


def deploy_ready(client, host, version):
    result = client.call(methods.VersionMethod, operation="GET", id=version)

    total = len([x for x in result.result["resources"] if x["agent"] == host])
    ready = len([x for x in result.result["resources"] if x["agent"] == host and x["updated"]])
    if total > 0:
        msg = "%s of %s -> %d%%" % (ready, total, 100 * ready / total)
        printl(msg + "\b" * len(msg))

    if ready == total:
        status = defaultdict(lambda: 0)
        for res in result.result["resources"]:
            if res["agent"] == host:
                status[res["status"]] += 1

        print("\nStatus report:")
        for key in sorted(status.keys()):
            print("\t%s: %d" % (key, status[key]))

    return ready < total


def printl(msg):
    print(msg, end="")
    sys.stdout.flush()


def create_report(client, changes):
    report = "\nDry run change report:\n\n"
    res_ids = sorted(changes.keys())
    for r_id in res_ids:
        change = changes[r_id]
        report += "\033[1mResource %s\033[0m\n" % r_id

        for attr, values in change["changes"].items():
            if attr == "hash":
                # get a diff
                result = client.call(methods.FileDiff, a=values[0], b=values[1])
                report += "  \033[1mfile content:\033[0m\n"
                report += result.result + "\n"

            else:
                report += "\033[1mattribute %s\033[0m:\n" % attr
                report += "  \033[1mfrom:\033[0m %s\n" % values[0]
                report += "  \033[1mto  :\033[0m %s\n" % values[1]

        report += "\n"

    print(report)


def deploy(agentname=None, dry_run=True, ip_address=None, list_agents=False):
    protocol.Transport.offline = True
    protocol.DirectTransport.connections = [("client", "server"), ("server_client", "agent"), ("agent_client", "server")]

    Config.get().set("config", "state-dir", os.path.join(Project.get().project_path, "state"))

    # start the agent and a management server and only use direct transports
    printl("Starting embedded agent and server ")
    executor = futures.ThreadPoolExecutor(max_workers=2)

    server = Server(code_loader=False)
    server_future = executor.submit(server.start)

    agent = Agent(remote=ip_address, hostname=agentname, code_loader=False)
    agent_future = executor.submit(agent.start)
    print("done")

    client = None
    try:
        # compile the configuration model
        printl("Loading configuration modules ")
        Project.get().verify()
        print("done")

        export = Exporter()

        printl("Deploying new version of plug-in code ")
        export.deploy_code()
        print("done")

        printl("Compiling the configuration model ")
        model = do_compile()
        print("done")

        printl("Exporting the configuration model to the server ")
        version, resources = export.run(model)
        print("done")

        if not list_agents:
            printl("Deploying changes of version %s in " % version)
            if dry_run:
                printl("dry run mode ")
            else:
                printl("normal mode ")

            client = protocol.Client("client", "client", [protocol.DirectTransport])
            client.start()
            client.call(methods.DeployVersion, version=version, dry_run=dry_run)

            while deploy_ready(client, agentname, version):
                time.sleep(1)

            # report changes
            result = client.call(methods.VersionMethod, operation="GET", id=version)
            resources = [x for x in result.result["resources"] if x["agent"] == agentname]

            changes = {}
            for resource in resources:
                rsv_id = "%s,v=%s" % (resource["id"], version)
                result = client.call(methods.ResourceMethod, id=rsv_id)
                if len(result.result["changes"]) > 0:
                    changes[resource["id"]] = result.result

            print("")
            if len(changes) > 0:
                create_report(client, changes)

        else:
            agents = set()
            for res in resources.keys():
                if res.agent_name not in agents:
                    agents.add(res.agent_name)

            print("Agents available in model:")
            for a in agents:
                print("- %s" % a)

    finally:
        # clean up
        printl("Ready, cleaning up ")

        if client is not None:
            client.stop()

        server.stop()
        server_future.cancel()

        agent.stop()
        agent_future.cancel()
        print("done")
