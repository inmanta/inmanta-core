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

import argparse
import glob
import sys
from collections import abc

from inmanta.command import CLIException, command


def _format_parser_config(parser: argparse.ArgumentParser, parent_parsers: abc.Sequence[argparse.ArgumentParser]) -> None:
    parser.add_argument("files", nargs="*", help="Files or directories to format. Defaults to all .cf files in current dir.")
    parser.add_argument("--check", action="store_true", help="Exit with code 1 if any file would change (for CI).")
    parser.add_argument("--diff", action="store_true", help="Print unified diff of changes.")
    parser.add_argument("--line-length", type=int, default=120, help="Maximum line length (default: 120).")


@command("format", help_msg="Format Inmanta .cf files", parser_config=_format_parser_config)
def format_command(options: argparse.Namespace) -> None:
    from inmanta.formatter import FormatterError, check_file, diff_file, format_file
    from inmanta.formatter.config import FormatConfig

    # Load config from pyproject.toml, then override with CLI flags
    config = FormatConfig.from_pyproject()
    if options.line_length != 120:  # CLI override
        config = FormatConfig(
            line_length=options.line_length,
            indent_width=config.indent_width,
            normalize_quotes=config.normalize_quotes,
            magic_trailing_comma=config.magic_trailing_comma,
        )
    files = _resolve_files(options.files)

    if not files:
        print("No .cf files found.")
        return

    changed_count = 0
    error_count = 0

    for path in files:
        try:
            if options.check:
                if not check_file(path, config=config):
                    print(f"would reformat {path}")
                    changed_count += 1
            elif options.diff:
                d = diff_file(path, config=config)
                if d:
                    print(d, end="")
                    changed_count += 1
            else:
                _, changed = format_file(path, config=config)
                if changed:
                    print(f"reformatted {path}")
                    changed_count += 1
        except FormatterError as e:
            print(f"error: {path}: {e}", file=sys.stderr)
            error_count += 1
        except Exception as e:
            print(f"error: {path}: {e}", file=sys.stderr)
            error_count += 1

    # Summary
    total = len(files)
    unchanged = total - changed_count - error_count
    parts = []
    if changed_count:
        verb = "would be reformatted" if options.check else "reformatted"
        parts.append(f"{changed_count} file{'s' if changed_count != 1 else ''} {verb}")
    if unchanged:
        parts.append(f"{unchanged} file{'s' if unchanged != 1 else ''} left unchanged")
    if error_count:
        parts.append(f"{error_count} file{'s' if error_count != 1 else ''} failed")
    if parts:
        print(", ".join(parts) + ".")

    if options.check and changed_count > 0:
        raise CLIException(exitcode=1)
    if error_count > 0:
        raise CLIException(exitcode=2)


def _resolve_files(paths: list[str]) -> list[str]:
    """Resolve file arguments to a list of .cf file paths."""
    import os

    if not paths:
        paths = ["."]

    result: list[str] = []
    for p in paths:
        if os.path.isfile(p):
            result.append(p)
        elif os.path.isdir(p):
            result.extend(sorted(glob.glob(os.path.join(p, "**", "*.cf"), recursive=True)))
        else:
            # Try as glob pattern
            result.extend(sorted(glob.glob(p, recursive=True)))

    return result
