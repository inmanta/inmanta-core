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
import os
import logging
import tornado import httpclient
import asyncio
import asyncio.subprocess
import subprocess
import time
from importlib.resources import files
import json

from inmanta.server import protocol
from inmanta import server, const, config
from inmanta.protocol.auth import decorators
from tornado.simple_httpclient import SimpleAsyncHTTPClient
from tornado.httpclient import HTTPRequest, HTTPError

LOGGER = logging.getLogger(__name__)

policy_file = Option("policy-engine", "policy-file", "/etc/inmanta/authorization/policy.rego", "File defining the authorization policy.", is_str)
policy_engine_bind_address = Option("policy-engine", "bind-address", "127.0.0.1", "Address on which the policy engine will listen for incoming connections.", is_str)
policy_engine_bind_port = Option("policy-engine", "bind-port", 8181, "Port on which the policy engine will listen for incoming connections.", is_int)
policy_engine_log = Option("logging", "policy-engine", "/var/log/inmanta/policy_engine.log", "Path to the log file of the policy engine.", is_str)


class AuthorizationSlice(protocol.ServerSlice):

    def __init__(self) -> None:
        super().__init__(server.SLICE_AUTHORIZATION)
        state_dir = await self._initialize_storage()
        self._opa_process = OpaServer(state_dir)

    async def _initialize_storage() -> str:
        """
        Make sure the required directories exist in the state directory for the policy engine.
        """
        state_dir = config.state_dir.get()
        policy_engine_state_dir = os.path.join(state_dir, "policy_engine")
        os.makedirs(policy_engine_state_dir, exist_ok=True)
        return policy_engine_state_dir

    async def start(self) -> None:
        await super().start()
        await self._opa_process.start()

    async def stop(self) -> None:
        await super().stop()
        await self._opa_process.stop()

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]

    def evaluate_policy(input_data: dict[str, object]) -> bool:
        """
        Return True iff the policy evaluates to True.

        Raises an exception if the policy cannot be evaluated.
        """
        client = SimpleAsyncHTTPClient()
        policy_engine_addr = self._opa_process.get_addr_policy_engine()
        request = HTTPRequest(
            url=f"http://{policy_engine_addr}/v1/data/policy/allowed",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=input_data,
        )
        try:
            response = await client.fetch(request)
        except HTTPError:
            LOGGER.exception("Failed to evaluate authorization policy for %s.", input_data)
            raise Exception("Failed to evaluate authorization policy.")
        else:
            if reponse.code != 200:
                LOGGER.error("Failed to evaluate authorization policy for %s.", input_data)
                raise Exception("Failed to evaluate authorization policy.")
            response_body = json.load(response.body.decode())
            return "result" in response_body and response_body["result"] is True


class OpaServer:

    def __init__(state_dir: str) -> None:
        self._state_dir = state_dir
        self.process: asyncio.subprocess.Process = None

    async def get_addr_policy_engine() -> str:
        return f"{policy_engine_bind_address.get()}:{policy_engine_bind_port.get()}",

    async def start(self) -> None:
        # Write data to state directory
        data_file = os.path.join(self._state_dir, "data.json")
        data = decorators.AuthorizationMetadata.get_open_policy_agent_data()
        with open(data_file, "w") as fh:
            json.dump(data, fh)

        # Start policy engine
        opa_binary = str(files('inmanta.opa').joinpath('opa').absolute())
        log_file_handle = None
        try:
            log_file_handle = open(policy_engine_log.get(), "wb+")
            self.process = await asyncio.create_subprocess_exec(
                opa_binary,
                "run",
                "--server",
                "--addr",
                await self.get_addr_policy_engine(),
                "--log-format",
                "text",
                "--log-level",
                "debug",
                data_file,
                policy_file.get(),
                stdout=log_file_handle,
                stderr=subprocess.STDOUT,
            )
        finally:
            if log_file_handle is not None:
                log_file_handle.close()
        await self._wait_until_opa_server_is_up()

    async def _wait_until_opa_server_is_up() -> None:
        client = httpclient.AsyncHTTPClient()
        server_is_up = False
        now: float = time.time()
        policy_engine_addr = await self.get_addr_policy_engine()
        health_endpoint = "http://{policy_engine_addr}/health?plugins&bundles"
        while not server_is_up and (time.time() - now) < const.POLICY_ENGINE_STARTUP_TIMEOUT:
            try:
                await client.fetch(health_endpoint)
            except httpclient.HTTPError:
                await asyncio.sleep(0.1)
            else:
                server_is_up = True
        if not server_is_up:
            raise Exception(
                f"Timeout: Policy engine didn't start in {const.POLICY_ENGINE_STARTUP_TIMEOUT} seconds."
                f" Please see {policy_engine_log.get()} for more information."
            )

    async def stop(self) -> None:
        if self.process.returncode is not None:
            # Process already terminated
            self.process = None
            return
        self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=const.POLICY_ENGINE_GRACE_HARD)
        except TimeoutError:
            LOGGER.warning("Policy engine didn't terminate in %d seconds. Killing it.", const.POLICY_ENGINE_GRACE_HARD)
            self.process.kill()
        self.process = None
