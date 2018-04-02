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

import base64
from collections import defaultdict
from configparser import ConfigParser, Interpolation
import json
import logging
import os
import re
import sys
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from tornado import httpclient

from inmanta import methods


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

    def set(self, value):
        """ Only for tests"""
        cfg = Config._get_instance()
        cfg.set(self.section, self.name, value)

#############################
# Config
#
# Global config options are defined here
#############################
# flake8: noqa: H904
state_dir = Option("config", "state_dir", "/var/lib/inmanta",
                   "The directory where the server stores its state")

log_dir = Option("config", "log_dir", "/var/log/inmanta",
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


nodename = Option("config", "node-name", get_default_nodename,
                  "Force the hostname of this machine to a specific value", is_str)


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
        self.ssl_ca_cert_file = Option(self.prefix, "ssl_ca_cert_file", None,
                                       "CA cert file used to validate the server certificate against", is_str_opt)
        self.token = Option(self.prefix, "token", None, "The bearer token to use to connect to the API", is_str_opt)

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
    sections = {}
    issuers = {}

    @classmethod
    def list(cls):
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

        return cls.sections.keys()

    @classmethod
    def get(cls, name):
        """
            Get the config with the given name
        """
        cls.list()
        if name in cls.sections:
            return cls.sections[name]
        return None

    @classmethod
    def get_sign_config(cls):
        """
            Get the configuration with sign is true
        """
        cls.list()
        for cfg in cls.sections.values():
            if cfg.sign:
                return cfg

    @classmethod
    def get_issuer(cls, issuer):
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

    def __init__(self, name, section, config):
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

    def validate_generic(self):
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
            if ct not in methods.VALID_CLIENT_TYPES:
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

    def validate_hs265(self):
        """
            Validate and parse HS256 algorithm configuration
        """
        if "key" not in self._config:
            raise ValueError("key is required in %s for algorithm %s" % (self.section, self.algo))

        self.key = base64.urlsafe_b64decode((self._config["key"] + "==").encode("ascii"))
        if len(self.key) < 32:
            raise ValueError("HS256 requires a key of 32 bytes (256 bits) or longer in " + self.section)

    def _load_public_key(self, e, n):
        def to_int(x):
            bs = base64.urlsafe_b64decode(x + "==")
            return int.from_bytes(bs, byteorder="big")

        ei = to_int(e)
        ni = to_int(n)
        numbers = RSAPublicNumbers(ei, ni)
        public_key = numbers.public_key(backend=default_backend())
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem

    def validate_rs265(self):
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

        http_client = httpclient.HTTPClient()
        try:
            response = http_client.fetch(self.jwks_uri, validate_cert=self.validate_cert)
            if hasattr(response.body, "decode"):
                body = response.body.decode()
            else:
                body = response.body
            key_data = json.loads(body)
        except httpclient.HTTPError as e:
            # HTTPError is raised for non-200 responses; the response
            # can be found in e.response.
            raise ValueError("Unable to load key data for %s using the provided jwks_uri. Got error: %s" %
                             (self.section, e.response))
        except Exception as e:
            # Other errors are possible, such as IOError.
            raise ValueError("Unable to load key data for %s using the provided jwks_uri." % (self.section))
        http_client.close()

        self.keys = {}
        for key in key_data["keys"]:
            self.keys[key["kid"]] = self._load_public_key(key["e"], key["n"])
