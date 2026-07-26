"""
Copyright 2026 Inmanta

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

String-processing helpers shared by both parser backends (PLY and Lark): range
merging, {{var}} interpolation of regular strings, and {field} interpolation of
f-strings. Keeping these in one place avoids the two backends drifting apart.
"""

import re
import string
from collections.abc import Sequence
from typing import Optional, Union

from inmanta.ast import LocatableString, Namespace, Range
from inmanta.ast.statements import Literal
from inmanta.ast.statements.assign import StringFormat, StringFormatV2
from inmanta.ast.variables import AttributeReference, Reference
from inmanta.parser import ParserException

# {{ variable }} interpolation pattern used by regular (non-f) strings.
INTERPOLATION_REGEX = re.compile(r"""({{\s*([\.A-Za-z0-9_-]+)\s*}})""", re.MULTILINE | re.DOTALL)


def expand_range(start: Range, end: Range) -> Range:
    """Return a range spanning from the start of `start` to the end of `end` (same file)."""
    return Range(start.file, start.lnr, start.start_char, end.end_lnr, end.end_char)


def get_string_ast_node(string_ast: LocatableString, mls: bool) -> Union[Literal, StringFormat]:
    """Expand {{var}} interpolation into a StringFormat, or return a plain Literal if there is none."""
    matches: list[re.Match[str]] = list(INTERPOLATION_REGEX.finditer(str(string_ast)))
    if len(matches) == 0:
        return Literal(str(string_ast))

    start_lnr = string_ast.location.lnr
    start_char_pos = string_ast.location.start_char
    whole_string = str(string_ast)
    mls_offset: int = 3 if mls else 1  # len('"""') or len('"')/len("'")

    def char_count_to_lnr_char(position: int) -> tuple[int, int]:
        before = whole_string[0:position]
        lines = before.count("\n")
        if lines == 0:
            return start_lnr, start_char_pos + position + mls_offset
        else:
            return start_lnr + lines, position - before.rindex("\n")

    locatable_matches: list[tuple[str, LocatableString]] = []
    for match in matches:
        start_line, start_char = char_count_to_lnr_char(match.start(2))
        end_line, end_char = char_count_to_lnr_char(match.end(2))
        r: Range = Range(string_ast.location.file, start_line, start_char, end_line, end_char)
        locatable_string = LocatableString(match[2], r, string_ast.lexpos, string_ast.namespace)
        locatable_matches.append((match[1], locatable_string))

    return StringFormat(str(string_ast), convert_to_references(locatable_matches, string_ast.namespace))


def process_fstring(string_ast: LocatableString) -> Union[StringFormatV2, Literal]:
    """Expand {field} interpolation of an f-string into a StringFormatV2."""
    formatter = string.Formatter()
    try:
        parsed = list(formatter.parse(str(string_ast)))
    except ValueError as e:
        raise ParserException(string_ast.location, str(string_ast), f"Invalid f-string: {e}")

    start_lnr = string_ast.location.lnr
    start_char_pos = string_ast.location.start_char + 2  # f" or f' prefix

    locatable_matches: list[tuple[str, LocatableString]] = []

    def locate_match(match: tuple[str, Optional[str], Optional[str], Optional[str]], scp: int, end_char: int) -> None:
        assert match[1]
        r: Range = Range(string_ast.location.file, start_lnr, scp, start_lnr, end_char)
        locatable_string = LocatableString(match[1], r, string_ast.lexpos, string_ast.namespace)
        locatable_matches.append((match[1], locatable_string))

    cur_pos = start_char_pos
    for match in parsed:
        if not match[1]:
            break
        lit_len = len(match[0])
        field_len = len(match[1])
        brack_len = 1 if field_len else 0
        cur_pos += lit_len + brack_len
        end_char = cur_pos + field_len
        locate_match(match, cur_pos, end_char)
        cur_pos += field_len

        if match[2]:
            cur_pos += 1
            sub_parsed = formatter.parse(match[2])
            for submatch in sub_parsed:
                if not submatch[1]:
                    break
                slit_len = len(submatch[0])
                sfield_len = len(submatch[1])
                sbrack_len = 1 if sfield_len else 0
                cur_pos += slit_len + sbrack_len
                end_char = cur_pos + sfield_len
                locate_match(submatch, cur_pos, end_char)
                cur_pos += sfield_len + sbrack_len

        cur_pos += brack_len

    return StringFormatV2(str(string_ast), convert_to_references(locatable_matches, string_ast.namespace))


def convert_to_references(
    variables: Sequence[tuple[str, LocatableString]], namespace: Namespace
) -> list[tuple["Reference", str]]:
    """Convert interpolated variable strings to References, with proper location tracking.

    Each input pairs the raw match text (e.g. "{{a.b}}" or "a.b") with a LocatableString
    holding just the variable and its range. Returned References are whitespace-trimmed;
    the matching text is returned unchanged.
    """

    def normalize(variable: str, locatable: LocatableString, offset: int = 0) -> LocatableString:
        start_char = locatable.location.start_char + offset
        end_char = start_char + len(variable)
        var_left_trim = variable.lstrip()
        left_spaces = len(variable) - len(var_left_trim)
        var_full_trim = var_left_trim.rstrip()
        right_spaces = len(var_left_trim) - len(var_full_trim)
        r: Range = Range(
            locatable.location.file,
            locatable.location.lnr,
            start_char + left_spaces,
            locatable.location.lnr,
            end_char - right_spaces,
        )
        return LocatableString(var_full_trim, r, locatable.lexpos, locatable.namespace)

    var_list: list[tuple[Reference, str]] = []
    for match, var in variables:
        var_name: str = str(var)
        var_parts: list[str] = var_name.split(".")
        ref_ls: LocatableString = normalize(var_parts[0], var)
        ref = Reference(ref_ls)
        ref.location = ref_ls.location
        ref.namespace = namespace
        if len(var_parts) > 1:
            offset = len(var_parts[0]) + 1
            for attr in var_parts[1:]:
                attr_ls: LocatableString = normalize(attr, var, offset=offset)
                ref = AttributeReference(ref, attr_ls)
                ref.location = attr_ls.location
                ref.namespace = namespace
                offset += len(attr) + 1
        var_list.append((ref, match))
    return var_list
