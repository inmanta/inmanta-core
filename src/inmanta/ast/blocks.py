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
import warnings
from collections.abc import Set
from itertools import chain
from typing import TYPE_CHECKING, Dict, FrozenSet, Iterable, Iterator, List, Optional, Sequence, Tuple

from inmanta.ast import Anchor, Locatable, Namespace, RuntimeException, TypeNotFoundException, VariableShadowWarning
from inmanta.ast.statements import DefinitionStatement, DynamicStatement, Statement, StaticEagerPromise
from inmanta.execute.runtime import QueueScheduler, Resolver

if TYPE_CHECKING:

    from inmanta.execute.runtime import ExecutionContext


class BasicBlock(object):
    def __init__(self, namespace: Namespace, stmts: List[DynamicStatement] = []) -> None:
        self.__stmts = []  # type: List[DynamicStatement]
        self.__definition_stmts = []  # type: List[DefinitionStatement]
        self.__variables = []  # type: List[Tuple[str, Statement]]
        self.namespace = namespace
        self.context: "ExecutionContext" = None

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
        """
        Returns a list of all variables declared in this block. Does not include variables declared in nested blocks.
        """
        return [var for var, _ in self.__variables]

    def add_var(self, name: str, stmt: Statement) -> None:
        """
        Adds a variable to this block, paired with the statement that put it here.
        """
        self.__variables.append((name, stmt))

    def normalize(self) -> None:
        self.__variables = [(var, stmt) for stmt in self.__stmts for var in stmt.declared_variables()]

        for s in self.__stmts:
            try:
                s.normalize()
            except TypeNotFoundException as e:
                e.set_statement(s)
                raise e
        # not used yet
        # self.requires = set([require for s in self.__stmts for require in s.requires()])

        # self.external = self.requires - set(self.__variables)

        # self.external_not_global = [x for x in self.external if "::" not in x]

    #     def get_requires(self) -> List[str]:
    #         return self.external

    def get_eager_promises(self) -> Sequence[StaticEagerPromise]:
        """
        Returns the collection of eager promises for this block, i.e. promises parent scopes should acquire as a result of
        attribute assignments in or below this block.

        Should only be called after normalization.
        """
        declared_variables: Set[str] = set(self.get_variables())
        return [
            promise
            for statement in self.get_stmts()
            for promise in statement.get_all_eager_promises()
            if promise.get_root_variable() not in declared_variables
        ]

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
            warnings.warn(
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
        self,
        surrounding_vars: Optional[Dict[str, FrozenSet[Locatable]]] = None,
    ) -> Iterator[Tuple[str, FrozenSet[Locatable], FrozenSet[Locatable]]]:
        """
        Returns an iterator over variables shadowed in this block or its nested blocks.
        The elements are tuples of the variable name, a set of the shadowed locations
        and a set of the originally declared locations.
        :param surrounding_vars: an accumulator for variables declared in surrounding blocks.
        """
        if surrounding_vars is None:
            surrounding_vars = {}
        surrounding_vars = surrounding_vars.copy()

        def merge_locatables(tuples: Iterable[Tuple[str, Locatable]]) -> Dict[str, FrozenSet[Locatable]]:
            acc: Dict[str, FrozenSet[Locatable]] = {}
            for var, loc in tuples:
                if var not in acc:
                    acc[var] = frozenset(())
                acc[var] = acc[var].union({loc})
            return acc

        for var, locs in merge_locatables(self.__variables).items():
            if var in surrounding_vars:
                yield (var, locs, surrounding_vars[var])
            surrounding_vars[var] = locs

        yield from chain.from_iterable(
            block.shadowed_variables(surrounding_vars)
            for stmt in chain(self.__stmts, self.__definition_stmts)
            for block in stmt.nested_blocks()
        )
