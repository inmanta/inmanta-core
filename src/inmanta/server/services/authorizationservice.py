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
import logging
import tornado import httpclient
import asyncio
import asyncio.subprocess
import time
from importlib.resources import files

from inmanta.server import protocol
from inmanta import server, const

LOGGER = logging.getLogger(__name__)

class AuthorizationSlice(protocol.ServerSlice):

    def __init__(self) -> None:
        super().__init__(server.SLICE_AUTHORIZATION)
        self._opa_process = OpaServer()

    async def start(self) -> None:
        await super().start()
        await self._opa_process.start()

    async def stop(self) -> None:
        await super().stop()
        await self._opa_process.stop()

    def get_depended_by(self) -> list[str]:
        return [SLICE_TRANSPORT]


class OpaServer:

    def __init__() -> None:
        self.process: asyncio.subprocess.Process = None

    async def start(self) -> None:
        # TODO: Setup location policy
        # TODO: Add configuration options for opa server???
        #       -> port number
        # TODO: What about logging?
        #       -> pipe logs to server and emit using a specific logger so that
        #          user can write a logging config.
        #       -> Write to a fixes file based on a config option.
        opa_binary = str(files('inmanta.opa').joinpath('opa').absolute())
        self.process = await asyncio.create_subprocess_exec(
            opa_binary,
            "run",
            "--server",
            "--addr",
            "127.0.0.1:8181",
            "--log-format",
            "text",
            "--log-level",
            "debug",
            "policy.rego",
            stdout=None,
            stderr=None,
        )
        await self._wait_until_opa_server_is_up()

    async def _wait_until_opa_server_is_up() -> None:
        client = httpclient.AsyncHTTPClient()
        server_is_up = False
        now: float = time.time()
        while not server_is_up and (time.time() - now) < const.POLICY_ENGINE_STARTUP_TIMEOUT:
            try:
                await client.fetch("http://127.0.0.1:8181/health?plugins&bundles")
            except httpclient.HTTPError:
                await asyncio.sleep(0.1)
            else:
                server_is_up = True
        if not server_is_up:
            # TODO: Add reference to logs
            raise Exception(f"Timeout: Policy engine didn't start in {const.POLICY_ENGINE_STARTUP_TIMEOUT} seconds.")

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
