"""
Copyright 2019 Inmanta

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
import base64
import json
import logging
import os
import pathlib
import time
from functools import partial

import jwt
import pytest
import tornado
from tornado import web

import requests
from inmanta import config, const
from inmanta.protocol.auth import auth
from inmanta.server.protocol import Server
from utils import log_contains


def test_jwt_create(inmanta_config):
    """
    Test creating, signing and verifying JWT with HS256 from the configuration
    """
    jot = auth.encode_token(["api"])
    payload, _ = auth.decode_token(jot)

    assert "api" in payload["urn:inmanta:ct"]

    # test creating an idempotent token
    jot1 = auth.encode_token(["agent"], idempotent=True)
    jot3 = auth.encode_token(["agent"])
    time.sleep(1)
    jot2 = auth.encode_token(["agent"], idempotent=True)
    jot4 = auth.encode_token(["agent"])
    assert jot1 == jot2
    assert jot3 != jot4
    assert jot1 != jot3
    assert jot2 != jot3


class PKHandler(web.RequestHandler):
    def get(self):
        public_key = {
            "keys": [
                {
                    "kid": "NMROYvAmygR5zzmtYXgmCbJd8cXHcvAtx_o-JxJNPoQ",
                    "kty": "RSA",
                    "alg": "RS256",
                    "use": "sig",
                    "n": "oA7zi9u230-e3atV4rW9oI6z3ea_rViKlBTqq4_v9E-PK47yPpUvnHH9eJrKBXcuX-cVO2pSmDQ65nAzEaobjBU8XPtm3sceY1GsC"
                    "cP4Uo7gEbqLxsaqN1WUt1tnbV10wEbZzHmtAW_J_J5wlIB696ceEdwxNyj3Zscq15QIMsahDmV54fvwussuPgNhd0t4ng9BzaW-kG"
                    "2-Z80blyxN3fUbXX1JRMOiX4a7W_UXN5Q9B4kE9vlqAm30FnhYvLLqKh-DFvxq49dbYTWR-pJSFkjRMD6u1MUzKQEmOLYTnDX42zA"
                    "rTVhbvQl7OnW-OXtwx9zVqiQIIqt5IQgZQ7PfwQ",
                    "e": "AQAB",
                }
            ]
        }

        self.write(json.dumps(public_key))


@pytest.fixture(scope="function")
async def jwks(unused_tcp_port):
    http_app = web.Application([(r"/auth/realms/inmanta/protocol/openid-connect/certs", PKHandler)])
    server = tornado.httpserver.HTTPServer(http_app)
    server.bind(unused_tcp_port)
    server.start()
    yield server

    server.stop()
    await server.close_all_connections()


async def test_validate_rs256(jwks, tmp_path):
    """
    Test that inmanta can download a rs256 public key
    """
    port = str(list(jwks._sockets.values())[0].getsockname()[1])
    config_file = os.path.join(tmp_path, "auth.cfg")
    with open(config_file, "w+", encoding="utf-8") as fd:
        fd.write("""
[auth_jwt_default]
algorithm=HS256
sign=true
client_types=agent,compiler
key=eciwliGyqECVmXtIkNpfVrtBLutZiITZKSKYhogeHMM
expire=0
issuer=https://localhost:8888/
audience=https://localhost:8888/

[auth_jwt_keycloak]
algorithm=RS256
sign=false
client_types=api
issuer=https://localhost:{0}/auth/realms/inmanta
audience=sodev
jwks_uri=http://localhost:{0}/auth/realms/inmanta/protocol/openid-connect/certs
validate_cert=false
""".format(port))

    config.Config.load_config(config_file)

    cfg_list = await asyncio.get_event_loop().run_in_executor(None, auth.AuthJWTConfig.list)
    assert len(cfg_list) == 2


async def test_auth_jwt_environment_variables(jwks, tmp_path, monkeypatch, caplog):
    """
    Test that we can set auth jwt config via environment variables and that it behaves accordingly and is validated.
    """
    port = str(list(jwks._sockets.values())[0].getsockname()[1])
    config_file = os.path.join(tmp_path, "auth.cfg")
    with open(config_file, "w+", encoding="utf-8") as fd:
        # Wrong/incomplete config
        fd.write("""
[auth_jwt_default]
sign=false
client_types=agent,compiler
key=eciwliGyqECVmXtIkNpfVrtBLutZiITZKSKYhogeHMM
expire=0
issuer=https://localhost:8888/
audience=https://localhost:8888/

