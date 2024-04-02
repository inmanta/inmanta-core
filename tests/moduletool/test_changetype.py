"""
    Copyright 2022 Inmanta

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

from inmanta.moduletool import ChangeType
from packaging.version import Version


def test_change_type() -> None:
    assert ChangeType.MAJOR.value == "major"
    assert ChangeType.MINOR.value == "minor"
    assert ChangeType.PATCH.value == "patch"

    assert ChangeType.PATCH < ChangeType.MINOR < ChangeType.MAJOR
    assert ChangeType.MAJOR > ChangeType.MINOR > ChangeType.PATCH


def test_change_type_diff() -> None:
    assert ChangeType.diff(low=Version("1.0.0"), high=Version("2.0.0")) == ChangeType.MAJOR
    assert ChangeType.diff(low=Version("1.0.1"), high=Version("2.0.0")) == ChangeType.MAJOR
    assert ChangeType.diff(low=Version("1.0.1"), high=Version("2.0.1")) == ChangeType.MAJOR
    assert ChangeType.diff(low=Version("1.0.0"), high=Version("3.0.0")) == ChangeType.MAJOR

    assert ChangeType.diff(low=Version("1.0.0"), high=Version("1.1.0")) == ChangeType.MINOR
    assert ChangeType.diff(low=Version("1.0.0"), high=Version("1.2.0")) == ChangeType.MINOR
    assert ChangeType.diff(low=Version("1.0.0"), high=Version("1.3.1")) == ChangeType.MINOR

    assert ChangeType.diff(low=Version("1.0.0"), high=Version("1.0.1")) == ChangeType.PATCH
    assert ChangeType.diff(low=Version("1.0.0"), high=Version("1.0.2")) == ChangeType.PATCH

    assert ChangeType.diff(low=Version("1.0.0.dev0"), high=Version("1.0.1.dev0")) == ChangeType.PATCH
    assert ChangeType.diff(low=Version("1.0.0.dev0"), high=Version("1.1.0.dev0")) == ChangeType.MINOR
    assert ChangeType.diff(low=Version("1.0.0.dev0"), high=Version("2.0.0.dev0")) == ChangeType.MAJOR

    assert ChangeType.diff(low=Version("1.0.0"), high=Version("1.0.0")) is None
    assert ChangeType.diff(low=Version("1.0.0.dev0"), high=Version("1.0.0")) is None

    with pytest.raises(ValueError):
        ChangeType.diff(low=Version("2.0.0"), high=Version("1.0.0"))
