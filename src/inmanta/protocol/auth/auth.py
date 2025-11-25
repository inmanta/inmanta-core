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

import base64
import configparser
import json
import logging
import ssl
import time
from typing import Any, Mapping, MutableMapping, Optional, Sequence
from urllib import error, request

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

from inmanta import config, const
from inmanta.protocol import exceptions

claim_type = Mapping[str, str | bool | Sequence[str] | Mapping[str, str]]


def encode_token(
    client_types: list[str],
    environment: Optional[str] = None,
    idempotent: bool = False,
    expire: Optional[float] = None,
    custom_claims: Optional[Mapping[str, str | bool | Mapping[str, list[str]]]] = None,
) -> str:
    cfg = AuthJWTConfig.get_sign_config()
    if cfg is None:
        raise Exception("No JWT signing configuration available.")

    for ct in client_types:
        if ct not in cfg.client_types:
            raise Exception(
                f"The signing config does not support the requested client type {ct}. Only {cfg.client_types} are allowed."
            )

    payload: dict[str, Any] = {"iss": cfg.issuer, "aud": [cfg.audience], const.INMANTA_URN + "ct": ",".join(client_types)}

    if custom_claims:
        payload.update(custom_claims)

    if not idempotent:
        payload["iat"] = int(time.time())

        if cfg.expire > 0:
            payload["exp"] = int(time.time() + cfg.expire)
        elif expire is not None:
            payload["exp"] = int(time.time() + expire)

    if environment is not None:
        payload[const.INMANTA_URN + "env"] = environment

    return jwt.encode(payload=payload, key=cfg.key, algorithm=cfg.algo)


def decode_token(token: str) -> tuple[claim_type, "AuthJWTConfig"]:
    try:
        # First decode the token without verification
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        raise exceptions.Forbidden("Unable to decode provided JWT bearer token.")

    if "iss" not in payload:
        raise exceptions.Forbidden("Issuer is required in token to validate.")

    cfg = AuthJWTConfig.get_issuer(str(payload["iss"]))
    if cfg is None:
        raise exceptions.Forbidden("Unknown issuer for token")

    if "alg" not in header or not isinstance(header["alg"], str):
        raise exceptions.Forbidden("alg field is missing in jwt header or is not a valid string")

    alg = header["alg"].lower()
    if alg == "hs256":
        key = cfg.key
    elif alg == "rs256":
        if "kid" not in header or not isinstance(header["kid"], str):
            raise exceptions.Forbidden("kid is missing in jwt header or is not a valid string")
        kid = header["kid"]
        if kid not in cfg.keys:
            raise exceptions.Forbidden(
                "The kid provided in the token does not match a known key. Check the jwks_uri or try "
                "restarting the server to load any new keys."
            )

        key = cfg.keys[kid]
    else:
        raise exceptions.Forbidden("Algorithm %s is not supported." % alg)

    try:
        # copy the payload and make sure the type is claim_type
        decoded_payload: MutableMapping[str, str | bool | Sequence[str] | Mapping[str, str]] = {}
        unsupported = []
        for k, v in jwt.decode(token, key, audience=cfg.audience, algorithms=[cfg.algo]).items():
            match v:
                case str() | bool():
                    decoded_payload[k] = v
                case list():
                    for el in v:
                        if not isinstance(el, str):
                            raise exceptions.Forbidden(
                                "Only claims of type string or list of strings are supported. "
                                f"Element {el} in claim {k} is not a string."
                            )
                    decoded_payload[k] = v
                case dict():
                    decoded_payload[k] = dict(v)
                case _:
                    unsupported.append(k)

        if unsupported:
            logging.getLogger(__name__).debug(
                "Only claims of type string or list of strings are supported. %s are filtered out.", ", ".join(unsupported)
            )

        ct_key = const.INMANTA_URN + "ct"
        ct_value = str(payload.get(ct_key, "api"))
        decoded_payload[ct_key] = [x.strip() for x in ct_value.split(",")]
    except Exception as e:
        raise exceptions.Forbidden(*e.args)

    return decoded_payload, cfg


#############################
# auth
#############################
AUTH_JWT_PREFIX = "auth_jwt_"


