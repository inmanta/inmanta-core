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
from inmanta.parser.pickle import ASTPickler, ASTUnpickler
from inmanta.util import get_compiler_version

LOGGER = logging.getLogger(__name__)


class CacheManager:
    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.failures = 0

        # import loop, ....
        from inmanta.compiler.config import feature_compiler_cache

        self.cache_enabled = feature_compiler_cache

    def get_file_name(self, filename: str) -> str:
        """
        Returns the name for the cached file, based on the name of the original source file

        Also ensures the cache folder exists.

        :param filename: the filename of the source file
        :return: the filename of the cached file
        """
        # get module folder name
        base_folder = os.path.dirname(filename)

        # get file name without extension
        filepart = os.path.basename(filename).rsplit(".", 1)[0]

        # determine cache folder
        cache_folder = os.path.join(base_folder, "__cfcache__")

        # create cache folder
        os.makedirs(cache_folder, exist_ok=True)

        # make filename with compiler version specific extension
        filename = f"{filepart}.{get_compiler_version().replace('.','_')}.cfc"

        # construct final path
        return os.path.join(cache_folder, filename)

    def un_cache(self, namespace: Namespace, filename: str) -> Optional[List[Statement]]:
        if not self.cache_enabled.get():
            # cache not enabled
            return None
        try:
            cache_filename = self.get_file_name(filename)
            if not os.path.exists(cache_filename):
                self.misses += 1
                return None
            if os.path.getmtime(filename) > os.path.getmtime(cache_filename):
                self.misses += 1
                return None
            with open(cache_filename, "rb") as fh:
                result = ASTUnpickler(fh, namespace).load()
                self.hits += 1
                return result
        except Exception:
            self.failures += 1
            LOGGER.exception("Compile cache loading failure, ignoring cache entry for %s", filename)
            return None

    def cache(self, filename: str, statements: List[Statement]) -> None:

        if not self.cache_enabled.get():
            # cache not enabled
            return
        try:
            cache_filename = self.get_file_name(filename)
            with open(cache_filename, "wb") as fh:
                ASTPickler(fh, protocol=4).dump(statements)
        except Exception:
            LOGGER.exception("Compile cache failure, failed to cache statements for %s", filename)

    def log_stats(self) -> None:
        if not self.cache_enabled.get():
            # cache not enabled
            return
        LOGGER.info(
            "Compiler cache observed %d hits and %d misses (%d%%)",
            self.hits,
            self.misses,
            (100 * self.hits) / (self.hits + self.misses),
        )
