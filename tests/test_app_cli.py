"""
    Copyright 2018 Inmanta

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

import pytest

from inmanta.app import cmd_parser
from inmanta.config import Config


def app(args):
    parser = cmd_parser()

    options, other = parser.parse_known_args(args=args)
    options.other = other

    # Load the configuration
    Config.load_config(options.config_file)

    # start the command
    if not hasattr(options, "func"):
        # show help
        parser.print_usage()
        return

    options.func(options)


def test_help(inmanta_config, capsys):
    with pytest.raises(SystemExit):
        app(["-h"])
    out, _ = capsys.readouterr()

    assert out.startswith("usage:")
    # check main options
    assert "--config" in out
    # check subcommands list
    assert "export" in out


def test_help2(inmanta_config, capsys):
    with pytest.raises(SystemExit):
        app(["help"])
    out, _ = capsys.readouterr()

    assert out.startswith("usage:")
    # check main options
    assert "--config" in out
    # check subcommands list
    assert "export" in out


def test_help_sub(inmanta_config, capsys):
    with pytest.raises(SystemExit):
        app(["help", "module"])
    out, _ = capsys.readouterr()

    assert out.startswith("usage:")
    # check main options
    assert "--config" not in out
    # check subcommands list
    assert "export" not in out
    # check subcommands help
    assert "update" in out
