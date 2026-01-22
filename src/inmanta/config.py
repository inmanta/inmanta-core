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

import logging
import os
import re
import sys
import typing
import uuid
import warnings
from collections import abc, defaultdict
from configparser import ConfigParser, Interpolation
from typing import Callable, Generic, Optional, TypeVar, Union, overload

from crontab import CronTab

LOGGER = logging.getLogger(__name__)


T = TypeVar("T")


def _normalize_name(name: str) -> str:
    return name.replace("_", "-")


def _get_env_var_name_for_config_option(section: str, name: str) -> str:
    """
    Return the name of the environment variable that belongs to the given config option.
    """
    env_var_name = f"INMANTA_{section}_{name}"
    # The names of config sections and config options can be written using both - and _ characters in config files.
    # For environment variables we support _ only.
    env_var_name = env_var_name.replace("-", "_")
    # The configuration section lsm.callback has a dot in its name. This character is not supported
    # in the name of an environment variable. As such, we use an _ instead.
    env_var_name = env_var_name.replace(".", "_")
    return env_var_name.upper()


def _get_from_env(section: str, name: str) -> Optional[str]:
    """
    Return the value of the given config option set via an environment variable, or None if the config
    option was not set via an environment variable.
    """
    env_var_name = _get_env_var_name_for_config_option(section, name)
    return os.environ.get(env_var_name, default=None)


class LenientConfigParser(ConfigParser):
    def optionxform(self, name: str) -> str:
        name = _normalize_name(name)
        return super().optionxform(name)

    def _validate_value_types(self, *, section: str = "", option: str = "", value: str = "") -> None:
        """
        Override parent class to get clear exceptions
        """
        if not isinstance(section, str):
            raise TypeError(f"section names must be strings, instead received {section} of type {type(section)}")
        if not isinstance(option, str):
            raise TypeError(f"option keys must be strings, instead received {option} of type {type(option)}")
        if not isinstance(value, str):
            raise TypeError(f"option values must be strings, instead received {value} of type {type(value)}")
        super()._validate_value_types(section=section, option=option, value=value)


