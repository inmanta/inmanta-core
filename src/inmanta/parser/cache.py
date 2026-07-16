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

Per-file AST cache manager for the Inmanta compiler.

Caches parsed AST statements in .cfcache/ to avoid re-parsing unchanged .cf files.
"""

import logging
import os
import pickle

from inmanta import __version__ as inmanta_version
from inmanta.ast import Namespace
from inmanta.ast.statements import Statement
from inmanta.const import CF_CACHE_DIR, LogLevel
from inmanta.parser.pickle import ASTPickler, ASTUnpickler

LOGGER = logging.getLogger(__name__)


class CacheEnvelope:
    """Wraps cached statements with the source file's modification time for cheap invalidation."""

    __slots__ = ("timestamp", "statements")

    def __init__(self, timestamp: float, statements: list[Statement]) -> None:
        self.timestamp = timestamp
        self.statements = statements


class CacheManager:
    def __init__(self) -> None:
        self.hits: int = 0
        self.misses: int = 0
        self.failures: int = 0

        # Import inside __init__ to avoid import cycle
        from inmanta.compiler.config import feature_compiler_cache

        self.cache_enabled = feature_compiler_cache
        self.root_cache_dir: str | None = None

    def _ensure_cache_path(self, namespace: Namespace, filename: str) -> str:
        """
        Returns the cache file path for a given source file.

        Also ensures the cache folder exists.

        :param namespace: The namespace this file is part of
        :param filename: the filename of the source file
        :return: the filename of the cached file
        """
        assert self.root_cache_dir is not None
        cache_folder = os.path.join(self.root_cache_dir, *namespace.to_path())
        os.makedirs(cache_folder, exist_ok=True)

        filepart = os.path.basename(filename).rsplit(".", maxsplit=1)[0]
        cache_name = f"{filepart}.{inmanta_version.replace('.', '_')}.cfc"
        return os.path.join(cache_folder, cache_name)

    def attach_to_project(self, project_dir: str) -> None:
        if not os.path.exists(project_dir):
            raise Exception(f"Project directory {project_dir} doesn't exist")
        self.root_cache_dir = os.path.join(project_dir, CF_CACHE_DIR)

    def is_attached_to_project(self) -> bool:
        return self.root_cache_dir is not None

    def detach_from_project(self) -> None:
        self.root_cache_dir = None

    def un_cache(self, namespace: Namespace, filename: str) -> list[Statement] | None:
        if not self.cache_enabled.get():
            return None
        if not self.is_attached_to_project():
            return None
        try:
            cache_filename = self._ensure_cache_path(namespace, filename)
            if not os.path.exists(cache_filename):
                self.misses += 1
                return None
            mtime = os.path.getmtime(filename)
            if mtime > os.path.getmtime(cache_filename):
                self.misses += 1
                return None
            with open(cache_filename, "rb") as fh:
                result = ASTUnpickler(fh, namespace).load()
                if not isinstance(result, CacheEnvelope):
                    self.misses += 1
                    return None
                if result.timestamp != mtime:
                    self.misses += 1
                    return None
                self.hits += 1
                return result.statements
        except (OSError, pickle.UnpicklingError, EOFError, AttributeError, ImportError, ValueError):
            self.failures += 1
            LOGGER.debug(
                "Compile cache loading failure, ignoring cache entry for %s",
                filename,
                exc_info=True,
            )
            return None

    def cache(self, namespace: Namespace, filename: str, statements: list[Statement]) -> None:
        if not self.cache_enabled.get():
            return
        if not self.is_attached_to_project():
            return
        try:
            cache_filename = self._ensure_cache_path(namespace, filename)
            mtime = os.path.getmtime(filename)
            cache_entry = CacheEnvelope(mtime, statements)
            with open(cache_filename, "wb") as fh:
                ASTPickler(fh, protocol=4).dump(cache_entry)
        except (OSError, pickle.PicklingError, EOFError, AttributeError, TypeError, ValueError):
            LOGGER.warning(
                "Compile cache failure, failed to cache statements for %s",
                filename,
                exc_info=LOGGER.isEnabledFor(LogLevel.DEBUG.to_int),
            )

    def reset_stats(self) -> None:
        self.hits = 0
        self.misses = 0
        self.failures = 0

    def log_stats(self) -> None:
        if not self.cache_enabled.get():
            return
        if self.failures > 0:
            LOGGER.warning(
                "Compiler cache: %d entries could not be loaded and were re-parsed (set log level to DEBUG for details)",
                self.failures,
            )
        if self.hits + self.misses != 0:
            LOGGER.debug(
                "Compiler cache observed %d hits and %d misses (%d%%)",
                self.hits,
                self.misses,
                (100 * self.hits) / (self.hits + self.misses),
            )
