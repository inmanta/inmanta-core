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

import inspect
import os
import subprocess
from functools import reduce
from typing import TYPE_CHECKING, Any, Callable, Dict, FrozenSet, List, Optional, Sequence, Tuple, Type, TypeVar

import inmanta.ast.type as inmanta_type
from inmanta import const, protocol
from inmanta.ast import CompilerException, LocatableString, Location, Namespace, Range, RuntimeException, TypeNotFoundException
from inmanta.ast.type import NamedType
from inmanta.config import Config
from inmanta.execute.proxy import DynamicProxy
from inmanta.execute.runtime import QueueScheduler, Resolver, ResultVariable
from inmanta.execute.util import Unknown
from inmanta.stable_api import stable_api


class Finalizers:
    """
    This class keeps all the finalizers that need to be called right after the compilation finishes
    """

    __finalizers: Sequence[Callable] = []

    @classmethod
    def add_function(cls, fnc: Callable) -> None:
        cls.__finalizers.append(fnc)

    @classmethod
    def call_finalizers(cls):
        for fnc in cls.__finalizers:
            fnc()
