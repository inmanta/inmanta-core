"""
    Copyright 2024 Inmanta

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

from typing import Generic, Optional, Self, TypeVar
from collections.abc import Hashable, Iterator, MutableMapping, Set


P = TypeVar("P", bound=Hashable)
S = TypeVar("S", bound=Hashable)
# type vars not bound to the class
K = TypeVar("K", bound=Hashable)
V = TypeVar("V", bound=Hashable)


# TODO: review


# TODO: better name?
class BidirectionalManyToManyMapping(MutableMapping[P, Set[S]], Generic[P, S]):
    def __init__(self) -> None:
        # TODO: better names than primary and secondary?
        self._primary: dict[P, set[S]] = {}
        self._secondary: dict[S, set[P]] = {}

    @staticmethod
    def _set(primary: dict[K, set[V]], secondary: dict[V, set[K]], key: K, values: Set[V]) -> None:
        current: Set[V] = primary.get(key, set())
        new: Set[V] = values - current
        missing: Set[V] = current - values

        # update primary
        primary[key] = set(values)

        # update secondary
        v: V
        for v in new:
            if v not in secondary:
                secondary[v] = set()
            secondary[v].add(key)
        for v in missing:
            secondary[v].remove(key)
            if not secondary[v]:
                del secondary[v]

    def set_primary(self, key: P, values: Set[S]) -> None:
        self._set(self._primary, self._secondary, key, values)

    def set_secondary(self, key: S, values: Set[P]) -> None:
        self._set(self._secondary, self._primary, key, values)

    def reverse_mapping(self) -> "BidirectionalManyToManyMapping[S, P]":
        # TODO: docstring: mention that it remains coupled
        return _BidirectionalManyToManyMappingReverse(self)

    def get_primary(self, key: P, default: Optional[Set[S]] = None) -> Optional[Set[S]]:
        return self._primary.get(key, default)

    def get_secondary(self, key: S, default: Optional[Set[P]] = None) -> Optional[Set[P]]:
        return self._secondary.get(key, default)

    # Implement MutableMapping interface

    def __getitem__(self, key: P) -> Set[S]:
        return self._primary.__getitem__(key)

    def __setitem__(self, key: P, value: Set[S]) -> None:
        self.set_primary(key, value)

    def __delitem__(self, key: P) -> None:
        if key not in self._primary:
            raise KeyError(key)
        # trim reverse mapping
        self.set_primary(key, set())
        # delete from primary mapping
        del self._primary[key]

    def __iter__(self) -> Iterator[P]:
        return iter(self._primary)

    def __len__(self) -> int:
        return len(self._primary)


class _BidirectionalManyToManyMappingReverse(BidirectionalManyToManyMapping[S, P], Generic[P, S]):
    def __init__(self, base: BidirectionalManyToManyMapping[P, S]) -> None:
        self._base = base
        self._primary = self._base._secondary
        self._secondary = self._base._primary

    def reverse(self) -> BidirectionalManyToManyMapping[P, S]:
        return self._base
