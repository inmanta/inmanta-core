"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: bart@impera.io
"""

from configparser import ConfigParser
import os


class Config(object):
    __instance = None

    @classmethod
    def load_config(cls, config_file=None):
        """
        Load the configuration file
        """
        config = ConfigParser()

        files = ["/etc/imp.cfg", "/etc/impera.cfg", os.path.expanduser("~/.imp.cfg"), os.path.expanduser("~/.impera.cfg"),
                 ".imp", ".impera"]
        if config_file is not None:
            files.append(config_file)

        config.read(files)
        cls.__instance = config

    @classmethod
    def _get_instance(cls):
        if cls.__instance is None:
            raise Exception("Load the configuration first")

        return cls.__instance

    # noinspection PyNoneFunctionAssignment
    @classmethod
    def get(cls, section=None, name=None, default_value=None):
        """
            Get the entire parser or get a value directly
        """
        cfg = cls._get_instance()
        if section is None:
            return cfg

        return cfg.get(section, name, fallback=default_value)

    @classmethod
    def getboolean(cls, section, name, default_value=None):
        """
            Return a boolean from the configuration
        """
        return cls._get_instance().getboolean(section, name, fallback=default_value)

    @classmethod
    def set(cls, section, name, value):
        """
            Override a value
        """
        cls._get_instance().set(section, name, value)
