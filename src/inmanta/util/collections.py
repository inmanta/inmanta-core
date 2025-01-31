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

from collections.abc import Hashable, Iterator, Mapping, MutableMapping, Set
from typing import Generic, Optional, TypeVar

S = TypeVar("S", bound=Hashable)
T = TypeVar("T", bound=Hashable)
# type vars not bound to the class
K = TypeVar("K", bound=Hashable)
V = TypeVar("V", bound=Hashable)


class BidirectionalManyMapping(MutableMapping[S, Set[T]], Generic[S, T]):
    """
    A mutable bidirectional mapping many-to-many mapping between two value domains. All operations uphold the bidirectional
    invariant.

    e.g. if a value s maps to t1 and t2, then both t1 and t2 will include s in the reverse mapping. This property holds in both
    directions.

    While this is a mutable mapping, mutations on the underlying sets are not supported.
    """

    def __init__(self, mapping: Optional[Mapping[S, Set[T]]] = None) -> None:
        self._primary: dict[S, set[T]] = {}
        self._reverse: dict[T, set[S]] = {}
        if mapping is not None:
            for key, values in mapping.items():
                self[key] = values

    @staticmethod
    def _set(primary: dict[K, set[V]], reverse: dict[V, set[K]], key: K, values: Set[V]) -> None:
        """
        Set the key-value pair on the primary dict and update the reverse mapping to uphold the bidirectionality.

        :param primary: The dict to consider as primary for this set operation, i.e. the one to set the key-value pair on.
        :param reverse: The dict to consider as secondary for this set operation, i.e. the one to apply the reverse key-value
            mapping on (may include deleting edges that were dropped from the primary mapping).
        """
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

    # MutableMapping interface

    def __getitem__(self, key: S) -> Set[T]:
        return self._primary.__getitem__(key)

    def __setitem__(self, key: S, value: Set[T]) -> None:
        self._set(self._primary, self._reverse, key, value)

    def __delitem__(self, key: S) -> None:
        """
        Delete item from this end of the mapping.
        """
        if key not in self._primary:
            raise KeyError(key)
        # trim reverse mapping
        self[key] = set()
        # delete from primary mapping
        del self._primary[key]

    def __iter__(self) -> Iterator[S]:
        return iter(self._primary)

    def __len__(self) -> int:
        return len(self._primary)

    def __repr__(self) -> str:
        # show both directions because empty sets are only visible on one end
        return f"BidirectionalManyMapping(primary={self._primary!r}, reverse={self._reverse!r})"

    def __str__(self) -> str:
        return str(self._primary)

    # Methods for reverse access

    def reverse_mapping(self) -> "BidirectionalManyMapping[T, S]":
        """
        Return a BidirectionalManyMapping coupled to this one to represent the reverse mapping. The instance remains coupled
        with this one, meaning that changes to one are reflected to the other, i.e. they're mutable views on both sides of the
        same bidirectional mapping.

        This method is symmetric, i.e. `self.reverse_mapping().reverse_mapping() is self`
        """
        return _BidirectionalManyToManyMappingReverse(self)

    def get_reverse(self, key: T, default: Optional[Set[S]] = None) -> Optional[Set[S]]:
        """
        Return the values associated with the given key in the reverse mapping.

        Equivalent to `self.reverse_mapping()[key].get()`
        """
        return self._reverse.get(key, default)

    def set_reverse(self, key: T, values: Set[S]) -> None:
        """
        Set new values for the key in the reverse mapping. Old values are completely replaced and the primary mapping is
        updated accordingly.

        Equivalent to `self.reverse_mapping()[key] = values`
        """
        self._set(self._reverse, self._primary, key, values)


class _BidirectionalManyToManyMappingReverse(BidirectionalManyMapping[T, S], Generic[S, T]):
    def __init__(self, base: BidirectionalManyMapping[S, T]) -> None:
        self._base = base
        self._primary = self._base._reverse
        self._reverse = self._base._primary

    def reverse_mapping(self) -> BidirectionalManyMapping[S, T]:
        return self._base
