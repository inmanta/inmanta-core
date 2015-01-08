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

from impera.agent import Agent
from impera.export import Exporter, Offline
from impera.compiler.main import Compiler
from impera.execute import scheduler

import time
import sys
import subprocess

from impera.deploy import deploy
from impera.resources import Resource

import logging
LOGGER = logging.getLogger()

ARGS = [
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "StrictHostKeyChecking=no",
    "-o", "PreferredAuthentications=publickey",
    "-tt"
]


def bootstrap(config):
    """
        Bootstrap Impera on a remote server by provisioning a VM, configuring it
        and starting the Impera server there.
    """
    console = logging.StreamHandler()
    LOGGER.addHandler(console)
    LOGGER.setLevel(logging.INFO)

    root_scope = compile_model(config)

    mgmt_server = get_mgmt_server_from_model(root_scope)

    # provision the mgmt server
    iaas_agent = Agent(config, False, mgmt_server.iaas.name, offline=True, deploy=True)
    export = Exporter(config)
    export.run(root_scope, offline=True)

    mgmt_vm_resource = Resource.get_resource(mgmt_server)
    iaas_agent.update(mgmt_vm_resource)

    print("Bootstrapping IaaS config and booting management server")
    while iaas_agent._queue.size() > 0:
        iaas_agent.deploy_config()

    # wait for the vm to come online get its ip
    print("Waiting for %s to become available" % mgmt_server.name)
    facts = None
    while facts is None:
        all_facts = iaas_agent.get_facts(mgmt_vm_resource)
        for vm_key in all_facts.keys():
            if vm_key == mgmt_vm_resource.id.resource_str() and "ip_address" in all_facts[vm_key]:
                facts = all_facts[vm_key]

        if facts is None:
            print("No response, waiting 5s for retry")
            time.sleep(5)

    # wait for the server to respond to ssh
    while True:
        result = run("/usr/bin/ssh", ARGS + ["ec2-user@" + facts["ip_address"], "echo 'OK'"])
        if result[0] == "OK":
            break
        else:
            time.sleep(5)

    # now add our ssh key to the root user
    deploy_key(facts["ip_address"], mgmt_vm_resource.key_value)

    # now recompile the model for the mgmt server and do a remote deploy
    Offline.get().set_facts(str(mgmt_vm_resource.id.resource_str()), facts)
    root_scope = compile_model(config)
    deploy(config, root_scope, remote=mgmt_server.name, dry_run=False, ip_address=facts["ip_address"])

    # # now boot all other servers, these are already available in the root_scope of the previous compile
    servers = set(root_scope.get_variable("Host", ["std"]).value)
    vm_servers = []
    for server in servers:
        vm_resource = Resource.get_resource(server)
        if vm_resource is not None:
            vm_servers.append(vm_resource)
            iaas_agent.update(vm_resource)

    print("Booting all other servers")
    print(vm_servers)
    while iaas_agent._queue.size() > 0:
        iaas_agent.deploy_config()

    # collect facts about all server
    print("Waiting for servers to become available")
    facts = {}
    while len(vm_servers) > len(facts):
        for vm in vm_servers:
            if vm.id.resource_str() not in facts:
                all_facts = iaas_agent.get_facts(vm)

                for vm_key in all_facts.keys():
                    if vm_key not in facts and "ip_address" in all_facts[vm_key]:
                        Offline.get().set_facts(vm_key, all_facts[vm_key])
                        facts[vm_key] = all_facts[vm_key]

        if len(vm_servers) > len(facts):
            print("No response, waiting 5s for retry")
            time.sleep(5)

    # now recompile the model once again with all facts and deploy to all servers
    root_scope = compile_model(config)

    # wait for the server to come online, deploy the ssh key and deploy the config
    print("Waiting for the server to come online, add our key to the root user and deploy the configuration")
    vm_todo = list(vm_servers)
    while len(vm_todo) > 0:
        for vm in list(vm_todo):
            ip = facts[vm.id.resource_str()]["ip_address"]

            result = run("/usr/bin/ssh", ARGS + ["ec2-user@" + ip, "echo 'OK'"])
            if result[0] == "OK":
                print("%s up" % vm.id.attribute_value)
                deploy_key(ip, vm.key_value)
                deploy(config, root_scope, remote=vm.name, dry_run=False, ip_address=ip)
                print("%s done" % vm.id.attribute_value)
                vm_todo.remove(vm)

        time.sleep(5)

    # now a final run with bootstrap off
        # now recompile the model once again with all facts and deploy to all servers
    root_scope = compile_model(config, bootstrap="false")

    # wait for the server to come online, deploy the ssh key and deploy the config
    print("Deploying final non-bootstrap configuration")
    vm_todo = list(vm_servers)
    for vm in list(vm_todo):
        ip = facts[vm.id.resource_str()]["ip_address"]

        deploy(config, root_scope, remote=vm.name, dry_run=False, ip_address=ip)
        vm_todo.remove(vm)


def deploy_key(ip, key):
        run("/usr/bin/ssh", ARGS + ["ec2-user@" + ip, ('echo "%s" > /tmp/key.pub; sudo mv /tmp/key.pub ' +
                                                       '/root/.ssh/authorized_keys; sudo chown root:root ' +
                                                       '/root/.ssh/authorized_keys; sudo chmod 600 /root/.ssh/authorized_keys')
                                    % key])


def get_mgmt_server_from_model(root_scope):
    try:
        mgmt_server = root_scope.get_variable("ManagementServer", ["vm"]).value
    except Exception:
        print("The vm module is not loaded or does not contain the definition of ManagementServer")
        return

    if len(mgmt_server) == 0:
        print("No management server was defined, cannot bootstrap without it.")
        return

    elif len(mgmt_server) > 1:
        print("Only one management server is supported by the bootstrap command")
        return

    return mgmt_server[0]


def run(command, arguments=[]):
    """
        Execute a command with the given argument and return the result
    """
    cmds = [command] + arguments
    print(" ".join(cmds))

    result = subprocess.Popen(cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    data = result.communicate()

    return (data[0].strip().decode("utf-8"), data[1].strip().decode("utf-8"))


def compile_model(config, bootstrap="true"):
    """
        Compile the configuration model
    """
    config["config"]["offline"] = "true"
    config["config"]["bootstrap"] = bootstrap

    libs = config.get("config", "lib-dir").split(":")
    compiler = Compiler(config, libs)

    graph = compiler.graph
    statements = compiler.compile()
    sched = scheduler.Scheduler(graph)
    success = sched.run(compiler, statements)

    if not success:
        sys.stderr.write("Unable to execute all statements.\n")
        sys.exit()

    return graph.root_scope