""")

    config.Config.load_config(config_file)

    # Add missing config via environment variable
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}DEFAULT_ALGORITHM", "HS256")
    # Overwrite config via environment variable
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}DEFAULT_SIGN", "true")
    # Add new config section with every possible config
    new_config = "MY_CONFIG_"
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}ALGORITHM", "RS256")
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}SIGN", "false")
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}CLIENT_TYPES", "api")
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}ISSUER", f"https://localhost:{port}/auth/realms/inmanta")
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}AUDIENCE", "sodev")
    monkeypatch.setenv(
        f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}JWKS_URI",
        f"http://localhost:{port}/auth/realms/inmanta/protocol/openid-connect/certs",
    )
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}VALIDATE_CERT", "false")
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}EXPIRE", "20")
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}JWT_USERNAME_CLAIM", "my-claim")
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}JWKS_REQUEST_TIMEOUT", "40.5")
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}KEY", "my-key")

    cfg_list = await asyncio.get_event_loop().run_in_executor(None, auth.AuthJWTConfig.list)
    assert len(cfg_list) == 2
    cfg = auth.AuthJWTConfig.get("default")
    assert cfg.algo == "HS256"
    assert cfg.sign is True

    cfg = auth.AuthJWTConfig.get("my_config")
    assert cfg.algo == "RS256"
    assert cfg.audience == "sodev"
    assert cfg.client_types == ["api"]
    assert cfg.expire == 20
    assert cfg.issuer == "https://localhost:{0}/auth/realms/inmanta".format(port)
    assert cfg.jwks_uri == "http://localhost:{0}/auth/realms/inmanta/protocol/openid-connect/certs".format(port)
    assert cfg.jwt_username_claim == "my-claim"
    assert cfg.sign is False
    assert cfg.validate_cert is False
    assert cfg._config.getfloat("jwks_request_timeout") == 40.5
    # Not sure if this key field is used
    assert cfg._config["key"] == "my-key"

    # Test what happens when you submit a wrong option
    config.Config.load_config(config_file)
    wrong_env_var = f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}WRONG_OPTION"
    monkeypatch.setenv(wrong_env_var, "true")

    with caplog.at_level(logging.WARNING):
        await asyncio.get_event_loop().run_in_executor(None, auth.AuthJWTConfig.list)
        log_contains(
            caplog,
            "inmanta.protocol.auth.auth",
            logging.WARNING,
            f"Found the following environment variable {wrong_env_var} with the {auth.ENV_AUTH_JWT_PREFIX} prefix",
        )

    monkeypatch.delenv(f"{auth.ENV_AUTH_JWT_PREFIX}{new_config}WRONG_OPTION")

    config.Config.load_config(config_file)
    monkeypatch.setenv(f"{auth.ENV_AUTH_JWT_PREFIX}OTHER_CONFIG_ALGORITHM", "HS256")

    with pytest.raises(
        ValueError,
        match="client_types is a required option for auth_jwt_other_config",
    ):
        await asyncio.get_event_loop().run_in_executor(None, auth.AuthJWTConfig.list)


class SlowHandler(web.RequestHandler):
    async def get(self):
        await asyncio.sleep(5)
        self.write(json.dumps({"keys": "not only slow, but also invalid"}))


@pytest.fixture(scope="function")
async def slow_jwks(unused_tcp_port):
    http_app = web.Application([(r"/auth/realms/inmanta/protocol/openid-connect/certs", SlowHandler)])
    server = tornado.httpserver.HTTPServer(http_app)
    server.bind(unused_tcp_port)
    server.start()
    yield server

    server.stop()
    await server.close_all_connections()


async def test_rs256_invalid_config_timeout(tmp_path, slow_jwks):
    """
    Test that an error is raised when the timeout to download the rs256 public key is exceeded
    """
    port = str(list(slow_jwks._sockets.values())[0].getsockname()[1])
    config_file = os.path.join(tmp_path, "auth.cfg")
    with open(config_file, "w+", encoding="utf-8") as fd:
        fd.write("""
[auth_jwt_keycloak]
algorithm=RS256
sign=false
client_types=api
issuer=https://localhost:{0}/auth/realms/inmanta
audience=sodev
jwks_uri=http://localhost:{0}/auth/realms/inmanta/protocol/openid-connect/certs
jwks_request_timeout=0.1
validate_cert=false
""".format(port))

    config.Config.load_config(config_file)
    with pytest.raises(ValueError):
        await asyncio.get_event_loop().run_in_executor(None, partial(auth.AuthJWTConfig.get, "auth_jwt_keycloak"))


@pytest.mark.parametrize("enable_auth", [True])
async def test_customer_header_user(tmp_path: pathlib.Path, server: Server) -> None:
    """Test using custom header and users"""
    port = config.Config.get("client_rest_transport", "port")
    config_file = tmp_path / "auth.cfg"
    with open(config_file, "w+", encoding="utf-8") as fd:
        fd.write("""
[server]
auth=true
auth_additional_header=Jwt-Assertion

[auth_jwt_test]
algorithm=HS256
sign=true
client_types=agent,compiler
key=eciwliGyqECVmXtIkNpfVrtBLutZiITZKSKYhogeHMM
expire=0
issuer=https://localhost:8888/
audience=https://localhost:8888/

[auth_jwt_name]
algorithm=HS256
client_types=agent,compiler
key=eciwliGyqECVmXtIkNpfVrtBLutZiITZKSKYhogeHMM
expire=0
issuer=https://example.com:8888/
audience=abcdef
jwt_username_claim=name
""")

    # Make sure the config starts from a clean slate
    config.Config.load_config(str(config_file))
    config.Config.set("client_rest_transport", "port", str(port))

    # load and parse
    cfg = auth.AuthJWTConfig.get("test")
    assert cfg

    cfg = auth.AuthJWTConfig.get("name")
    assert cfg

    # Test authentication with custom token header
    payload: dict[str, object] = {
        "iss": cfg.issuer,
        "aud": [cfg.audience],
        const.INMANTA_URN + "ct": "api",
        "name": "test-user",
    }
    token = jwt.encode(payload=payload, key=cfg.key, algorithm=cfg.algo)

    def get() -> requests.Response:
        return requests.get(f"http://localhost:{port}/api/v2/current_user", headers={"Jwt-Assertion": token})

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, get)
    response.raise_for_status()

    assert response.json()["data"]["username"] == "test-user"
