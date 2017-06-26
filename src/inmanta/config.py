"""
    Copyright 2017 Inmanta

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

from configparser import ConfigParser, Interpolation
import os
import logging
from collections import defaultdict
import uuid
import sys
import re

LOGGER = logging.getLogger(__name__)


def _normalize_name(name: str):
    return name.replace("_", "-")


class LenientConfigParser(ConfigParser):

    def optionxform(self, name):
        name = _normalize_name(name)
        return super(LenientConfigParser, self).optionxform(name)


class Config(object):
    __instance = None
    __config_definition = defaultdict(lambda: {})

    @classmethod
    def get_config_options(cls):
        return cls.__config_definition

    @classmethod
    def load_config(cls, config_file=None):
        """
        Load the configuration file
        """
        config = LenientConfigParser(interpolation=Interpolation())

        files = ["/etc/inmanta.cfg", os.path.expanduser("~/.inmanta.cfg"), ".inmanta",
                 ".inmanta.cfg"]
        if config_file is not None:
            files.append(config_file)

        config.read(files)
        cls.__instance = config

    @classmethod
    def _get_instance(cls):
        if cls.__instance is None:
            raise Exception("Load the configuration first")

        return cls.__instance

    @classmethod
    def _reset(cls):
        cls.__instance = None

    # noinspection PyNoneFunctionAssignment
    @classmethod
    def get(cls, section=None, name=None, default_value=None):
        """
            Get the entire compiler or get a value directly
        """
        cfg = cls._get_instance()
        if section is None:
            return cfg
        name = _normalize_name(name)

        opt = cls.validate_option_request(section, name, default_value)

        val = cfg.get(section, name, fallback=default_value)
        if not opt:
            return val
        return opt.validate(val)

    @classmethod
    def getboolean(cls, section, name, default_value=None):
        """
            Return a boolean from the configuration
        """
        cls.validate_option_request(section, name, default_value)
        return cls._get_instance().getboolean(section, name, fallback=default_value)

    @classmethod
    def set(cls, section, name, value):
        """
            Override a value
        """
        name = _normalize_name(name)

        if section not in cls._get_instance():
            cls._get_instance().add_section(section)
        cls._get_instance().set(section, name, value)

    @classmethod
    def register_option(cls, option):
        cls.__config_definition[option.section][option.name] = option

    @classmethod
    def validate_option_request(cls, section, name, default_value):
        if section not in cls.__config_definition:
            LOGGER.warning("Config section %s not defined" % (section))
            # raise Exception("Config section %s not defined" % (section))
            return
        if name not in cls.__config_definition[section]:
            LOGGER.warning("Config name %s not defined in section %s" % (name, section))
            # raise Exception("Config name %s not defined in section %s" % (name, section))
            return
        opt = cls.__config_definition[section][name]
        if not opt.get_default_value() == opt.get_default_value():
            LOGGER.warning("Inconsistent default value for option %s.%s: defined as %s, got %s" %
                        (section, name, opt.default, default_value))

        return opt


def is_int(value):
    """int"""
    return int(value)


def is_time(value):
    """time"""
    return int(value)


def is_bool(value):
    """bool"""
    if type(value) == bool:
        return value
    return Config._get_instance()._convert_to_boolean(value)


def is_list(value):
    """list"""
    return [x.strip() for x in value.split(",")]


def is_map(map_in):
    """map"""
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


def is_str(value):
    """str"""
    return str(value)


def is_str_opt(value):
    """optional str"""
    if value is None:
        return None
    return str(value)


def is_uuid_opt(value):
    """optional uuid"""
    if value is None:
        return None
    return uuid.UUID(value)


class Option(object):
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
    """

    def __init__(self, section, name, default, documentation, validator=is_str):
        self.section = section
        self.name = _normalize_name(name)
        self.validator = validator
        self.documentation = documentation
        self.default = default
        Config.register_option(self)

    def get(self):
        cfg = Config._get_instance()
        out = cfg.get(self.section, self.name, fallback=self.get_default_value())
        return self.validate(out)

    def get_type(self):
        if callable(self.validator):
            return self.validator.__doc__
        return None

    def get_default_desc(self):
        defa = self.default
        if callable(defa):
            return "$%s" % defa.__doc__
        else:
            return defa

    def validate(self, value):
        return self.validator(value)

    def get_default_value(self):
        defa = self.default
        if callable(defa):
            return defa()
        else:
            return defa

#############################
# Config
#
# Global config options are defined here
#############################
# flake8: noqa: H904
state_dir = \
    Option("config", "state_dir", "/var/lib/inmanta",
           "The directory where the server stores its state")

log_dir = \
    Option("config", "log_dir", "/var/log/inmanta",
           "The directory where the server stores log file. Currently this is only for the output of embedded agents.")


def get_executable():
    """os.path.abspath(sys.argv[0]) """
    try:
        return os.path.abspath(sys.argv[0])
    except:
        return None


def get_default_nodename():
    """ socket.gethostname() """
    import socket
    return socket.gethostname()

nodename = \
    Option("config", "node-name", get_default_nodename, "Force the hostname of this machine to a specific value", is_str)


###############################
# Transport Config
###############################


class TransportConfig(object):
    """
        A class to register the config options for Client classes
    """

    def __init__(self, name):
        self.prefix = "%s_rest_transport" % name
        self.host = Option(self.prefix, "host", "localhost", "IP address or hostname of the server", is_str)
        self.port = Option(self.prefix, "port", 8888, "Server port", is_int)
        self.ssl = Option(self.prefix, "ssl", False, "Connect using SSL?", is_bool)
        self.ssl_ca_cert_file = Option(
            self.prefix, "ssl_ca_cert_file", None, "CA cert file used to validate the server certificate against", is_str_opt)
        self.password = Option(
            self.prefix, "password", None, "Password used to connect to the server", is_str_opt)
        self.username = Option(
            self.prefix, "username", None, "Username used to connect to the server", is_str_opt)

TransportConfig("compiler")
TransportConfig("client")
cmdline_rest_transport = TransportConfig("cmdline")
