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

from itertools import chain
from typing import Dict, FrozenSet, Iterator, List, Optional, Tuple

import inmanta.warnings as inmanta_warnings
from inmanta.ast import Anchor, Locatable, Namespace, RuntimeException, TypeNotFoundException, VariableShadowWarning
from inmanta.ast.statements import DefinitionStatement, DynamicStatement
from inmanta.execute.runtime import QueueScheduler, Resolver


class BasicBlock(object):
    def __init__(self, namespace: Namespace, stmts: List[DynamicStatement] = []) -> None:
        self.__stmts = []  # type: List[DynamicStatement]
        self.__definition_stmts = []  # type: List[DefinitionStatement]
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

    def add_definition(self, stmt: DefinitionStatement) -> None:
        self.__definition_stmts.append(stmt)

    def get_variables(self) -> List[str]:
        return self.variables

    def add_var(self, name: str) -> None:
        self.variables.append(name)

    def normalize(self) -> None:
        self.variables = list(chain.from_iterable(stmt.declared_variables() for stmt in self.__stmts))

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

    def warn_shadowed_variables(self) -> None:
        """
            Produces a warning for any shadowed variables in ocurring in this namespace. This namespace's scope's root block
            is used as an entrypoint for the check. If nested_block is provided, that block is interpreted as living in this
            scope and only that block is searched for shadowing with respect to the scope.
        """
        for var, shadowed_locs, orig_locs in self.shadowed_variables():
            inmanta_warnings.warn(
                VariableShadowWarning(
                    None,
                    "Variable `%s` shadowed: originally declared at %s, shadowed at %s"
                    % (
                        var,
                        ",".join(str(loc.get_location()) for loc in orig_locs),
                        ",".join(str(loc.get_location()) for loc in shadowed_locs),
                    ),
                )
            )

    def shadowed_variables(
        self, surrounding_vars: Optional[Dict[str, FrozenSet[Locatable]]] = None,
    ) -> Iterator[Tuple[str, FrozenSet[Locatable], FrozenSet[Locatable]]]:
        """
            Returns an iterator over variables shadowed in this block or it's nested blocks.
            The elements are tuples of the variable name, a set of the shadowed locations
            and a set of the originally declared locations.
            :param surrounding_vars: an accumulator for variables declared in surrounding blocks.
            :param nested_blocks: nested blocks to search for shadowed variables,
                defaults to this block's statement's nested blocks.
        """
        if surrounding_vars is None:
            surrounding_vars = {}
        surrounding_vars = surrounding_vars.copy()

        def merge_locatables(tuples: Iterator[Tuple[str, Locatable]]) -> Dict[str, FrozenSet[Locatable]]:
            acc: Dict[str, FrozenSet[Locatable]] = {}
            for var, loc in tuples:
                if var not in acc:
                    acc[var] = frozenset(())
                acc[var] = acc[var].union({loc})
            return acc

        own_variables: Iterator[Tuple[str, Locatable]] = (
            (var, stmt) for stmt in self.__stmts for var in stmt.declared_variables()
        )
        for var, locs in merge_locatables(own_variables).items():
            if var in surrounding_vars:
                yield (var, locs, surrounding_vars[var])
            surrounding_vars[var] = locs

        yield from chain.from_iterable(
            block.shadowed_variables(surrounding_vars)
            for stmt in chain(self.__stmts, self.__definition_stmts)
            for block in stmt.nested_blocks()
        )
