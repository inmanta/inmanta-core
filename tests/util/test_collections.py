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

import pytest

from inmanta.util.collections import BidirectionalManyMapping


def test_bidirectional_many_mapping() -> None:
    """
    Verify the behavior of the BidirectionalManyMapping class and its core functionality
    """
    plain_mapping: dict[str, set[int]] = {
        "digit": set(range(10)),
        "even": {0, 2, 4, 42},
        "significant": {0, 1, 42},
    }
    plain_reverse: dict[int, set[str]] = {
        0: {"digit", "even", "significant"},
        1: {"digit", "significant"},
        2: {"digit", "even"},
        3: {"digit"},
        4: {"digit", "even"},
        5: {"digit"},
        6: {"digit"},
        7: {"digit"},
        8: {"digit"},
        9: {"digit"},
        42: {"even", "significant"},
    }
    number_categories: BidirectionalManyMapping[str, int] = BidirectionalManyMapping(plain_mapping)
    category_numbers: BidirectionalManyMapping[int, str] = number_categories.reverse_mapping()
    assert category_numbers.reverse_mapping() is number_categories

    def assert_equal() -> None:
        """
        Assert mapping equality, respectively between
        - plain_mapping and number_categories
        - plain_reverse and category_numbers
        """
        assert number_categories.keys() == plain_mapping.keys()
        assert len(number_categories) == len(plain_mapping)
        for key, values in number_categories.items():
            assert values == plain_mapping[key]

        assert category_numbers.keys() == plain_reverse.keys()
        assert len(category_numbers) == len(category_numbers)
        for key, values in category_numbers.items():
            assert values == plain_reverse[key]

    # assert initial construction
    assert_equal()

    # verify that bidir mapping objects are not bound to their construction args
    plain_mapping["digit"] = set(range(1, 10))  # 0 is not a real digit
    assert plain_mapping["digit"] != number_categories["digit"]
    # restore equality
    # additionally verifies removal of an element
    plain_reverse[0].remove("digit")
    number_categories["digit"] = set(range(1, 10))
    assert_equal()

    # verify appropriate behavior when using reverse as mutable mapping
    category_numbers[2] = set()
    plain_reverse[2] = set()
    for category in ("digit", "even"):
        plain_mapping[category].remove(2)
    assert_equal()

    # add new elements on both ends
    number_categories["new"] = {12, 0}
    number_categories["significant"] = number_categories["significant"].union({-1, 2})
    plain_mapping["new"] = {12, 0}
    plain_mapping["significant"] = {-1, 0, 1, 2, 42}
    for category in ("new", "significant"):
        for i in plain_mapping[category]:
            if i not in plain_reverse:
                plain_reverse[i] = set()
            plain_reverse[i].add(category)
    assert_equal()

    # verify item deletion
    number_categories["temp"] = {0, 1234}
    assert "temp" in number_categories
    assert category_numbers[1234] == {"temp"}
    del number_categories["temp"]
    assert "temp" not in number_categories
    assert "temp" not in category_numbers[0]
    assert category_numbers[1234] == set()
    # clean up because empty sets make items view tricky (unidirectional), complicating rest of test
    del category_numbers[1234]
    with pytest.raises(KeyError):
        del category_numbers["doesnotexist"]
    # verify item deletion in same-type mapping: should delete from one side only
    same_type_mapping: BidirectionalManyMapping[int, int] = BidirectionalManyMapping({0: {0, 1}})
    del same_type_mapping[0]
    assert dict(same_type_mapping.items()) == {}
    assert dict(same_type_mapping.reverse_mapping().items()) == {0: set(), 1: set()}

    # verify equivalence of some methods
    assert category_numbers.get(0) is category_numbers[0]
    assert number_categories.get_reverse(0) is category_numbers[0]
    copy: BidirectionalManyMapping[str, int] = BidirectionalManyMapping(number_categories)

    def copy_equals() -> bool:
        return dict(copy.items()) == dict(number_categories.items()) and dict(copy.reverse_mapping().items()) == dict(
            category_numbers.items()
        )

    assert copy_equals()
    copy.set_reverse(-2, {"even"})
    assert not copy_equals()
    category_numbers[-2] = {"even"}
    assert copy_equals()
