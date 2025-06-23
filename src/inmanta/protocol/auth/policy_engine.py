"""
Copyright 2025 Inmanta

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

import asyncio
import asyncio.subprocess
import json
import logging
import os
import subprocess
import time
from typing import Mapping

from tornado import httpclient
from tornado.httpclient import HTTPRequest

from inmanta import config, const, data
from inmanta import tornado as inmanta_tornado
from inmanta import util
from inmanta.protocol import common

LOGGER = logging.getLogger(__name__)

opa_log_level_values = ["debug", "info", "error"]


def is_opa_log_level(value: str) -> str:
    value = value.lower()
    if value not in opa_log_level_values:
        raise ValueError(f"Invalid value {value}. Valid values: {opa_log_level_values}")
    return value


policy_file = config.Option(
    "policy_engine", "policy-file", "/etc/inmanta/authorization/policy.rego", "File defining the access policy.", config.is_str
)
policy_engine_log_level = config.Option(
    "policy_engine",
    "log-level",
    "error",
    f"The log level used by the policy engine. Valid values: {opa_log_level_values}",
    is_opa_log_level,
)
path_opa_executable = config.Option(
    "policy_engine",
    "executable",
    "/opt/inmanta/bin/opa",
    "Path to the executable that runs the Open Policy Agent.",
    config.is_str,
)


class PolicyEngine:
    """
    A class representing an Open Policy Agent server that listens on a unix socket.

    The implementation of this class assumes only one instance of this class exists at any point in time.
    """

    def __init__(self) -> None:
        self._state_dir: str = self._initialize_storage()
        self._policy_engine_log = os.path.join(config.log_dir.get(), "policy_engine.log")
        self._process: asyncio.subprocess.Process | None = None
        self.running = False
        # The OPA server will listen on this unix socket.
        self._socket_file = os.path.join(self._state_dir, "policy_engine.socket")
        # A virtual hostname that will be mapped to the unix socket by the custom tornado resolver.
        self._hostname = "policy_engine"
        inmanta_tornado.LoopResolverWithUnixSocketSuppport.register_unix_socket(self._hostname, self._socket_file)
        self._client = httpclient.AsyncHTTPClient()

    def _initialize_storage(self) -> str:
        """
        Make sure the required directories exist in the state directory for the policy engine.
        """
        state_dir = config.state_dir.get()
        policy_engine_state_dir = os.path.abspath(os.path.join(state_dir, "policy_engine"))
        os.makedirs(policy_engine_state_dir, exist_ok=True)
        log_dir = config.log_dir.get()
        os.makedirs(log_dir, exist_ok=True)
        return policy_engine_state_dir

    async def start(self) -> None:
        if not os.path.isfile(policy_file.get()):
            raise Exception(f"Access policy file {policy_file.get()} not found.")

        # Write data to state directory
        data_file = os.path.join(self._state_dir, "data.json")
        data: dict[str, object] = common.MethodProperties.get_open_policy_agent_data()
        with open(data_file, "w") as fh:
            json.dump(data, fh)

        # Start policy engine
        opa_executable = path_opa_executable.get()
        if not opa_executable:
            raise Exception(f"Config option {path_opa_executable.get_full_name()} was not set.")
        if not os.path.isfile(opa_executable):
            raise Exception(f"Config option {path_opa_executable.get_full_name()} doesn't point to a file: {opa_executable}.")
        log_file_handle = None
        try:
            log_file_handle = open(self._policy_engine_log, "wb+")
            self._process = await asyncio.create_subprocess_exec(
                opa_executable,
                "run",
                "--server",
                "--addr",
                f"unix://{self._socket_file}",
                "--unix-socket-perm",
                "600",
                "--log-format",
                "text",
                "--log-level",
                policy_engine_log_level.get(),
                data_file,
                policy_file.get(),
                stdout=log_file_handle,
                stderr=subprocess.STDOUT,
            )
        finally:
            if log_file_handle is not None:
                log_file_handle.close()
        await self._wait_until_opa_server_is_up()
        await self._synchronize_roles_to_db()
        self.running = True

    async def _wait_until_opa_server_is_up(self) -> None:
        now: float = time.time()
        health_endpoint = f"http://{self._hostname}/health?plugins&bundles"
        while True:
            try:
                await self._client.fetch(health_endpoint)
            except Exception as e:
                # Server is not yet up
                timeout_happened = (time.time() - now) >= const.POLICY_ENGINE_STARTUP_TIMEOUT
                if timeout_happened:
                    raise Exception(
                        f"Timeout: Policy engine didn't start in {const.POLICY_ENGINE_STARTUP_TIMEOUT} seconds."
                        f"\n\n{e}\n\n"
                        f"Please see {self._policy_engine_log} for more information."
                    )
                else:
                    await asyncio.sleep(0.1)
            else:
                # Server is up
                return

    async def stop(self) -> None:
        if self._process is None or self._process.returncode is not None:
            # Process didn't start or was already terminated.
            self._process = None
            self.running = False
            return

        self._process.terminate()
        try:
            await asyncio.wait_for(self._process.wait(), timeout=const.POLICY_ENGINE_GRACE_HARD)
        except TimeoutError:
            LOGGER.warning("Policy engine didn't terminate in %d seconds. Killing it.", const.POLICY_ENGINE_GRACE_HARD)
            self._process.kill()
            await self._process.wait()
        self._process = None
        self.running = False

    async def _evaluate_policy(
        self,
        query: str,
        error_message: str,
        input_data: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        """
        Perform a query on the policy engine and return the response.

        :param query: The query to execute.
        :param error_message: The error message to write to the log file of the server in case the query fails to execute.
        :param input_data: The input_data for the query.
        :return: The response body of the call to the policy engine or an empty dictionary if the query fails to execute.
        """
        body: str = json.dumps(input_data, default=util.api_boundary_json_encoder) if input_data is not None else ""
        request = HTTPRequest(
            url=f"http://{self._hostname}/v1/data/policy/{query}",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=body,
        )
        try:
            response = await self._client.fetch(request)
            if response.code != 200:
                LOGGER.error(
                    "% (query=%s, input_data=%s). See %s for more information.",
                    error_message,
                    query,
                    body,
                    self._policy_engine_log,
                )
                return {}
            return json.loads(response.body.decode())
        except Exception:
            LOGGER.exception(
                "% (query=%s, input_data=%s). See %s for more information.", error_message, query, body, self._policy_engine_log
            )
            return {}

    async def does_satisfy_access_policy(self, input_data: Mapping[str, object]) -> bool:
        """
        Return True iff the policy evaluates to True.
        """
        if not self.running:
            LOGGER.error("Policy engine is not running. Call OpaServer.start() first.")
            return False
        response = await self._evaluate_policy(
            query="allow", error_message="Failed to evaluate access policy", input_data=input_data
        )
        return "result" in response and response["result"] is True

    async def _get_roles(self) -> list[str]:
        """
        Return the roles defined in the access policy.
        """
        response = await self._evaluate_policy(query="roles", error_message="Failed to get roles from access policy.")
        if "result" not in response:
            # The policy didn't define any roles.
            return []
        roles = response["result"]
        if not isinstance(roles, list):
            raise Exception(f"roles defined in access policy must be a list, got: {roles}")
        for elem in roles:
            if not isinstance(elem, str):
                raise Exception(f"The list of roles defined in the access policy contains a non-string element: {elem}")
        return roles

    async def _synchronize_roles_to_db(self) -> None:
        """
        Make sure that the roles defined in the access policy are also present in the database.
        """
        roles = await self._get_roles()
        if not roles:
            return
        await data.Role.ensure_roles(roles)
