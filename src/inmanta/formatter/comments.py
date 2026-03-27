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
"""

import re
from dataclasses import dataclass, field

# Matches # comments (not inside strings — applied to masked source)
_COMMENT_RE = re.compile(r"#[^\n]*")

# Matches all string literal forms in the Inmanta grammar so we can mask them.
# Order matters: MLS (triple-quoted) must come before STRING to avoid partial matches.
_STRING_RE = re.compile(
    r'"{3,5}[\s\S]*?"{3,5}'  # MLS (triple-quoted, 3-5 quotes)
    r"|"
    r'f"[^"\\\n]*(?:\\.[^"\\\n]*)*"'  # f-string double
    r"|"
    r"f'[^'\\\n]*(?:\\.[^'\\\n]*)*'"  # f-string single
    r"|"
    r'r"[^"\\\n]*(?:\\.[^"\\\n]*)*"'  # r-string double
    r"|"
    r"r'[^'\\\n]*(?:\\.[^'\\\n]*)*'"  # r-string single
    r"|"
    r'"[^"\\\n]*(?:\\.[^"\\\n]*)*"'  # regular double-quoted string
    r"|"
    r"'[^'\\\n]*(?:\\.[^'\\\n]*)*'",  # regular single-quoted string
)


@dataclass(frozen=True, slots=True)
class Comment:
    """A single # comment extracted from source code."""

    line: int  # 1-based line number
    column: int  # 0-based column where # starts
    text: str  # full comment text including #
    is_inline: bool  # True if non-whitespace code precedes # on same line


@dataclass
class CommentMap:
    """Maps source line numbers to comments for reattachment during formatting."""

    _by_line: dict[int, Comment] = field(default_factory=dict)
    _consumed: set[int] = field(default_factory=set)

    def add(self, comment: Comment) -> None:
        self._by_line[comment.line] = comment

    def get_leading(self, line: int) -> list[Comment]:
        """Get block of standalone comments on consecutive lines immediately before ``line``."""
        result: list[Comment] = []
        check = line - 1
        while check in self._by_line and not self._by_line[check].is_inline and check not in self._consumed:
            result.append(self._by_line[check])
            self._consumed.add(check)
            check -= 1
        result.reverse()
        return result

    def get_trailing(self, line: int) -> Comment | None:
        """Get inline comment on same line as code at ``line``."""
        c = self._by_line.get(line)
        if c is not None and c.is_inline and line not in self._consumed:
            self._consumed.add(line)
            return c
        return None

    def get_orphans(self, after_line: int, before_line: int) -> list[Comment]:
        """Get standalone comments between two source lines (exclusive)."""
        result: list[Comment] = []
        for line_nr in sorted(self._by_line):
            if line_nr <= after_line:
                continue
            if line_nr >= before_line:
                break
            c = self._by_line[line_nr]
            if not c.is_inline and line_nr not in self._consumed:
                result.append(c)
                self._consumed.add(line_nr)
        return result

    def get_remaining(self) -> list[Comment]:
        """Get all comments not yet consumed, in line order."""
        return [c for line_nr, c in sorted(self._by_line.items()) if line_nr not in self._consumed]

    def __len__(self) -> int:
        return len(self._by_line)


@dataclass
class FmtOffRegions:
    """Tracks ``# fmt: off`` / ``# fmt: on`` regions and ``# fmt: skip`` lines."""

    _off_ranges: list[tuple[int, int]] = field(default_factory=list)  # (start_line, end_line) inclusive
    _skip_lines: set[int] = field(default_factory=set)

    def is_off(self, line: int) -> bool:
        """Check if *line* is inside a ``# fmt: off`` region or has ``# fmt: skip``."""
        if line in self._skip_lines:
            return True
        for start, end in self._off_ranges:
            if start <= line <= end:
                return True
        return False

    def is_off_range(self, start_line: int, end_line: int) -> bool:
        """Check if the range [start_line, end_line] overlaps a ``# fmt: off`` region."""
        for off_start, off_end in self._off_ranges:
            if off_start <= end_line and off_end >= start_line:
                return True
        return False


_FMT_OFF_RE = re.compile(r"#\s*fmt:\s*off\b")
_FMT_ON_RE = re.compile(r"#\s*fmt:\s*on\b")
_FMT_SKIP_RE = re.compile(r"#\s*fmt:\s*skip\b")


def extract_fmt_regions(source: str) -> FmtOffRegions:
    """Scan *source* for ``# fmt: off``, ``# fmt: on``, and ``# fmt: skip`` directives."""
    regions = FmtOffRegions()
    off_start: int | None = None

    for line_nr, line_text in enumerate(source.splitlines(), 1):
        if _FMT_OFF_RE.search(line_text):
            if off_start is None:
                off_start = line_nr
        elif _FMT_ON_RE.search(line_text):
            if off_start is not None:
                regions._off_ranges.append((off_start, line_nr))
                off_start = None
        if _FMT_SKIP_RE.search(line_text):
            regions._skip_lines.add(line_nr)

    # Unclosed # fmt: off extends to end of file
    if off_start is not None:
        regions._off_ranges.append((off_start, len(source.splitlines()) + 1))

    return regions


def extract_comments(source: str) -> CommentMap:
    """Extract all ``#`` comments from *source*, skipping those inside string literals."""
    masked = _mask_strings(source)
    comment_map = CommentMap()
    for match in _COMMENT_RE.finditer(masked):
        start = match.start()
        # Compute 1-based line number and 0-based column
        line = source[:start].count("\n") + 1
        line_start = source.rfind("\n", 0, start) + 1
        column = start - line_start
        # Check if there's non-whitespace code before the # on this line
        prefix = source[line_start:start]
        is_inline = prefix.strip() != ""
        comment_map.add(
            Comment(
                line=line,
                column=column,
                text=source[match.start() : match.end()],
                is_inline=is_inline,
            )
        )
    return comment_map


def _mask_strings(source: str) -> str:
    """Replace string literal contents with spaces so ``#`` inside strings is not matched as a comment."""
    chars = list(source)
    for match in _STRING_RE.finditer(source):
        for i in range(match.start(), match.end()):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)
