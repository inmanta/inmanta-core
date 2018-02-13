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

from inmanta.ast.statements import DynamicStatement
from inmanta.ast.statements.assign import Assign
from inmanta.ast import TypeNotFoundException, RuntimeException, Namespace, Anchor
from typing import List
from inmanta.execute.runtime import Resolver, QueueScheduler


class BasicBlock(object):

    def __init__(self, namespace: Namespace, stmts: List[DynamicStatement]=[]) -> None:
        self.__stmts = []  # type: List[DynamicStatement]
        self.variables = []  # type: List[str]
        self.namespace = namespace

        for st in stmts:
            self.add(st)

    def get_stmts(self) -> List[DynamicStatement]:
        return self.__stmts

    def get_anchors(self) -> List[Anchor]:
        return [a for s in self.__stmts for a in s.get_anchors()]

    def add(self, stmt: DynamicStatement) -> None:
        self.__stmts.append(stmt)

    def get_variables(self) -> List[str]:
        return self.variables

    def add_var(self, name: str) -> None:
        self.variables.append(name)

    def normalize(self) -> None:
        assigns = [s for s in self.__stmts if isinstance(s, Assign)]  # type: List[Assign]
        self.variables = [s.name for s in assigns]

        for s in self.__stmts:
            try:
                s.normalize()
            except TypeNotFoundException as e:
                e.set_statement(s)
                raise e
        # not used yet
        # self.requires = set([require for s in self.__stmts for require in s.requires()])

        # self.external = self.requires - set(self.variables)

        # self.external_not_global = [x for x in self.external if "::" not in x]

#     def get_requires(self) -> List[str]:
#         return self.external

    def emit(self, resolver: Resolver, queue: QueueScheduler) -> None:
        for s in self.__stmts:
            try:
                s.emit(resolver, queue)
            except RuntimeException as e:
                e.set_statement(s)
                raise e
