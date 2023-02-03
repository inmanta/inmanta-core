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

import base64
import json
import logging
import os
import re
import ssl
import sys
import uuid
import warnings
from collections import abc, defaultdict
from configparser import ConfigParser, Interpolation, SectionProxy
from typing import Callable, Dict, Generic, List, Optional, TypeVar, Union, overload
from urllib import error, request

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

from inmanta import const

LOGGER = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    return name.replace("_", "-")


def _get_from_env(section: str, name: str) -> Optional[str]:
    return os.environ.get(f"INMANTA_{section}_{name}".replace("-", "_").upper(), default=None)


class LenientConfigParser(ConfigParser):
    def optionxform(self, name: str) -> str:
        name = _normalize_name(name)
        return super(LenientConfigParser, self).optionxform(name)


class Config(object):
    __instance: Optional[ConfigParser] = None
    _config_dir: Optional[str] = None  # The directory this config was loaded from
    __config_definition: Dict[str, Dict[str, "Option"]] = defaultdict(lambda: {})

    @classmethod
    def get_config_options(cls) -> Dict[str, Dict[str, "Option"]]:
        return cls.__config_definition

    @classmethod
    def load_config(
        cls,
        min_c_config_file: Optional[str] = None,
        config_dir: Optional[str] = None,
        main_cfg_file: str = "/etc/inmanta/inmanta.cfg",
    ) -> None:
        """
        Load the configuration file
        """

        cfg_files_in_config_dir: List[str]
        if config_dir and os.path.isdir(config_dir):
            cfg_files_in_config_dir = sorted(
                [os.path.join(config_dir, f) for f in os.listdir(config_dir) if f.endswith(".cfg")]
            )
        else:
            cfg_files_in_config_dir = []

        local_dot_inmanta_cfg_files: List[str] = [os.path.expanduser("~/.inmanta.cfg"), ".inmanta", ".inmanta.cfg"]

        # Files with a higher index in the list, override config options defined by files with a lower index
        files: List[str]
        if min_c_config_file is not None:
            files = [main_cfg_file] + cfg_files_in_config_dir + local_dot_inmanta_cfg_files + [min_c_config_file]
        else:
            files = [main_cfg_file] + cfg_files_in_config_dir + local_dot_inmanta_cfg_files

        config = LenientConfigParser(interpolation=Interpolation())
        config.read(files)
        cls.__instance = config
        cls._config_dir = config_dir

    @classmethod
    def _get_instance(cls) -> ConfigParser:
        if cls.__instance is None:
            cls.load_config()

        return cls.__instance

    @classmethod
    def _reset(cls) -> None:
        cls.__instance = None
        cls._config_dir = None

    @overload
    @classmethod
    def get(cls) -> ConfigParser:
        ...

    @overload
    @classmethod
    def get(cls, section: str, name: str, default_value: Optional[str] = None) -> Optional[str]:
        ...

    # noinspection PyNoneFunctionAssignment
    @classmethod
    def get(
        cls, section: Optional[str] = None, name: Optional[str] = None, default_value: Optional[str] = None
    ) -> Union[str, ConfigParser]:
        """
        Get the entire config or get a value directly
        """
        cfg = cls._get_instance()
        if section is None:
            return cfg

        assert name is not None
        name = _normalize_name(name)

        opt = cls.validate_option_request(section, name, default_value)

        val = _get_from_env(section, name)
        if val is not None:
            LOGGER.debug(f"Setting {section}:{name} was set using an environment variable")
        else:
            val = cfg.get(section, name, fallback=default_value)

        if not opt:
            return val
        return opt.validate(val)

    @classmethod
    def is_set(cls, section: str, name: str) -> bool:
        """Check if a certain config option was specified in the config file."""
        return section in cls._get_instance() and name in cls._get_instance()[section]

    @classmethod
    def getboolean(cls, section: str, name: str, default_value: Optional[bool] = None) -> bool:
        """
        Return a boolean from the configuration
        """
        cls.validate_option_request(section, name, default_value)
        return cls._get_instance().getboolean(section, name, fallback=default_value)

    @classmethod
    def set(cls, section: str, name: str, value: str) -> None:
        """
        Override a value
        """
        name = _normalize_name(name)

        if section not in cls._get_instance():
            cls._get_instance().add_section(section)
        cls._get_instance().set(section, name, value)

    @classmethod
    def register_option(cls, option: "Option") -> None:
        cls.__config_definition[option.section][option.name] = option

    @classmethod
    def validate_option_request(cls, section: str, name: str, default_value: Optional[str]) -> Optional["Option"]:
        if section not in cls.__config_definition:
            LOGGER.warning("Config section %s not defined" % (section))
            # raise Exception("Config section %s not defined" % (section))
            return None
        if name not in cls.__config_definition[section]:
            LOGGER.warning("Config name %s not defined in section %s" % (name, section))
            # raise Exception("Config name %s not defined in section %s" % (name, section))
            return None
        opt = cls.__config_definition[section][name]
        if default_value is not None and opt.get_default_value() != default_value:
            LOGGER.warning(
                "Inconsistent default value for option %s.%s: defined as %s, got %s"
                % (section, name, opt.default, default_value)
            )

        return opt