class Config:
    __instance: Optional[ConfigParser] = None
    _config_dir: Optional[str] = None  # The directory this config was loaded from
    _min_c_config_file: Optional[str] = None  # Config file
    __config_definition: dict[str, dict[str, "Option"]] = defaultdict(dict)

    @classmethod
    def get_config_options(cls) -> dict[str, dict[str, "Option"]]:
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
        cfg_files_in_config_dir: list[str]
        if config_dir and os.path.isdir(config_dir):
            cfg_files_in_config_dir = sorted(
                [os.path.join(config_dir, f) for f in os.listdir(config_dir) if f.endswith(".cfg")]
            )
        else:
            cfg_files_in_config_dir = []

        local_dot_inmanta_cfg_files: list[str] = [os.path.expanduser("~/.inmanta.cfg"), ".inmanta", ".inmanta.cfg"]

        # Files with a higher index in the list, override config options defined by files with a lower index
        files: list[str]
        if min_c_config_file is not None:
            files = [main_cfg_file] + cfg_files_in_config_dir + local_dot_inmanta_cfg_files + [min_c_config_file]

        else:
            files = [main_cfg_file] + cfg_files_in_config_dir + local_dot_inmanta_cfg_files

        config = LenientConfigParser(interpolation=Interpolation())
        config.read(files)
        cls._save_loaded_config(config, config_dir, min_c_config_file)

    @classmethod
    def load_config_from_dict(
        cls,
        input_config: typing.Mapping[str, typing.Mapping[str, typing.Any]],
    ) -> None:
        """
        Load the configuration from a dict, used to copy config.
        Replaces all existing config.
        """
        config = LenientConfigParser(interpolation=Interpolation())
        config.read_dict(input_config)
        cls._save_loaded_config(config, config_dir=None, min_c_config_file=None)

    @classmethod
    def _save_loaded_config(
        cls, config: LenientConfigParser, config_dir: Optional[str], min_c_config_file: Optional[str]
    ) -> None:
        cls.__instance = config
        cls._config_dir = config_dir
        cls._min_c_config_file = min_c_config_file
        cls._config_updated()

    @classmethod
    def config_as_dict(cls) -> typing.Mapping[str, typing.Mapping[str, typing.Any]]:
        """
        Return the config as a dict, to be used with load_config_from_dict
        """
        assert cls.__instance is not None
        return dict(cls.__instance.items())

    @classmethod
    def _get_instance(cls) -> ConfigParser:
        if cls.__instance is None:
            cls.load_config()
            assert cls.__instance is not None

        return cls.__instance

    @classmethod
    def get_instance(cls) -> ConfigParser:
        """Get the singleton instance of the ConfigParser. In case it did not load the config yet, it will be loaded."""
        return cls._get_instance()

    @classmethod
    def _reset(cls) -> None:
        cls.__instance = None
        cls._config_dir = None
        cls._min_c_config_file = None
        cls._config_updated()

    @classmethod
    def _config_updated(cls) -> None:
        """
        This method must be called every time the configuration is updated.
        """
        from inmanta.protocol.auth import auth

        # Clear the cached JWT config. It might have become out of sync with
        # the configuration in this class.
        auth.AuthJWTConfig.reset()

    @overload
    @classmethod
    def get(cls) -> ConfigParser: ...

    @overload
    @classmethod
    def get(cls, section: str, name: str, default_value: Optional[T] = None) -> Optional[str | T]: ...

    # noinspection PyNoneFunctionAssignment
    @classmethod
    def get(cls, section: Optional[str] = None, name: Optional[str] = None, default_value: Optional[object] = None) -> object:
        """
        Get the entire config or get a value directly
        """
        if section is None:
            return cls.get_instance()

        assert name is not None
        name = _normalize_name(name)

        option: Optional[Option[object]] = cls.validate_option_request(section, name, default_value)
        return cls.get_for_option(option) if option is not None else cls._get_value(section, name, default_value)

    @classmethod
    def get_for_option(cls, option: "Option[T]") -> T:
        default_value = option.get_default_value()
        raw_value: str | T = cls._get_value(option.section, option.name, default_value)
        return option.validate(raw_value)

    @classmethod
    def _get_value(cls, section: str, name: str, default_value: T) -> str | T:
        cfg: ConfigParser = cls.get_instance()
        val: Optional[str] = _get_from_env(section, name)
        if val is not None:
            LOGGER.debug("Setting %s:%s was set using an environment variable", section, name)
            return val
        # Typing of this method in the sdk is not entirely accurate
        # It just returns the fallback, whatever its type
        return cfg.get(section, name, fallback=default_value)

    @classmethod
    def is_set(cls, section: str, name: str) -> bool:
        """Check if a certain config option was specified in the config file."""
        return section in cls.get_instance() and name in cls.get_instance()[section]

    @classmethod
    def getboolean(cls, section: str, name: str, default_value: Optional[bool] = None) -> bool:
        """
        Return a boolean from the configuration
        """
        value = cls.get(section, name, default_value)
        if value is None:
            raise ValueError(f"Expected boolean value. Found: {value}")
        return is_bool(value)

    @classmethod
    def set(cls, section: str, name: str, value: str) -> None:
        """
        Override a value
        """
        name = _normalize_name(name)

        if section not in cls.get_instance():
            cls.get_instance().add_section(section)
        cls.get_instance().set(section, name, value)
        cls._config_updated()

    @classmethod
    def register_option(cls, option: "Option") -> None:
        cls.__config_definition[option.section][option.name] = option

    @classmethod
    def validate_option_request(cls, section: str, name: str, default_value: Optional[T]) -> Optional["Option[T]"]:
        if section not in cls.__config_definition:
            LOGGER.warning("Config section %s not defined", section)
            # raise Exception("Config section %s not defined" % (section))
            return None
        if name not in cls.__config_definition[section]:
            LOGGER.warning("Config name %s not defined in section %s", name, section)
            # raise Exception("Config name %s not defined in section %s" % (name, section))
            return None
        opt = cls.__config_definition[section][name]
        if default_value is not None and opt.get_default_value() != default_value:
            LOGGER.warning(
                "Inconsistent default value for option %s.%s: defined as %s, got %s", section, name, opt.default, default_value
            )

        return opt


def is_int(value: str | int) -> int:
    """int"""
    return int(value)


def is_float(value: str | float) -> float:
    """float"""
    return float(value)


def is_time(value: str | int) -> int:
    """Time, the number of seconds represented as an integer value"""
    return int(value)


def is_time_or_cron(value: str | int) -> Union[int, str]:
    """Time, the number of seconds represented as an integer value or a cron-like expression"""
    try:
        return is_time(value)
    except ValueError:
        try:
            CronTab(value)
        except ValueError as e:
            raise ValueError("Not an int or cron expression: %s" % value)
        return value


def is_bool(value: Union[bool, str]) -> bool:
    """Boolean value, represented as any of true, false, on, off, yes, no, 1, 0. (Case-insensitive)"""
    if isinstance(value, bool):
        return value
    boolean_states: abc.Mapping[str, bool] = Config.get_instance().BOOLEAN_STATES
    if value.lower() not in boolean_states:
        raise ValueError("Not a boolean: %s" % value)
    return boolean_states[value.lower()]


