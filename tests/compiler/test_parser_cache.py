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
import os.path
from pathlib import Path
from time import sleep

import inmanta.parser.plyInmantaParser as parser
from inmanta.parser.cache import CacheManager


def test_caching(snippetcompiler):
    # reset counts
    parser.cache_manager = CacheManager()
    snippetcompiler.setup_for_snippet(
        """
a=1
"""
    )
    # don't know hit count, may vary on previous testcases
    assert parser.cache_manager.misses > 1
    assert parser.cache_manager.failures == 0

    # reset counts
    parser.cache_manager = CacheManager()
    # reset project ast cache
    snippetcompiler._load_project(autostd=True, install_project=True)

    assert parser.cache_manager.misses == 0
    assert parser.cache_manager.failures == 0
    assert parser.cache_manager.hits == 2  # main.cf and std::init

    main_file = os.path.join(snippetcompiler.project_dir, "main.cf")
    cached_main = parser.cache_manager.get_file_name(main_file)
    Path(main_file).touch()
    # make the cache a tiny bit newer
    sleep(0.001)
    Path(cached_main).touch()

    # reset counts
    parser.cache_manager = CacheManager()
    # reset project ast cache
    snippetcompiler._load_project(autostd=True, install_project=True)

    assert parser.cache_manager.misses == 1  # std::init
    assert parser.cache_manager.failures == 0
    assert parser.cache_manager.hits == 1  # main.cf
