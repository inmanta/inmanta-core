"""
    Copyright 2023 Inmanta

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

import abc
import logging
import re
from collections.abc import Sequence
from typing import Optional, TypeVar, Union, overload

from inmanta.stable_api import stable_api
from typing_extensions import TypeGuard

LOGGER = logging.getLogger(__name__)

TWDP = TypeVar("TWDP", bound="WildDictPath")
TWID = TypeVar("TWID", bound="WildInDict")
TWKL = TypeVar("TWKL", bound="WildKeyedList")
TWCP = TypeVar("TWCP", bound="WildComposedPath")


@stable_api
class InvalidPathException(Exception):
    """
    The path could not be parsed correctly.
    """


@stable_api
class ContainerStructureException(LookupError):
    """
    The requested item could not be found,
    because the container passed to this path is not of the expected type.
    """


@stable_api
class DictPathValue(abc.ABC):
    """
    Represents a data value part of a WildDictPath.
    """

    @abc.abstractmethod
    def escape(self) -> str:
        """
        Return this value with all special characters escaped.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def matches(self, value: Optional[object]) -> bool:
        """
        Return true iff the given value matches this value.
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def value(self) -> Optional[str]:
        """
        Return the unescaped data value.
        """
        raise NotImplementedError()

    @classmethod
    def create(cls, value: str) -> "DictPathValue":
        """
        Create a DictPathValue from the given value. Argument `value` must have all
        special characters escaped when their special meaning is not desired.
        """
        if value == WildCardValue.WILDCARD_CHARACTER:
            return WildCardValue()
        elif value == NullValue.NULL_VALUE_CHARACTER:
            return NullValue()
        else:
            unescaped_value: str = WildDictPath.PATTERN_ESCAPED_SPECIAL_CHARACTER.sub(r"\1", value)
            return NormalValue(unescaped_value)

    @classmethod
    def from_object(cls, value: object) -> "DictPathValue":
        """
        Create a DictPathValue from the given object.
        :param value: The object to construct a DictPathValue for. It is interpreted as a literal value: if it is a string,
            special characters will not be interpreted and must not be escaped. If it is not `None`, it must implement `str()`
            to be an unambiguous representation of the object.
        """
        if value is None:
            return NullValue()
        return NormalValue(str(value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__)


@stable_api
class NormalValue(DictPathValue):
    """
    A normal dict path value. This is a data value that is matched literally
    against another value.
    """

    def __init__(self, value: str) -> None:
        super(DictPathValue, self).__init__()
        self._value: str = value
        self._numeric_value: Optional[float] = self._try_parse_numeric(value)

    def escape(self) -> str:
        return WildDictPath.PATTERN_SPECIAL_CHARACTER.sub(r"\\\1", self._value)

    def matches(self, value: Optional[object]) -> bool:
        if value is None:
            return False

        # Perform a numeric comparison only if the value is an int/float and
        # The key in the dictpath can be interpreted as an int/float
        if self._numeric_value is not None and isinstance(value, (int, float)):
            return self._numeric_value == value

        # Fallback to string comparison for other types
        return self._value == str(value)

    @staticmethod
    def _try_parse_numeric(value: str) -> Optional[float]:
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NormalValue):
            return False
        return self.value == other.value


@stable_api
class WildCardValue(DictPathValue):
    """
    Represents a wildcard value. This is a data value that matches any other value.
    """

    WILDCARD_CHARACTER: str = "*"

    def escape(self) -> str:
        return self.WILDCARD_CHARACTER

    def matches(self, value: Optional[object]) -> bool:
        return True

    @property
    def value(self) -> str:
        raise Exception("A WildCardValue doesn't have an actual data value.")


@stable_api
class NullValue(DictPathValue):
    """
    Represents the data value None. Matches against any other None value.
    """

    NULL_VALUE_CHARACTER: str = r"\0"

    def escape(self) -> str:
        return self.NULL_VALUE_CHARACTER

    def matches(self, value: Optional[object]) -> bool:
        return value is None

    @property
    def value(self) -> None:
        return None


@stable_api
class WildDictPath(abc.ABC):
    """
    A base class for all dict paths segments.  It supports the usage of wildcards, allowing to reach
    multiple elements in the same Dict.

    The wildcard is the character "*", its usage for the different segment type is documented later.
    In the internal representation of this object, wildcards are represented using the value None.

    The special characters mentioned in `WildDictPath.SPECIAL_CHARACTERS` should be escaped using a
    backslash when its used as a data character (e.g. the value of a key in a dictionary) instead
    of a control character (a character used to guide the dictpath library). Other characters must
    never be escaped.
    """

    # Special characters should be escaped in data elements of the dict path
    # to prevent incorrect interpretation of the dict path.
    SPECIAL_CHARACTERS: list[str] = ["\\", "[", "]", ".", "*", "="]
    REGEX_SPECIAL_CHARACTER = rf"([{re.escape(''.join(SPECIAL_CHARACTERS))}])"
    PATTERN_SPECIAL_CHARACTER = re.compile(REGEX_SPECIAL_CHARACTER)
    REGEX_ESCAPED_SPECIAL_CHARACTER = rf"\\([{re.escape(''.join(SPECIAL_CHARACTERS))}])"
    PATTERN_ESCAPED_SPECIAL_CHARACTER = re.compile(REGEX_ESCAPED_SPECIAL_CHARACTER)
    REGEX_NORMAL_CHARACTER = rf"[^{re.escape(''.join(SPECIAL_CHARACTERS))}]"

    # Add the WILDCARD variable here for backwards compatibility
    WILDCARD = WildCardValue.WILDCARD_CHARACTER

    @abc.abstractmethod
    def get_elements(self, container: object) -> list[object]:
        """
        Get the elements identified by this Path from the given collection.
        If no element is matched, an empty list is returned.

        :param container: the container to search in
        """

    @abc.abstractmethod
    def to_str(self) -> str:
        """
        Returns the dict path expression represented by this instance.
        """

    def __str__(self) -> str:
        return self.to_str()

    def __add__(self, other: object) -> "WildDictPath":
        if not isinstance(other, WildDictPath):
            return NotImplemented
        return WildComposedPath(path=list(self.get_path_sections()) + list(other.get_path_sections()))

    @abc.abstractmethod
    def get_path_sections(self) -> Sequence["WildDictPath"]:
        """
        A DictPath can be a combination of multiple DictPaths, this returns all the DictPaths
        that compose this one, or itself if it is not a composition of multiple DictPaths.
        """

    @classmethod
    @abc.abstractmethod
    def parse(cls: type[TWDP], inp: str) -> Optional[TWDP]:
        pass

    def _validate_container(self, container: object) -> TypeGuard[dict[object, object]]:
        return isinstance(container, dict)


@stable_api
class WildInDict(WildDictPath):
    """
    This is the path that, if you call get_element on a dict, it returns the value stored in
    that key in that dict. This class accepts only top level keys as its expression.

    The string representation of the following path element is `a`

    .. code_block:: python

        assert WildInDict("a").get_elements(
        {
            "a":"b",
            "c":"d",
        }) == ["b"]

    A wild card can be used to get all values from the dict.  The wildcard only works as a single character.

    .. code_block:: python

        assert WildInDict("*").get_elements(
            {
                "a":"b",
                "c":"d",
            }
        ) == ["b", "d"]

    The following code raises a KeyError.

    .. code_block:: python

        WildInDict("a*").get_elements(
            {
                "a":"b",
                "c":"d",
            }
        )

    """

    IN_DICT_PATTERN = re.compile(
        rf"(?P<key>({WildDictPath.REGEX_NORMAL_CHARACTER}|{WildDictPath.REGEX_ESCAPED_SPECIAL_CHARACTER})+|\*)"
    )

    def __init__(self, key: str) -> None:
        key_value = DictPathValue.create(key)
        if not isinstance(key_value, NormalValue) and not isinstance(key_value, WildCardValue):
            raise InvalidPathException(f"Invalid dictionary key {key}")
        self.key: Union[NormalValue, WildCardValue] = key_value

    def get_elements(self, container: object) -> list[object]:
        if self._validate_container(container):
            try:
                return [value for key, value in container.items() if self.key.matches(key)]
            except KeyError:
                return []
        else:
            raise ContainerStructureException(f"{container} is not a Dict")

    def to_str(self) -> str:
        return self.key.escape()

    def get_path_sections(self) -> Sequence[WildDictPath]:
        return [self]

    @classmethod
    def parse(cls: type[TWID], inp: str) -> Optional[TWID]:
        match = cls.IN_DICT_PATTERN.fullmatch(inp)
        if match:
            return cls(inp)
        return None


@stable_api
class WildKeyedList(WildDictPath):
    """
    Find a specific item in a list, based on a key-value pair.
    The list is in a dictionary itself.

    The string representation of the following path element is `relation[key_attribute=key_value]`
    A wild card can be used to get all values from the list having the key_attribute.

    e.g.::

        WildKeyedList("relation","key_attribute","key_value").get_elements(
        {
            "relation":[
                {
                    "key_attribute":"key_value",
                    "other_attribute":"other_value"
                },
                {
                    "key_attribute":"other_value"
                }
            [
        })

    will return::

        [
            {
                "key_attribute":"key_value",
                "other_attribute":"other_value"
            }
        ]

    e.g.::

        WildKeyedList("relation","key_attribute","*").get_elements(
        {
            "relation":[
                {
                    "key_attribute":"key_value",
                    "other_attribute":"other_value",
                },
                {
                    "key_attribute":"other_value",
                },
                {
                    "other_key_attribute":"other_value",
                },
            [
        })

    will return::

        [
            {
                "key_attribute":"key_value",
                "other_attribute":"other_value",
            },
            {
                "key_attribute":"other_value",
            }
        ]

    """

    REGEX_RELATION = rf"(?P<relation>({WildDictPath.REGEX_NORMAL_CHARACTER}|{WildDictPath.REGEX_ESCAPED_SPECIAL_CHARACTER})+)"
    REGEX_KEY_ATTRIBUTE = (
        rf"(?P<key_attribute>({WildDictPath.REGEX_NORMAL_CHARACTER}|{WildDictPath.REGEX_ESCAPED_SPECIAL_CHARACTER})+|\*)"
    )
    REGEX_KEY_VALUE = (
        rf"(?P<key_value>({WildDictPath.REGEX_NORMAL_CHARACTER}|{WildDictPath.REGEX_ESCAPED_SPECIAL_CHARACTER})*|\*|\\0)"
    )
    KEY_VALUE_PAIR = rf"\[{REGEX_KEY_ATTRIBUTE}={REGEX_KEY_VALUE}]"

    KEYED_LIST_PATTERN = re.compile(rf"^{REGEX_RELATION}(?P<selectors>({KEY_VALUE_PAIR})+)$")
    KEY_VALUE_PAIRS_PATTERN = re.compile(KEY_VALUE_PAIR)

    @overload
    def __init__(self, relation: str, key_value_pairs: Sequence[tuple[str, str]]) -> None:
        """
        :param relation: The relation on the object that is the keyed list
        :param key_value_pairs: The key-value pairs to look for in each item of the keyed list.
            The key is compared using string comparison. As such 5=="5" and False=="False"
        """
        ...

    @overload
    def __init__(self, relation: str, key_attribute: str, key_value: str, /) -> None:
        """
        Deprecated constructor, kept for backwards compatibility reasons.

        :param relation: The relation on the object that is the keyed list
        :param key_attribute: The attribute to look for in each item of the keyed list
        :param key_value: The attribute value to look for in each item of the keyed list.
        """

    def __init__(
        self, relation: str, key_value_pairs: Union[str, Sequence[tuple[str, str]]], key_value: Optional[str] = None
    ) -> None:
        if isinstance(key_value_pairs, str):
            LOGGER.warning(
                "The %s(relation: str, key_attribute: str, key_value: str, /) constructor is deprecated and will be removed"
                " in a future version. Please use %s(relation: str, key_value_pairs: Sequence[Tuple[str, str]]) instead",
                self.__class__.__name__,
                self.__class__.__name__,
            )
            assert key_value is not None
            key_value_pairs = [(key_value_pairs, key_value)]
        relation_value = DictPathValue.create(relation)
        if not isinstance(relation_value, NormalValue):
            raise InvalidPathException(f"Invalid relation name: {relation}")
        self.relation: NormalValue = relation_value

        if not key_value_pairs:
            raise ValueError("A keyed list path requires at least one key-value pair.")
        if len({pair[0] for pair in key_value_pairs}) != len(key_value_pairs):
            raise ValueError("No duplicate keys allowed in keyed list path")

        self.key_value_pairs: Sequence[tuple[Union[NormalValue, WildCardValue], DictPathValue]] = [
            (self._parse_key(pair[0]), self._parse_value(pair[1])) for pair in key_value_pairs
        ]

    @classmethod
    def _parse_key(cls, key: str) -> Union[NormalValue, WildCardValue]:
        """
        Parse a key string into the corresponding dict path object.
        """
        result: DictPathValue = DictPathValue.create(key)
        if not isinstance(result, NormalValue) and not isinstance(result, WildCardValue):
            raise InvalidPathException(f"Invalid dictionary key name: {key}")
        return result

    @classmethod
    def _parse_value(cls, value: str) -> DictPathValue:
        """
        Parse a value string into the corresponding dict path object.
        """
        return DictPathValue.create(value)

    def _validate_outer_container(self, container: object) -> dict[object, object]:
        if not isinstance(container, dict):
            raise ContainerStructureException(f"{container} is not a Dict")
        return container

    def _validate_inner_container(self, container: object) -> list[object]:
        if not isinstance(container, list):
            raise ContainerStructureException(f"{container} is not a List or Set")
        return container

    def get_elements(self, container: object) -> list[object]:
        outer = self._validate_outer_container(container)
        try:
            inner = outer[self.relation.value]
        except KeyError:
            return []
        the_list = self._validate_inner_container(inner)
        return [
            dct
            for dct in the_list
            if isinstance(dct, dict)
            and all(any(key.matches(k) and value.matches(v) for k, v in dct.items()) for key, value in self.key_value_pairs)
        ]

    def to_str(self) -> str:
        escaped_relation: str = self.relation.escape()
        escaped_key_value_pairs: str = "][".join(key.escape() + "=" + value.escape() for key, value in self.key_value_pairs)
        return f"{escaped_relation}[{escaped_key_value_pairs}]"

    def get_path_sections(self) -> Sequence[WildDictPath]:
        return [self]

    @classmethod
    def parse(cls: type[TWKL], inp: str) -> Optional[TWKL]:
        match = cls.KEYED_LIST_PATTERN.fullmatch(inp)
        if match:
            group_dct = match.groupdict()
            pairs: list[tuple[str, str]] = [
                (pair.group("key_attribute"), pair.group("key_value"))
                for pair in cls.KEY_VALUE_PAIRS_PATTERN.finditer(group_dct["selectors"])
            ]
            return cls(group_dct["relation"], pairs)
        return None

    def get_key_value_pairs(self) -> Sequence[tuple[str, Optional[str]]]:
        """
        Return a list of tuples, where each element in the list is a literal (unescaped) key-value pair for this WildKeyedList.
        """
        return [(key.value, value.value) for key, value in self.key_value_pairs]

    def __eq__(self, other: object) -> bool:
        if other.__class__ != self.__class__:
            return False
        assert isinstance(other, WildKeyedList)  # Make mypy happy
        return self.relation == other.relation and self.key_value_pairs == other.key_value_pairs


@stable_api
class WildComposedPath(WildDictPath):
    """
    A path composed of multiple elements, separated by "."
    """

    element_types: Sequence[type[WildDictPath]] = [WildInDict, WildKeyedList]
    COMPOSED_DICT_PATH_PATTERN = re.compile(r"(?:[^.\\]|\\.)+")

    def __init__(self, path_str: Optional[str] = None, path: Optional[Sequence[WildDictPath]] = None) -> None:
        if (path_str is None) == (path is None):
            raise ValueError("Either path or path_str should be set")

        self.path: str
        self.expanded_path: Sequence[WildDictPath]
        if path_str is not None:
            self.path = path_str
            self.expanded_path = self.do_parse(path_str)
        else:
            assert path is not None
            self.expanded_path = path
            self.path = self.un_parse()

    def un_parse(self) -> str:
        return ".".join(element.to_str() for element in self.expanded_path)

    @classmethod
    def split_on_dots(cls, path_str: str) -> list[str]:
        """
        Split the given `path_str` on dot characters if they are not escaped with a backslash.
        """
        match = cls.COMPOSED_DICT_PATH_PATTERN.findall(path_str)
        if not match:
            raise InvalidPathException(f"Could not parse path {path_str}")
        return match

    @classmethod
    def do_parse(cls, path_str: str) -> Sequence[WildDictPath]:
        splitted_path_str: list[str] = cls.split_on_dots(path_str)

        def parse_element(inp: str) -> WildDictPath:
            for subtype in cls.element_types:
                parsed = subtype.parse(inp)
                if parsed is not None:
                    return parsed
            raise InvalidPathException(f"Could not parse path segment {inp}")

        return [parse_element(e) for e in splitted_path_str]

    @classmethod
    def parse(cls: type[TWCP], inp: str) -> Optional[TWCP]:
        try:
            path = cls.do_parse(path_str=inp)
            return cls(path=path)
        except InvalidPathException:
            return None

    def get_elements(self, container: object) -> list[object]:
        if container is None:
            raise IndexError("Can not get anything from None")

        containers = [container]
        for item in self.expanded_path:
            next_containers = []
            for container in containers:
                next_containers.extend(item.get_elements(container))

            containers = next_containers

        return containers

    def to_str(self) -> str:
        return self.path

    def get_path_sections(self) -> Sequence[WildDictPath]:
        return self.expanded_path

    def __eq__(self, other: object) -> bool:
        if other.__class__ != self.__class__:
            return False
        assert isinstance(other, type(self)), f"{type(other)} != {type(self)}"  # Make mypy happy
        return self.expanded_path == other.expanded_path


@stable_api
class WildNullPath(WildDictPath):
    """
    A DictPath with no length

    (i.e. return the container itself, wrapped in a list)
    """

    def get_elements(self, container: object) -> list[object]:
        if self._validate_container(container):
            return [container]
        else:
            raise ContainerStructureException(f"{container} is not a Dict")

    def get_path_sections(self) -> Sequence["DictPath"]:
        return []

    def to_str(self) -> str:
        return "."

    @classmethod
    def parse(cls, inp: str) -> None:
        raise NotImplementedError("NullPath is not intended to be parseable, it should only be used programmatically.")


@stable_api
class DictPath(WildDictPath):
    """
    A base class for all non-wild dict paths segments.  The key difference between WildDictPath and DictPath subclasses are:
     1. WildDictPath can only get a list of elements, with get_elements.  If no element is found, an empty list is returned,
        no error is raised.
     2. DictPath can not use get_elements as it is always expected to have exactly one match.
     3. DictPath can use get_element, which will return the matching element, or raise an exception if more or less than one
        is found.
     4. DictPath can set values, using set_element, and can build the dict structure expected by the path by using the
        construct flag in the get_element method.
    """

    @abc.abstractmethod
    def get_element(self, container: object, construct: bool = False) -> object:
        """
        Get the element identified by this Path from the given collection

        :param container: the container to search in
        :param construct: construct a dict on the location identified by this path in the container
                          if the element doesn't exist. Return this new dict.

        :raises KeyError: if the element is not found or if more than one occurrence was found.
        """

    def get_elements(self, container: object) -> list[object]:
        try:
            return [self.get_element(container, False)]
        except LookupError:
            return []

    @abc.abstractmethod
    def set_element(self, container: object, value: object, construct: bool = True) -> None:
        """
        Set the element identified by this Path from the given collection.

        If construct is True, all containers on the path towards the value are constructed if absent.

        :raises LookupError: if the path leading to the element is not found or if more than one occurrence was found.
        """

    def __add__(self, other: object) -> "DictPath":
        if not isinstance(other, DictPath):
            return NotImplemented
        return ComposedPath(path=list(self.get_path_sections()) + list(other.get_path_sections()))

    def get_path_sections(self) -> Sequence["DictPath"]:
        """Get the individual parts of this path"""
        return []

    @abc.abstractmethod
    def get_key(self) -> str:
        """
        Return the dictionary key referenced by this element in the dict path.
        """

    @abc.abstractmethod
    def remove(self, container: object) -> None:
        """
        Remove an element if it exists:
            * On an InDict or a WildInDict: Remove the referenced key from the dictionary.
            * On a KeyedList or a WildKeyedList: Remove the referenced element from the list.
            * On a NullPath: This operation is not supported on a NullPath.
        """
        raise NotImplementedError()


@stable_api
class InDict(DictPath, WildInDict):
    """
    This is the path that, if you call get_element on a dict, it returns the value stored in that key in that dict.

    The string representation of the following path element is: "a"

    .. code_block:: python

        assert InDict("a").get_element(
        {
            "a":"b",
            "c":"d",
        }) == "b"

    """

    def __init__(self, key: str) -> None:
        WildInDict.__init__(self, key)
        if isinstance(self.key, WildCardValue):
            raise ValueError(f"The Wildcard ('{WildCardValue.WILDCARD_CHARACTER}') can not be used in DictPath's")
        # Override type annotation from super class
        self.key: NormalValue

    def get_element(self, container: object, construct: bool = False) -> object:
        elements = WildInDict.get_elements(self, container)

        if not elements and construct:
            if self._validate_container(container):
                container[self.key.value] = {}
                return container[self.key.value]
            else:
                raise ContainerStructureException(f"{container} is not a Dict")

        if len(elements) != 1:
            raise KeyError(f"Found no or multiple items matching {self.to_str()} in {container}: {elements}")

        return elements[0]

    def set_element(self, container: object, value: object, construct: bool = True) -> None:
        if self._validate_container(container):
            container[self.key.value] = value
        else:
            raise ContainerStructureException(f"{container} is not a Dict")

    def get_path_sections(self) -> Sequence[DictPath]:
        return [self]

    def get_key(self) -> str:
        return self.key.value

    def remove(self, container: object) -> None:
        if self._validate_container(container):
            for key in list(container.keys()):
                if self.key.matches(key):
                    del container[key]
        else:
            raise ContainerStructureException(f"{container} is not a Dict")


@stable_api
class KeyedList(DictPath, WildKeyedList):
    """
    Find a specific item in a list, based on a key-value pair.
    The list is in a dictionary itself.

    The string representation of the following path element is `relation[key_attribute=key_value]`

    e.g.::

        KeyedList("relation","key_attribute","key_value").get_element(
        {
            "relation":[
                {
                    "key_attribute":"key_value",
                    "other_attribute":"other_value"
                },
                {
                    "key_attribute":"other_value"
                }
            [
        })

    will return::

        {
            "key_attribute":"key_value",
            "other_attribute":"other_value"
        }

    """

    def __init__(
        self, relation: str, key_value_pairs: Union[str, Sequence[tuple[str, str]]], key_value: Optional[str] = None
    ) -> None:
        if isinstance(key_value_pairs, str):
            assert key_value is not None
            WildKeyedList.__init__(self, relation, key_value_pairs, key_value)
        else:
            assert key_value is None
            WildKeyedList.__init__(self, relation, key_value_pairs)
        # Override type annotation from super class
        self.key_value_pairs: Sequence[tuple[NormalValue, Union[NormalValue, NullValue]]]

    @classmethod
    def _parse_key(cls, key: str) -> NormalValue:
        result: Union[NormalValue, WildCardValue] = super()._parse_key(key)
        if isinstance(result, WildCardValue):
            raise ValueError(f"The Wildcard ('{WildCardValue.WILDCARD_CHARACTER}') can not be used in DictPath's")
        return result

    @classmethod
    def _parse_value(cls, value: str) -> DictPathValue:
        """
        Parse a value string into the corresponding dict path object.
        """
        result: DictPathValue = super()._parse_value(value)
        if isinstance(result, WildCardValue):
            raise ValueError(f"The Wildcard ('{WildCardValue.WILDCARD_CHARACTER}') can not be used in DictPath's")
        return result

    def get_element(self, container: object, construct: bool = False) -> object:
        found = WildKeyedList.get_elements(self, container)

        if not found and construct:
            outer = self._validate_outer_container(container)
            if self.relation.value not in outer:
                outer[self.relation.value] = []
            the_list = self._validate_inner_container(outer[self.relation.value])
            new_dict: dict[Optional[str], Optional[str]] = {key.value: value.value for key, value in self.key_value_pairs}
            the_list.append(new_dict)
            return new_dict

        if len(found) != 1:
            raise KeyError(f"Found no or multiple items matching {self.to_str()} in {container}: {found}")
        return found[0]

    def set_element(self, container: object, value: object, construct: bool = True) -> None:
        outer: dict[object, object] = self._validate_outer_container(container)
        try:
            inner = outer[self.relation.value]
        except KeyError:
            inner = []
            outer[self.relation.value] = inner

        the_list: list[object] = self._validate_inner_container(inner)
        try:
            element_to_be_replaced: object = self.get_element(container, construct=False)
        except KeyError:
            the_list.append(value)
        else:
            index = the_list.index(element_to_be_replaced)
            the_list[index] = value

    def get_path_sections(self) -> Sequence[DictPath]:
        return [self]

    def get_key(self) -> str:
        return self.relation.value

    def remove(self, container: object) -> None:
        outer = self._validate_outer_container(container)
        try:
            inner = outer[self.relation.value]
        except KeyError:
            return
        the_list = self._validate_inner_container(inner)
        outer[self.relation.value] = [
            dct
            for dct in the_list
            if not isinstance(dct, dict)
            or not all(any(key.matches(k) and value.matches(v) for k, v in dct.items()) for key, value in self.key_value_pairs)
        ]


@stable_api
class ComposedPath(DictPath, WildComposedPath):
    """
    A path composed of multiple elements, separated by "."
    """

    element_types: Sequence[type[DictPath]] = [InDict, KeyedList]

    def __init__(self, path_str: Optional[str] = None, path: Optional[Sequence[DictPath]] = None) -> None:
        WildComposedPath.__init__(self, path_str, path)
        self.expanded_path: Sequence[DictPath]

    def get_element(self, container: object, construct: bool = False) -> object:
        elements = WildComposedPath.get_elements(self, container)

        if not elements and construct:
            element = container
            for item in self.get_path_sections():
                element = item.get_element(element, True)

            return element

        if len(elements) != 1:
            raise KeyError(f"Found no or multiple items matching {self.to_str()} in {container}: {elements}")

        return elements[0]

    def set_element(self, container: object, value: object, construct: bool = True) -> None:
        for item in self.get_path_sections()[:-1]:
            container = item.get_element(container, construct=construct)

        self.get_path_sections()[-1].set_element(container, value)

    def get_path_sections(self) -> Sequence[DictPath]:
        return self.expanded_path

    def get_key(self) -> str:
        raise NotImplementedError("Method get_key() not supported on a ComposedPath")

    def remove(self, container: object) -> None:
        for item in self.get_path_sections()[:-1]:
            try:
                container = item.get_element(container, construct=False)
            except KeyError:
                return

        self.get_path_sections()[-1].remove(container)


@stable_api
class NullPath(DictPath, WildNullPath):
    """
    A DictPath with no length

    (i.e. return the container itself)
    """

    def get_element(self, container: object, construct: bool = False) -> dict[object, object]:
        if self._validate_container(container):
            return container
        else:
            raise ContainerStructureException(f"{container} is not a Dict")

    def set_element(self, container: object, value: object, construct: bool = True) -> None:
        if not self._validate_container(container):
            raise ContainerStructureException(f"Argument container is not a Dict: {container}")
        if not self._validate_container(value):
            raise ContainerStructureException(f"Argument value is not a Dict: {container}")
        assert isinstance(container, dict)
        assert isinstance(value, dict)
        container.clear()
        for key, value in value.items():
            container[key] = value

    @classmethod
    def parse(cls, inp: str) -> None:
        raise NotImplementedError("NullPath is not intended to be parseable, it should only be used programmatically.")

    def get_key(self) -> str:
        raise NotImplementedError("Method get_key() is not supported on a NullPath")

    def remove(self, container: object) -> None:
        raise NotImplementedError("Method remove() is not supported on a NullPath")


@stable_api
def to_wild_path(inp: str) -> WildDictPath:
    """
    Convert a string to a WildDictPath

    :raises InvalidPathException: the path is not valid
    """
    if inp == ".":
        return WildNullPath()
    if inp.startswith("."):
        # A leading dot represents the entire container
        inp = inp[1:]
    try:
        return WildComposedPath(path_str=inp)
    except ValueError as e:
        raise InvalidPathException(str(e))


@stable_api
def to_path(inp: str) -> DictPath:
    """
    Convert a string to a DictPath

    :raises InvalidPathException: the path is not valid
    """
    if inp == ".":
        return NullPath()
    if inp.startswith("."):
        # A leading dot represents the entire container
        inp = inp[1:]
    try:
        return ComposedPath(path_str=inp)
    except ValueError as e:
        raise InvalidPathException(str(e))
