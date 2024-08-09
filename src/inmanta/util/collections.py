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
# TODO: unit tests


# TODO: better name?
class BidirectionalManyToManyMapping(MutableMapping[P, Set[S]], Generic[P, S]):
    # TODO: docstring + mention that it only supports methods on the mapping, not on the underlying sets
    def __init__(self, mapping: Optional[Mapping[P, Set[S]]] = None) -> None:
        self._primary: dict[P, set[S]] = {}
        self._reverse: dict[S, set[P]] = {}
        if mapping is not None:
            for key, values in mapping.items():
                self.set_primary(key, values)

    @staticmethod
    def _set(primary: dict[K, set[V]], reverse: dict[V, set[K]], key: K, values: Set[V]) -> None:
        current: Set[V] = primary.get(key, set())
        new: Set[V] = values - current
        missing: Set[V] = current - values

        # update primary
        primary[key] = set(values)

        # update reverse
        v: V
        for v in new:
            if v not in reverse:
                reverse[v] = set()
            reverse[v].add(key)
        for v in missing:
            reverse[v].remove(key)
            if not reverse[v]:
                del reverse[v]

    def set_primary(self, key: P, values: Set[S]) -> None:
        self._set(self._primary, self._reverse, key, values)

    def set_reverse(self, key: S, values: Set[P]) -> None:
        self._set(self._reverse, self._primary, key, values)

    def reverse_mapping(self) -> "BidirectionalManyToManyMapping[S, P]":
        # TODO: docstring: mention that it remains coupled
        return _BidirectionalManyToManyMappingReverse(self)

    def get_primary(self, key: P, default: Optional[Set[S]] = None) -> Optional[Set[S]]:
        return self._primary.get(key, default)

    def get_reverse(self, key: S, default: Optional[Set[P]] = None) -> Optional[Set[P]]:
        return self._reverse.get(key, default)

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

    def __repr__(self) -> str:
        return f"BidirectionalManyToManyMapping({self._primary!r})"

    def __str__(self) -> str:
        return str(self._primary)


class _BidirectionalManyToManyMappingReverse(BidirectionalManyToManyMapping[S, P], Generic[P, S]):
    def __init__(self, base: BidirectionalManyToManyMapping[P, S]) -> None:
        self._base = base
        self._primary = self._base._reverse
        self._reverse = self._base._primary

    def reverse(self) -> BidirectionalManyToManyMapping[P, S]:
        return self._base


# TODO: drop or move to test case
import math
import random
import time
from collections.abc import Mapping
from dataclasses import dataclass

@dataclass
class ScalingTest:
    size: int
    nb_targets: int
    nb_updates: int

    @staticmethod
    def generate_mapping(*, size: int, nb_targets: int, target_range: Optional[int] = None) -> dict[int, set[int]]:
        return {
            i: {random.randint(1, target_range if target_range is not None else size) for _ in range(nb_targets)}
            for i in range(size)
        }

    def test(self) -> None:
        init_mapping: Mapping[int, Set[int]] = self.generate_mapping(size=self.size, nb_targets=self.nb_targets)
        updates: Mapping[int, Set[int]] = self.generate_mapping(
            size=self.nb_updates, nb_targets=self.nb_targets, target_range=self.size
        )

        m: BidirectionalManyToManyMapping[int, int] = BidirectionalManyToManyMapping()
        time_start: float = time.process_time()
        for k, v in init_mapping.items():
            m[k] = v
        time_populated: float = time.process_time()
        for k, v in updates.items():
            m[k] = v
        time_updated: float = time.process_time()

        print(
            f"Initial population with {self.size} items with {self.nb_targets} each: {time_populated - time_start},"
            f" update: of {self.nb_updates} items: {time_updated - time_populated}."
        )


ScalingTest(size=100, nb_targets=10, nb_updates=10).test()
ScalingTest(size=100_000, nb_targets=10, nb_updates=100).test()
ScalingTest(size=100_000, nb_targets=10, nb_updates=1_000).test()
ScalingTest(size=100_000, nb_targets=10, nb_updates=10_000).test()
ScalingTest(size=100_000, nb_targets=10, nb_updates=100_000).test()
ScalingTest(size=1_000_000, nb_targets=5, nb_updates=1_000).test()
ScalingTest(size=1_000_000, nb_targets=10, nb_updates=1_000).test()
ScalingTest(size=10_000, nb_targets=10_000, nb_updates=10).test()
