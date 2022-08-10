"""
    Copyright 2021 Inmanta

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
import logging
import os
from typing import List, Optional

from inmanta.ast import Namespace
from inmanta.ast.statements import Statement
from inmanta.const import CF_CACHE_DIR
from inmanta.parser.pickle import ASTPickler, ASTUnpickler
from inmanta.util import get_compiler_version

LOGGER = logging.getLogger(__name__)


class CacheEnvelope:
    """Every cached file gets the exact modification time of the file it is caching, to have cheap, accurate invalidation"""

    def __init__(self, timestamp: float, statements: List[Statement]) -> None:
        self.timestamp = timestamp
        self.statements = statements


class CacheManager:
    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.failures = 0

        # import loop, ....
        from inmanta.compiler.config import feature_compiler_cache

        self.cache_enabled = feature_compiler_cache
        self.root_cache_dir: Optional[str] = None

    def _get_file_name(self, namespace: Namespace, filename: str) -> str:
        """
        Returns the name for the cached file, based on the name of the original source file

        Also ensures the cache folder exists.

        :param namespace: The namespace this file is part of
        :param filename: the filename of the source file
        :return: the filename of the cached file
        """
        # Make mypy happy
        assert self.root_cache_dir is not None
        # Obtains directory where the cache file will be stored
        cache_folder = os.path.join(self.root_cache_dir, *namespace.to_path())
        # create cache folder
        os.makedirs(cache_folder, exist_ok=True)

        # get file name without extension
        filepart = os.path.basename(filename).rsplit(".", maxsplit=1)[0]
        # make filename with compiler version specific extension
        filename = f"{filepart}.{get_compiler_version().replace('.','_')}.cfc"

        # construct final path
        return os.path.join(cache_folder, filename)

    def attach_to_project(self, project_dir: str) -> None:
        if not os.path.exists(project_dir):
            raise Exception(f"Project directory {project_dir} doesn't exist")
        self.root_cache_dir = os.path.join(project_dir, CF_CACHE_DIR)

    def is_attached_to_project(self) -> bool:
        return self.root_cache_dir is not None

    def detach_from_project(self) -> None:
        self.root_cache_dir = None

    def un_cache(self, namespace: Namespace, filename: str) -> Optional[List[Statement]]:
        if not self.cache_enabled.get():
            # cache not enabled
            return None
        if not self.is_attached_to_project():
            return None
        try:
            cache_filename = self._get_file_name(namespace, filename)
            if not os.path.exists(cache_filename):
                self.misses += 1
                return None
            mtime = os.path.getmtime(filename)
            if os.path.getmtime(filename) > os.path.getmtime(cache_filename):
                self.misses += 1
                return None
            with open(cache_filename, "rb") as fh:
                result = ASTUnpickler(fh, namespace).load()
                if not isinstance(result, CacheEnvelope):
                    # old cache format
                    self.misses += 1
                    return None
                if result.timestamp != mtime:
                    # mtime is not exactly the same
                    self.misses += 1
                    return None
                self.hits += 1
                return result.statements
        except Exception:
            self.failures += 1
            LOGGER.warning("Compile cache loading failure, ignoring cache entry for %s", filename, exc_info=True)
            return None

    def cache(self, namespace: Namespace, filename: str, statements: List[Statement]) -> None:
        if not self.cache_enabled.get():
            # cache not enabled
            return
        if not self.is_attached_to_project():
            return
        try:
            cache_filename = self._get_file_name(namespace, filename)
            mtime = os.path.getmtime(filename)
            cache_entry = CacheEnvelope(mtime, statements)
            with open(cache_filename, "wb") as fh:
                ASTPickler(fh, protocol=4).dump(cache_entry)
        except Exception:
            LOGGER.warning("Compile cache failure, failed to cache statements for %s", filename, exc_info=True)

    def reset_stats(self) -> None:
        self.hits = 0
        self.misses = 0
        self.failures = 0

    def log_stats(self) -> None:
        if not self.cache_enabled.get():
            # cache not enabled
            return
        if self.hits + self.misses != 0:
            LOGGER.debug(
                "Compiler cache observed %d hits and %d misses (%d%%)",
                self.hits,
                self.misses,
                (100 * self.hits) / (self.hits + self.misses),
            )
