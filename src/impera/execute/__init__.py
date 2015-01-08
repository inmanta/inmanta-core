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

import logging


LOGGER = logging.getLogger(__name__)


class DuplicateVariableException(Exception):
    """
        This exception thrown when a variable is declared twice in the same
        scope.
    """


class DuplicateScopeException(Exception):
    """
        This exception is raised when a scope with a duplicate name is created.
    """


class NotFoundException(Exception):
    """
        This exception is thrown when a variable is not found
    """
