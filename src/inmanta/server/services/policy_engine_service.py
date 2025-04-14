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
from importlib.resources import files
from typing import Mapping

from tornado import httpclient
from tornado.httpclient import HTTPRequest
from tornado.simple_httpclient import SimpleAsyncHTTPClient

from inmanta import config, const, server, util
from inmanta.protocol.auth import decorators
from inmanta.server import protocol, config as server_config

LOGGER = logging.getLogger(__name__)

policy_file = config.Option(
    "policy-engine", "policy-file", "/etc/inmanta/authorization/policy.rego", "File defining the access policy.", config.is_str
)
policy_engine_bind_address = config.Option(
    "policy-engine",
    "bind-address",
    "127.0.0.1",
    "Address on which the policy engine will listen for incoming connections.",
    config.is_str,
)
policy_engine_bind_port = config.Option(
    "policy-engine", "bind-port", 8181, "Port on which the policy engine will listen for incoming connections.", config.is_int
)


class PolicyEngineSlice(protocol.ServerSlice):

    def __init__(self) -> None:
        super().__init__(server.SLICE_POLICY_ENGINE)
        self._opa_process = OpaServer()

    async def start(self) -> None:
        await super().start()
        if server_config.enforce_access_policy.get():
            await self._opa_process.start()

    async def stop(self) -> None:
        await super().stop()
        await self._opa_process.stop()

    def get_depended_by(self) -> list[str]:
        return [server.SLICE_TRANSPORT]

    async def does_satisfy_access_policy(self, input_data: Mapping[str, object]) -> bool:
        """
        Return True iff the policy evaluates to True.
        """
        if not server_config.enforce_access_policy.get():
            return True
        if not self._opa_process.running:
            raise Exception("Policy engine is not running. Call OpaServer.start() first.")
        client = SimpleAsyncHTTPClient()
        policy_engine_addr = await self._opa_process.get_addr_policy_engine()
        request = HTTPRequest(
            url=f"http://{policy_engine_addr}/v1/data/policy/allowed",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=json.dumps(input_data, default=util.api_boundary_json_encoder),
        )
        try:
            response = await client.fetch(request)
            if response.code != 200:
                LOGGER.error("Failed to evaluate access policy for %s.", input_data)
                return False
            response_body = json.loads(response.body.decode())
            return "result" in response_body and response_body["result"] is True
        except Exception:
            LOGGER.exception("Failed to evaluate access policy for %s.", input_data)
            return False


class OpaServer:

    def __init__(self) -> None:
        self.process: asyncio.subprocess.Process | None = None
        self.running = False

    async def get_addr_policy_engine(self) -> str:
        """
        Returns the "<host>:<port>" on which the policy engine should listen for incoming connections.
        """
        return f"{policy_engine_bind_address.get()}:{policy_engine_bind_port.get()}"

    def _initialize_storage(self) -> str:
        """
        Make sure the required directories exist in the state directory for the policy engine.
        """
        state_dir = config.state_dir.get()
        policy_engine_state_dir = os.path.join(state_dir, "policy_engine")
        os.makedirs(policy_engine_state_dir, exist_ok=True)
        return policy_engine_state_dir

    async def start(self) -> None:
        if not os.path.isfile(policy_file.get()):
            raise Exception(f"Access policy file {policy_file.get()} not found.")

        state_dir = self._initialize_storage()

        # Write data to state directory
        data_file = os.path.join(state_dir, "data.json")
        data = decorators.AuthorizationMetadata.get_open_policy_agent_data()
        with open(data_file, "w") as fh:
            json.dump(data, fh)

        # Start policy engine
        opa_binary = str(files("inmanta.opa").joinpath("opa").absolute())
        log_dir = config.log_dir.get()
        policy_engine_log = os.path.join(log_dir, "policy_engine.log")
        log_file_handle = None
        try:
            log_file_handle = open(policy_engine_log, "wb+")
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
        await self._wait_until_opa_server_is_up(policy_engine_log)
        self.running = True

    async def _wait_until_opa_server_is_up(self, policy_engine_log_file: str) -> None:
        client = httpclient.AsyncHTTPClient()
        now: float = time.time()
        policy_engine_addr = await self.get_addr_policy_engine()
        health_endpoint = f"http://{policy_engine_addr}/health?plugins&bundles"
        while True:
            try:
                await client.fetch(health_endpoint)
            except Exception as e:
                # Server is not yet up
                timeout_happened = (time.time() - now) >= const.POLICY_ENGINE_STARTUP_TIMEOUT
                if timeout_happened:
                    raise Exception(
                        f"Timeout: Policy engine didn't start in {const.POLICY_ENGINE_STARTUP_TIMEOUT} seconds."
                        f"\n\n{e}\n\n"
                        f"Please see {policy_engine_log_file} for more information."
                    )
                else:
                    await asyncio.sleep(0.1)
            else:
                # Server is up
                return

    async def stop(self) -> None:
        if self.process is None or self.process.returncode is not None:
            # Process didn't start or was already terminated.
            self.process = None
            self.running = False
            return
        self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=const.POLICY_ENGINE_GRACE_HARD)
        except TimeoutError:
            LOGGER.warning("Policy engine didn't terminate in %d seconds. Killing it.", const.POLICY_ENGINE_GRACE_HARD)
            self.process.kill()
        self.process = None
        self.running = False
