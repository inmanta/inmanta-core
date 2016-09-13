"""
    Copyright 2016 Inmanta

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
import sys

from cliff.app import App
from cliff.commandmanager import CommandManager


class Inmanta(App):

    log = logging.getLogger(__name__)

    def __init__(self):
        super(Inmanta, self).__init__(
            description='inmanta cli app',
            version='0.7',
            command_manager=CommandManager('inmanta'),
        )

    def initialize_app(self, argv):
        self.log.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    myapp = Inmanta()
    return myapp.run(argv)


def get_parser():
    from inmanta.client import InmantaCommand

    myapp = Inmanta()
    rp = myapp.parser
    subparsers = rp.add_subparsers()

    command_manager = myapp.command_manager
    for name, ep in sorted(command_manager):
        try:
            factory = ep.load()
        except Exception as err:
            myapp.stdout.write('Could not load %r\n' % ep)
            continue
        try:
            cmd = factory(myapp, None)
            if cmd.deprecated:
                continue
        except Exception as err:
            myapp.stdout.write('Could not instantiate %r: %s\n' % (ep, err))
            continue
        if isinstance(cmd, InmantaCommand):
            cmd.get_parser(name, parser_override=subparsers)

    return rp


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