class AuthJWTConfig:
    """
    Auth JWT configuration manager
    """

    sections: dict[str, "AuthJWTConfig"] = {}
    issuers: dict[str, "AuthJWTConfig"] = {}
    _config_successfully_loaded: bool = False

    validate_cert: bool
    key: bytes

    @classmethod
    def reset(cls) -> None:
        cls._config_successfully_loaded = False
        cls.sections = {}
        cls.issuers = {}

    @classmethod
    def _load_config_and_validate(cls) -> None:
        if cls._config_successfully_loaded:
            return

        try:
            cfg = config.Config.get_instance()
            prefix_len = len(AUTH_JWT_PREFIX)

            for config_section in cfg.keys():
                if config_section[:prefix_len] == AUTH_JWT_PREFIX:
                    name = config_section[prefix_len:]
                    if name not in cls.sections:
                        obj = cls(name, config_section, cfg[config_section])
                        cls.sections[name] = obj
                        if obj.issuer in cls.issuers:
                            raise ValueError("Only one configuration per issuer is supported")

                        cls.issuers[obj.issuer] = obj

            # Verify that only one has sign set to true
            sign = False
            for section in cls.sections.values():
                if section.sign:
                    if sign:
                        raise ValueError("Only one auth_jwt section may have sign set to true")
                    else:
                        sign = True

            if len(cls.sections.keys()) > 0 and not sign:
                raise ValueError("One auth_jwt section should have sign set to true")
        except Exception:
            # Make sure we don't have a partially loaded config.
            cls.reset()
            raise
        else:
            cls._config_successfully_loaded = True

    @classmethod
    def list(cls) -> list[str]:
        """
        Return a list of all defined auth jwt configurations. This method will load new sections if they were added
        since the last invocation.
        """
        cls._load_config_and_validate()
        return list(cls.sections.keys())

    @classmethod
    def get(cls, name: str) -> Optional["AuthJWTConfig"]:
        """
        Get the config with the given name
        """
        cls._load_config_and_validate()
        if name in cls.sections:
            return cls.sections[name]
        return None

    @classmethod
    def get_sign_config(cls) -> Optional["AuthJWTConfig"]:
        """
        Get the configuration with sign is true
        """
        cls._load_config_and_validate()
        for cfg in cls.sections.values():
            if cfg.sign:
                return cfg
        return None

    @classmethod
    def get_issuer(cls, issuer: str) -> Optional["AuthJWTConfig"]:
        """
        Get the config for the given issuer. Only when no auth config has been loaded yet, the configuration will be loaded
        again. For loading additional configuration, call list() first. This method is in the auth path for each API
        request.
        """
        cls._load_config_and_validate()
        if issuer in cls.issuers:
            return cls.issuers[issuer]
        return None

    def __init__(self, name: str, section: str, config: configparser.SectionProxy) -> None:
        self.name: str = name
        self.section: str = section
        self.keys: dict[str, bytes] = {}
        self._config: configparser.SectionProxy = config

        self.jwt_username_claim: str = "sub"
        self.expire: int = 0
        self.sign: bool = False
        self.issuer: str = "https://localhost:8888/"
        self.audience: str

        if "algorithm" not in config:
            raise ValueError("algorithm is required in %s section" % self.section)

        self.algo = config["algorithm"]
        self.validate_generic()

        if self.algo.lower() == "hs256":
            self.validate_hs265()
        elif self.algo.lower() == "rs256":
            self.validate_rs265()
        else:
            raise ValueError(f"Algorithm {self.algo} in {self.section} is not support ")

    def validate_generic(self) -> None:
        """
        Validate  and parse the generic options that are valid for all algorithms
        """
        if "sign" in self._config:
            self.sign = config.is_bool(self._config["sign"])

        if "client_types" not in self._config:
            raise ValueError("client_types is a required options for %s" % self.section)

        self.client_types = config.is_list(self._config["client_types"])
        for ct in self.client_types:
            if ct not in [client_type for client_type in const.ClientType]:
                raise ValueError(f"invalid client_type {ct} in {self.section}")

        if "expire" in self._config:
            self.expire = config.is_int(self._config["expire"])

        if "issuer" in self._config:
            self.issuer = config.is_str(self._config["issuer"])

        if "audience" in self._config:
            self.audience = config.is_str(self._config["audience"])
        else:
            self.audience = self.issuer

        if "jwt-username-claim" in self._config:
            if self.sign:
                raise ValueError(f"auth config {self.section} used for signing cannot use a custom claim.")
            self.jwt_username_claim = self._config["jwt-username-claim"]

    def validate_hs265(self) -> None:
        """
        Validate and parse HS256 algorithm configuration
        """
        if "key" not in self._config:
            raise ValueError(f"key is required in {self.section} for algorithm {self.algo}")

        self.key = base64.urlsafe_b64decode((self._config["key"] + "==").encode("ascii"))
        if len(self.key) < 32:
            raise ValueError("HS256 requires a key of 32 bytes (256 bits) or longer in " + self.section)

    def _load_public_key(self, e: str, n: str) -> bytes:
        def to_int(x: str) -> int:
            bs = base64.urlsafe_b64decode(x + "==")
            return int.from_bytes(bs, byteorder="big")

        ei = to_int(e)
        ni = to_int(n)
        numbers = RSAPublicNumbers(ei, ni)
        public_key = numbers.public_key(backend=default_backend())
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem

    def validate_rs265(self) -> None:
        """
        Validate and parse RS256 algorithm configuration
        """
        if "jwks_uri" not in self._config:
            raise ValueError("jwks_uri is required for RS256 based providers in section %s" % self.section)

        self.jwks_uri = self._config["jwks_uri"]

        if "validate_cert" in self._config:
            validate_cert = self._config.getboolean("validate_cert")
            # Make mypy happy
            assert validate_cert is not None
            self.validate_cert = validate_cert
        else:
            self.validate_cert = True

        ctx = None
        if not self.validate_cert:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        jwks_timeout = self._config.getfloat("jwks_request_timeout", 30.0)
        try:
            with request.urlopen(self.jwks_uri, timeout=jwks_timeout, context=ctx) as response:
                key_data = json.loads(response.read().decode("utf-8"))
        except error.URLError as e:
            # HTTPError is raised for non-200 responses; the response
            # can be found in e.response.
            raise ValueError(
                "Unable to load key data for %s using the provided jwks_uri %s. Got error: %s"
                % (self.section, self.jwks_uri, e.reason)
            )
        except Exception:
            # Other errors are possible, such as IOError.
            raise ValueError("Unable to load key data for %s using the provided jwks_uri." % self.section)

        for key in key_data["keys"]:
            self.keys[key["kid"]] = self._load_public_key(key["e"], key["n"])