def is_int(value: str) -> int:
    """int"""
    return int(value)


def is_float(value: str) -> float:
    """float"""
    return float(value)


def is_time(value: str) -> int:
    """Time, the number of seconds represented as an integer value"""
    return int(value)


def is_bool(value: Union[bool, str]) -> bool:
    """Boolean value, represented as any of true, false, on, off, yes, no, 1, 0. (Case-insensitive)"""
    if isinstance(value, bool):
        return value
    boolean_states: abc.Mapping[str, bool] = Config._get_instance().BOOLEAN_STATES
    if value.lower() not in boolean_states:
        raise ValueError("Not a boolean: %s" % value)
    return boolean_states[value.lower()]


def is_list(value: str) -> List[str]:
    """List of comma-separated values"""
    return [] if value == "" else [x.strip() for x in value.split(",")]


def is_map(map_in: str) -> Dict[str, str]:
    """List of comma-separated key=value pairs"""
    map_out = {}
    if map_in is not None:
        mappings = map_in.split(",")

        for mapping in mappings:
            parts = re.split("=", mapping.strip(), 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key != "" and value != "":
                    map_out[key] = value

    return map_out


def is_str(value: str) -> str:
    """str"""
    return str(value)


def is_str_opt(value: str) -> Optional[str]:
    """optional str"""
    if value is None:
        return None
    return str(value)


def is_uuid_opt(value: str) -> uuid.UUID:
    """optional uuid"""
    if value is None:
        return None
    return uuid.UUID(value)


T = TypeVar("T")


class Option(Generic[T]):
    """
    Defines an option and exposes it for use

    All config option should be define prior to use
    For the document generator to work properly, they should be defined at the module level.

    :param section: section in the config file
    :param name: name of the option
    :param default: default value for this option
        the default value is either a value or a function.
        If it is a value, `str(default)` will be used a default value.
        If it is a function, its doc string will be used to represent the value in documentation.
        and its return value as the actual default value
    :param documentation: the documentation for this option
    :param validator: a function responsible for turning the string representation of the option into the correct type.
        Its docstring is used as representation for the type of the option.
    :param predecessor_option: The Option that was deprecated in favour of this option.
    """

    def __init__(
        self,
        section: str,
        name: str,
        default: Union[T, None, Callable[[], T]],
        documentation: str,
        validator: Callable[[str], T] = is_str,
        predecessor_option: Optional["Option"] = None,
    ) -> None:
        self.section = section
        self.name = _normalize_name(name)
        self.validator = validator
        self.documentation = documentation
        self.default = default
        self.predecessor_option = predecessor_option
        Config.register_option(self)

    def get(self) -> T:
        cfg = Config._get_instance()
        if self.predecessor_option:
            has_deprecated_option = cfg.has_option(self.predecessor_option.section, self.predecessor_option.name)
            has_new_option = cfg.has_option(self.section, self.name)
            if has_deprecated_option and not has_new_option:
                warnings.warn(
                    "Config option %s is deprecated. Use %s instead." % (self.predecessor_option.name, self.name),
                    category=DeprecationWarning,
                )
                return self.predecessor_option.get()
        out = cfg.get(self.section, self.name, fallback=self.get_default_value())
        return self.validate(out)

    def get_type(self) -> Optional[str]:
        if callable(self.validator):
            return self.validator.__doc__
        return None

    def get_default_desc(self) -> str:
        defa = self.default
        if callable(defa):
            return "%s" % defa.__doc__
        else:
            return f"``{defa}``"

    def validate(self, value: str) -> T:
        return self.validator(value)

    def get_default_value(self) -> Optional[T]:
        defa = self.default
        if callable(defa):
            return defa()
        else:
            return defa

    def set(self, value: str) -> None:
        """Only for tests"""
        Config.set(self.section, self.name, value)


def option_as_default(opt: Option[T]) -> Callable[[], T]:
    """
    Wrap an option to be used as default value
    """

    def default_func() -> T:
        return opt.get()

    default_func.__doc__ = f""":inmanta.config:option:`{opt.section}.{opt.name}`"""
    return default_func


#############################
# Config
#
# Global config options are defined here
#############################
# flake8: noqa: H904
state_dir = Option("config", "state_dir", "/var/lib/inmanta", "The directory where the server stores its state", is_str)

log_dir = Option(
    "config",
    "log_dir",
    "/var/log/inmanta",
    "The directory where the resource action log is stored and the logs of auto-started agents.",
    is_str,
)


def get_executable() -> Optional[str]:
    """``os.path.abspath(sys.argv[0])``"""
    try:
        return os.path.abspath(sys.argv[0])
    except:
        return None


def get_default_nodename() -> str:
    """``socket.gethostname()``"""
    import socket

    return socket.gethostname()


nodename = Option("config", "node-name", get_default_nodename, "Force the hostname of this machine to a specific value", is_str)
feature_file_config = Option("config", "feature-file", None, "The loacation of the inmanta feature file.", is_str_opt)

###############################
# Transport Config
###############################
class TransportConfig(object):
    """
    A class to register the config options for Client classes
    """

    def __init__(self, name: str, port: int = 8888) -> None:
        self.prefix = "%s_rest_transport" % name
        self.host = Option(self.prefix, "host", "localhost", "IP address or hostname of the server", is_str)
        self.port = Option(self.prefix, "port", port, "Server port", is_int)
        self.ssl = Option(self.prefix, "ssl", False, "Connect using SSL?", is_bool)
        self.ssl_ca_cert_file = Option(
            self.prefix, "ssl_ca_cert_file", None, "CA cert file used to validate the server certificate against", is_str_opt
        )
        self.token = Option(self.prefix, "token", None, "The bearer token to use to connect to the API", is_str_opt)
        self.request_timeout = Option(
            self.prefix, "request_timeout", 120, "The time before a request times out in seconds", is_int
        )


compiler_transport = TransportConfig("compiler")
TransportConfig("client")
cmdline_rest_transport = TransportConfig("cmdline")


#############################
# auth
#############################
AUTH_JWT_PREFIX = "auth_jwt_"


class AuthJWTConfig(object):
    """
    Auth JWT configuration manager
    """

    sections: Dict[str, "AuthJWTConfig"] = {}
    issuers: Dict[str, "AuthJWTConfig"] = {}

    validate_cert: bool

    @classmethod
    def list(cls) -> List[str]:
        """
        Return a list of all defined auth jwt configurations. This method will load new sections if they were added
        since the last invocation.
        """
        cfg = Config._get_instance()
        prefix_len = len(AUTH_JWT_PREFIX)

        for section in cfg.keys():
            if section[:prefix_len] == AUTH_JWT_PREFIX:
                name = section[prefix_len:]
                if name not in cls.sections:
                    obj = cls(name, section, cfg[section])
                    cls.sections[name] = obj
                    if obj.issuer in cls.issuers:
                        raise ValueError("Only oner configuration per issuer is supported")

                    cls.issuers[obj.issuer] = obj

        # Verify that only one has sign set to true
        sign = False
        for name, cfg in cls.sections.items():
            if cfg.sign:
                if sign:
                    raise ValueError("Only one auth_jwt section may have sign set to true")
                else:
                    sign = True

        if len(cls.sections.keys()) > 0 and not sign:
            raise ValueError("One auth_jwt section should have sign set to true")

        return list(cls.sections.keys())

    @classmethod
    def get(cls, name: str) -> Optional["AuthJWTConfig"]:
        """
        Get the config with the given name
        """
        cls.list()
        if name in cls.sections:
            return cls.sections[name]
        return None

    @classmethod
    def get_sign_config(cls) -> Optional["AuthJWTConfig"]:
        """
        Get the configuration with sign is true
        """
        cls.list()
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
        if len(cls.issuers) == 0:
            cls.list()
        if issuer in cls.issuers:
            return cls.issuers[issuer]
        return None

    def __init__(self, name: str, section: str, config: SectionProxy):
        self.name = name
        self.section = section
        self._config = config
        if "algorithm" not in config:
            raise ValueError("algorithm is required in %s section" % self.section)

        self.algo = config["algorithm"]
        self.validate_generic()

        if self.algo.lower() == "hs256":
            self.validate_hs265()
        elif self.algo.lower() == "rs256":
            self.validate_rs265()
        else:
            raise ValueError("Algorithm %s in %s is not support " % (self.algo, self.section))

    def validate_generic(self) -> None:
        """
        Validate  and parse the generic options that are valid for all algorithms
        """
        if "sign" in self._config:
            self.sign = is_bool(self._config["sign"])
        else:
            self.sign = False

        if "client_types" not in self._config:
            raise ValueError("client_types is a required options for %s" % self.section)

        self.client_types = is_list(self._config["client_types"])
        for ct in self.client_types:
            if ct not in [client_type for client_type in const.ClientType]:
                raise ValueError("invalid client_type %s in %s" % (ct, self.section))

        if "expire" in self._config:
            self.expire = is_int(self._config["expire"])
        else:
            self.expire = 0

        if "issuer" in self._config:
            self.issuer = is_str(self._config["issuer"])
        else:
            self.issuer = "https://localhost:8888/"

        if "audience" in self._config:
            self.audience = is_str(self._config["audience"])
        else:
            self.audience = self.issuer

    def validate_hs265(self) -> None:
        """
        Validate and parse HS256 algorithm configuration
        """
        if "key" not in self._config:
            raise ValueError("key is required in %s for algorithm %s" % (self.section, self.algo))

        self.key = base64.urlsafe_b64decode((self._config["key"] + "==").encode("ascii"))
        if len(self.key) < 32:
            raise ValueError("HS256 requires a key of 32 bytes (256 bits) or longer in " + self.section)

    def _load_public_key(self, e: str, n: str) -> str:
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
            self.validate_cert = self._config.getboolean("validate_cert")
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
                "Unable to load key data for %s using the provided jwks_uri. Got error: %s" % (self.section, e.response)
            )
        except Exception as e:
            # Other errors are possible, such as IOError.
            raise ValueError("Unable to load key data for %s using the provided jwks_uri." % (self.section))

        self.keys: Dict[str, str] = {}
        for key in key_data["keys"]:
            self.keys[key["kid"]] = self._load_public_key(key["e"], key["n"])
