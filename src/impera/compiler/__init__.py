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

import sys
import logging

from impera.execute import scheduler
from impera import module
from . import main

LOGGER = logging.getLogger(__name__)


def do_compile():
    """
        Run run run
    """
    module.Project.get().verify()
    compiler = main.Compiler()

    success = False
    try:
        LOGGER.debug("Starting compile")
        graph = compiler.graph
        statements = compiler.compile()
        sched = scheduler.Scheduler(graph)
        success = sched.run(compiler, statements)

        LOGGER.debug("Compile done")

        if not success:
            sys.stderr.write("Unable to execute all statements.\n")
        else:
            return graph.root_scope

    except Exception:
        LOGGER.exception("An exception occurred during compile")
        return None
