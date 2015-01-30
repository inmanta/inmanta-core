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

    This module contains a client to communicate with Impera agents and other
    services connected to the Impera message bus.
"""

import logging
import pprint
import time
import datetime
from collections import defaultdict

from impera import protocol, methods
from impera.resources import Id

LOGGER = logging.getLogger(__name__)


class Client(object):
    """
        A client to communicate with impera agents
    """
    def __init__(self, output=True):
        self.output = output
        self._client = protocol.Client("client", "client", [protocol.RESTTransport, protocol.AMQPTransport])
        self._client.start()

        while not self._client.all_transports_connected():
            time.sleep(0.1)

    def _report(self, message):
        """
            Report a message to the user
        """
        if self.output:
            print(message)

    def execute(self, cmd, args):
        """
            Execute the given command
        """
        if hasattr(self, cmd):
            method = getattr(self, cmd)
            method(*args)

        else:
            raise Exception("%s not implemented" % cmd)

    def on_status_reply(self, message):
        """
            A method called when a reply is received for a status request
        """
        LOGGER.info("Received a status reponse")

        if len(message) == 0:
            if message["code"] == 404:
                self._report("No resource found")
            else:
                self._report("No response with code: %d" % message["code"])

        else:
            self._report(pprint.pformat(message))

        self._stack["status"] = message

    def on_queue_reply(self, message):
        """
            A method called when a reply is received for a queue request
        """
        LOGGER.info("Received a queue response")

        self._report(pprint.pformat(message["queue"]))

        self._stack["queue"] = message["queue"]

    def on_info_reply(self, message):
        """
            A method called when a reply is received for an info request
        """
        LOGGER.info("Received an info reponse")
        self._stack["info"].append(message)

    def on_facts_reply(self, message):
        """
            A method called when a reply is received for a facts request
        """
        LOGGER.info("Received a facts reponse")

        if len(message) == 0:
            if message["code"] == 404:
                self._report("No resource found")
            else:
                self._report("No response with code: %d" % message["code"])

        else:
            facts = message["facts"]
            subject = message["subject"]

            if subject in facts:
                self._report(pprint.pformat(facts[subject]))

                self._stack["facts"] = facts[subject]

    def discover(self):
        """
            Send out a ping and print out a list of agents that responded
        """
        result = self._client.call(methods.PingMethod, destination="*", async=True)

        result.wait(timeout=5)
        if result.available():
            print("Agents discovered")
            for response in result.result:
                if response["role"] == "agent":
                    print("- %s" % response["nodename"])
                    for agent in response["end_point_names"]:
                        print("  . %s" % agent)
        else:
            print(".")

    def status(self, resource_id, timeout=10):
        """
            Check the state of a resource
        """
        self._report("Requesting status of %s" % resource_id)

        id_obj = Id.parse_id(resource_id)

        request = {"id": resource_id}
        topic = 'resources.%s.%s' % (id_obj.agent_name, id_obj.entity_type)

        self._mq_send(topic, "STATUS", request)

        self._stack["status"] = None

        stop = time.time() + timeout
        while self._stack["status"] is None and stop > time.time():
            time.sleep(0.1)

        return self._stack["status"]

    def facts(self, resource_id, timeout=10, wait=True):
        """
            Get facts about a resource
        """
        id_obj = Id.parse_id(resource_id)

        request = {"id": resource_id}
        topic = 'resources.%s.%s' % (id_obj.agent_name, id_obj.entity_type)
        self._mq_send(topic, "FACTS", request)

        self._stack["facts"] = None

        if wait:
            stop = time.time() + timeout
            while self._stack["facts"] is None and stop > time.time():
                time.sleep(0.1)

            return self._stack["facts"]

        return None

    def queue(self, agent):
        """
            Retrieve the current queue of a configuration agent
        """
        wait = 2
        self._stack["queue"] = None

        request = {"agent": agent}
        self._mq_send("control", "QUEUE", request)

        stop = time.time() + wait
        while self._stack["queue"] is None and stop > time.time():
            time.sleep(0.1)

    def info(self, agent):
        """
            Retrieve the current info of a configuration agent
        """
        wait = 2
        self._stack["info"] = []

        request = {"agent": agent}
        self._mq_send("control", "INFO", request)

        stop = time.time() + wait
        while self._stack["info"] is None and stop > time.time():
            time.sleep(0.1)

        agents = {}
        agent_list = []
        for response in self._stack["info"]:
            print(response)
            agent_id = ", ".join(response["source"])
            agents[agent_id] = response
            agent_list.append(agent_id)

    def dump(self, agent):
        """
            Dump the current runtime information
        """
        self._client.call(methods.DumpAgent, destination="host.agent.%s" % agent)

    def deploy(self):
        """
            Deploy the last available version
        """
        # get the list of available versions
        last_version = 0
        result = self._client.call(methods.VersionMethod, operation="GET")
        if "versions" in result.result:
            pks = {v["pk"]: v for v in result.result["versions"]}
            keys = sorted(pks.keys())
            if len(keys) > 0:
                last_version = pks[keys[-1]]
        else:
            print("Unable to retrieve available versions from the server.")
            return

        if last_version == 0:
            print("There are no version available for deployment.")
            return

        if last_version["deploy_started"] is None:
            print("Requesting the server to start deploy of version %s from %s" %
                  (last_version["pk"], datetime.datetime.fromtimestamp(int(last_version["pk"])).strftime("%Y-%m-%d %H:%M:%S")))

            self._client.call(methods.DeployVersion, version=last_version["pk"])

        else:
            print("Deploy of of version %s form %s already started" %
                  (last_version["pk"], datetime.datetime.fromtimestamp(int(last_version["pk"])).strftime("%Y-%m-%d %H:%M:%S")))

        result = self._client.call(methods.VersionMethod, operation="GET", id=last_version["pk"])
        total = result.result["total_resources"]
        deployed = 0
        while total > deployed:
            deployed = 0
            result = self._client.call(methods.VersionMethod, operation="GET", id=last_version["pk"])

            status = defaultdict(lambda: 0)
            for res in result.result["resources"]:
                status[res["status"]] += 1
                if res["status"] != "not handled":
                    deployed += 1

            print("Deployment progress")
            for k, v in status.items():
                print("\t%s:%s" % (k, v))

            print("\ttotal: %d" % total)

            time.sleep(2)


INSTANCE = None


def get_client():
    """
        Get a client instance
    """
    global INSTANCE
    if INSTANCE is None:
        INSTANCE = Client(output=False)

    return INSTANCE
