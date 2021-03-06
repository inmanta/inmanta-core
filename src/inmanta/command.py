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


class CLIException(Exception):
    def __init__(self, exitcode: int, *args, **kwargs):
        self.exitcode = exitcode
        super(CLIException, self).__init__(*args, **kwargs)


class ShowUsageException(Exception):
    """
    Raise this exception to show the usage message of the given level
    """


class Commander(object):
    """
    This class handles commands
    """

    __command_functions = {}

    @classmethod
    def add(cls, name: str, function, help_msg: str, parser_config, require_project=False, aliases=[]) -> None:
        """
        Add a new export function
        """
        if name in cls.__command_functions:
            raise Exception("Command %s already registered" % name)

        cls.__command_functions[name] = {
            "function": function,
            "help": help_msg,
            "parser_config": parser_config,
            "require_project": require_project,
            "aliases": aliases,
        }

    config = None

    @classmethod
    def reset(cls):
        """
        Return a list of commands
        """
        cls.__command_functions = {}

    @classmethod
    def commands(cls):
        """
        Return a list of commands
        """
        return cls.__command_functions


class command(object):  # noqa: N801
    """
    A decorator that registers an export function
    """

    def __init__(self, name, help_msg, parser_config=None, require_project=False, aliases=[]):
        self.name = name
        self.help = help_msg
        self.require_project = require_project
        self.parser_config = parser_config
        self.aliases = aliases

    def __call__(self, function):
        """
        The wrapping
        """
        Commander.add(self.name, function, self.help, self.parser_config, self.require_project, self.aliases)
        return function