def is_list(value: str | list[str]) -> list[str]:
    """List of comma-separated values"""
    if isinstance(value, list):
        return value
    return [] if value == "" else [x.strip() for x in value.split(",")]


def is_lower_bounded_int(lower_bound: int) -> Callable[[str | int], int]:
    """lower-bounded int factory"""

    def inner(value: str | int) -> int:
        to_int = int(value)
        if to_int < lower_bound:
            raise ValueError(f"Value can not be lower than {lower_bound}")
        return to_int

    inner.__doc__ = f"int >= {lower_bound}"
    return inner


def is_map(map_in: str | typing.Mapping[str, str]) -> typing.Mapping[str, str]:
    """List of comma-separated key=value pairs"""
    if isinstance(map_in, typing.Mapping):
        return map_in
    map_out = {}
    if map_in is not None:
        mappings = map_in.split(",")

        for mapping in mappings:
            parts = re.split("=", mapping.strip(), maxsplit=1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key != "" and value != "":
                    map_out[key] = value

    return map_out


def config_map_to_str(inp: typing.Mapping[str, str]) -> str:
    return ",".join(f"{k}={v}" for k, v in inp.items())


def is_str(value: str) -> str:
    """str"""
    return str(value)


def is_str_opt(value: Optional[str]) -> Optional[str]:
    """optional str"""
    if value is None:
        return None
    return str(value)


def is_uuid_opt(value: Optional[str | uuid.UUID]) -> Optional[uuid.UUID]:
    """optional uuid"""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(value)


def is_int_opt(value: Optional[str]) -> Optional[int]:
    """optional int"""
    if value is None:
        return None
    return int(value)


class Option(Generic[T]):
    """
    Defines an option and exposes it for use

    All config option should be defined prior to use
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
        default: Union[T, Callable[[], T]],
        documentation: str,
        validator: Callable[[str | T], T] = is_str,
        predecessor_option: Optional["Option"] = None,
    ) -> None:
        self.section = section
        self.name = _normalize_name(name)
        self.validator = validator
        self.documentation = documentation
        self.default = default
        self.predecessor_option = predecessor_option
        Config.register_option(self)

    def get_full_name(self) -> str:
        """
        Returns the fully-qualified name of this config option.
        """
        return f"{self.section}.{self.name}"

    def get(self) -> T:
        raw_config: ConfigParser = Config.get()
        if self.predecessor_option:
            has_deprecated_option = raw_config.has_option(self.predecessor_option.section, self.predecessor_option.name)
            has_new_option = raw_config.has_option(self.section, self.name)
            if has_deprecated_option and not has_new_option:
                warnings.warn(
                    f"Config option {self.predecessor_option.name} is deprecated. Use {self.name} instead.",
                    category=DeprecationWarning,
                )
                return self.predecessor_option.get()
        return Config.get_for_option(self)

    def get_type(self) -> Optional[str]:
        if callable(self.validator):
            return self.validator.__doc__
        return None

    def get_environment_variable(self) -> str:
        """
        Return the environment variable associated with this config option.
        """
        return _get_env_var_name_for_config_option(self.section, self.name)

    def get_default_desc(self) -> str:
        defa = self.default
        if callable(defa):
            return "%s" % defa.__doc__
        else:
            return f"``{defa}``"

    def validate(self, value: str | T) -> T:
        return self.validator(value)

    def get_default_value(self) -> T:
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

logging_config = Option(
    section="config",
    name="logging_config",
    default=None,
    documentation="The path to the configuration file for the logging framework. This is a YAML file that follows "
    "the dictionary-schema accepted by logging.config.dictConfig(). All other log-related configuration "
    "options will be ignored when this option is set.",
    validator=is_str_opt,
)


def make_option_for_log_file(component_name: str) -> Option[str | None]:
    return Option(
        section="logging",
        name=component_name,
        default=None,
        documentation=f"The path to the configuration file for the logging of the {component_name}. This is a YAML file that follows "
        "the dictionary-schema accepted by logging.config.dictConfig(). All other log-related configuration "
        "options will be ignored when this option is set.",
        validator=is_str_opt,
    )


component_log_configs = {k: make_option_for_log_file(k) for k in ["server", "scheduler", "compiler"]}
scheduler_log_config = component_log_configs["scheduler"]


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
feature_file_config = Option("config", "feature-file", None, "The location of the inmanta feature file.", is_str_opt)


###############################
# Transport Config
###############################
class TransportConfig:
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
        self.max_clients = Option(
            self.prefix,
            "max_clients",
            None,
            "The maximum number of simultaneous connections that can be open in parallel",
            is_int_opt,
        )


compiler_transport = TransportConfig("compiler")
TransportConfig("client")
cmdline_rest_transport = TransportConfig("cmdline")
