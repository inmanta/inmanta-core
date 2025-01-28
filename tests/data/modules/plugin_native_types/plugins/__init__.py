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

from inmanta.plugins import plugin


@plugin
def get_from_dict(value: dict[str, str], key: str) -> str | None:
    return value.get(key)


@plugin
def many_arguments(il: list[str], idx: int) -> str:
    return sorted(il)[idx]


@plugin
def as_none(value: str) -> None:
    pass


@plugin
def var_args_test(value: str, *other: list[str]) -> None:
    pass


@plugin
def var_kwargs_test(value: str, *other: list[str], **more: dict[str, int]) -> None:
    pass


@plugin
def all_args_types(
    positional_arg: str,
    /,
    *star_args_collector: list[str],
    key_word_arg: str | None = None,
    **star_star_args_collector: dict[str, str],
) -> None:
    pass


@plugin
def positional_args_ordering_test(c: str, a: str, b: str) -> str:
    return ""


@plugin
def no_collector(pos_arg_1: str, pos_arg_2: str, /, kw_only_123: str, kw_only_2: str, kw_only_3: str) -> None:
    pass


@plugin
def only_kwargs(*, kw_only_1: str, kw_only_2: str, kw_only_3: str) -> None:
    pass
