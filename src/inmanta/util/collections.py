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

P = TypeVar("P", bound=Hashable)
S = TypeVar("S", bound=Hashable)
# type vars not bound to the class
K = TypeVar("K", bound=Hashable)
V = TypeVar("V", bound=Hashable)


class BidirectionalManyMapping(MutableMapping[P, Set[S]], Generic[P, S]):
    """
    A mutable bidirectional mapping many-to-many mapping between two value domains.

    e.g. if a value x maps to y1 and y2, then both y1 and y2 will include x in the reverse mapping. This property holds in both
    directions.

    While this is a mutable mapping, mutations on the underlying sets are not supported.
    """
    def __init__(self, mapping: Optional[Mapping[P, Set[S]]] = None) -> None:
        self._primary: dict[P, set[S]] = {}
        self._reverse: dict[S, set[P]] = {}
        if mapping is not None:
            for key, values in mapping.items():
                self[key] = values

    @staticmethod
    def _set(primary: dict[K, set[V]], reverse: dict[V, set[K]], key: K, values: Set[V]) -> None:
        """
        Set the key-value pair on the primary dict and update the reverse mapping to uphold the bidirectionality.

        :param primary: The dict to consider as primary for this set operation, i.e. the one to set the key-value pair on.
        :param primary: The dict to consider as secondary for this set operation, i.e. the one to apply the reverse key-value
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

    def __getitem__(self, key: P) -> Set[S]:
        return self._primary.__getitem__(key)

    def __setitem__(self, key: P, value: Set[S]) -> None:
        self._set(self._primary, self._reverse, key, value)

    def __delitem__(self, key: P) -> None:
        """
        Delete item from this end of the mapping.
        """
        if key not in self._primary:
            raise KeyError(key)
        # trim reverse mapping
        self[key] = set()
        # delete from primary mapping
        del self._primary[key]

    def __iter__(self) -> Iterator[P]:
        return iter(self._primary)

    def __len__(self) -> int:
        return len(self._primary)

    def __repr__(self) -> str:
        # show both directions because empty sets are only visible on one end
        return f"BidirectionalManyMapping(primary={self._primary!r}, reverse={self._reverse!r})"

    def __str__(self) -> str:
        return str(self._primary)

    # Methods for reverse access

    def reverse_mapping(self) -> "BidirectionalManyMapping[S, P]":
        """
        Return a BidirectionalManyMapping coupled to this one to represent the reverse mapping. The instance remains coupled
        with this one, meaning that changes to one are reflected to the other, i.e. they're mutable views on both sides of the
        same bidirectional mapping.
        """
        return _BidirectionalManyToManyMappingReverse(self)

    def get_reverse(self, key: S, default: Optional[Set[P]] = None) -> Optional[Set[P]]:
        """
        Return the values associated with the given key in the reverse mapping.

        Equivalent to `self.reverse_mapping()[key].get()`
        """
        return self._reverse.get(key, default)

    def set_reverse(self, key: S, values: Set[P]) -> None:
        """
        Set new values for the key in the reverse mapping. Old values are completely replaced and the primary mapping is
        updated accordingly.

        Equivalent to `self.reverse_mapping()[key] = values`
        """
        self._set(self._reverse, self._primary, key, values)


class _BidirectionalManyToManyMappingReverse(BidirectionalManyMapping[S, P], Generic[P, S]):
    def __init__(self, base: BidirectionalManyMapping[P, S]) -> None:
        self._base = base
        self._primary = self._base._reverse
        self._reverse = self._base._primary

    def reverse_mapping(self) -> BidirectionalManyMapping[P, S]:
        return self._base
