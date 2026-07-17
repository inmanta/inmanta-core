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

import io
import os.path
from pathlib import Path
from pickle import UnpicklingError
from time import sleep

import pytest

from inmanta.ast import Namespace
from inmanta.ast.statements import Statement
from inmanta.parser import dispatch as parser
from inmanta.parser.pickle import ASTPickler, ASTUnpickler


def test_caching(snippetcompiler):
    """Verify cache miss on first parse, cache hit on re-parse, and cache miss after source modification."""
    # reset counts
    parser.cache_manager.reset_stats()
    snippetcompiler.setup_for_snippet(
        """
a=1
""",
        autostd=True,
    )
    # don't know hit count, may vary on previous testcases
    assert parser.cache_manager.misses >= 1
    assert parser.cache_manager.failures == 0

    # reset counts
    parser.cache_manager.reset_stats()
    # reset project ast cache
    snippetcompiler._load_project(autostd=True, install_project=True)

    assert parser.cache_manager.misses == 0
    assert parser.cache_manager.failures == 0
    assert parser.cache_manager.hits == 2  # main.cf and std::init

    main_file = os.path.join(snippetcompiler.project_dir, "main.cf")
    root_ns = snippetcompiler.project.root_ns
    cached_main = parser.cache_manager._ensure_cache_path(root_ns.get_child_or_create("main.cf"), main_file)
    Path(main_file).touch()
    # make the cache a tiny bit newer
    sleep(0.001)
    Path(cached_main).touch()

    # reset counts
    parser.cache_manager.reset_stats()
    # reset project ast cache
    snippetcompiler._load_project(autostd=True, install_project=True)

    assert parser.cache_manager.misses == 1  # std::init
    assert parser.cache_manager.failures == 0
    assert parser.cache_manager.hits == 1  # main.cf


def test_pickle_roundtrip():
    """Verify that pickle round-trip preserves AST structure."""
    root_ns = Namespace("__root__")
    ns = Namespace("__config__")
    ns.parent = root_ns

    stmts = parser.base_parse(ns, "test", 'x = 1\ny = "hello"')
    assert len(stmts) == 2

    # Pickle
    buf = io.BytesIO()
    ASTPickler(buf, protocol=4).dump(stmts)

    # Unpickle
    buf.seek(0)
    restored = ASTUnpickler(buf, ns).load()
    assert isinstance(restored, list)
    assert len(restored) == len(stmts)

    # Verify structure is preserved
    for orig, rest in zip(stmts, restored):
        assert type(orig) is type(rest)
        assert isinstance(rest, Statement)


def test_pickle_namespace_mismatch():
    """Verify that unpickling with wrong namespace raises UnpicklingError."""
    root_ns = Namespace("__root__")
    ns_a = Namespace("ns_a")
    ns_a.parent = root_ns
    ns_b = Namespace("ns_b")
    ns_b.parent = root_ns

    stmts = parser.base_parse(ns_a, "test", "x = 1")

    buf = io.BytesIO()
    ASTPickler(buf, protocol=4).dump(stmts)
    buf.seek(0)

    with pytest.raises(UnpicklingError, match="Namespace mismatch"):
        ASTUnpickler(buf, ns_b).load()


def test_cache_corrupt_file(snippetcompiler):
    """Verify graceful handling of corrupt cache files."""
    parser.cache_manager.reset_stats()
    snippetcompiler.setup_for_snippet(
        """
a=1
""",
        autostd=True,
    )

    # Find the cached main.cf by walking the cache directory
    cache_dir = os.path.join(snippetcompiler.project_dir, ".cfcache")
    assert os.path.isdir(cache_dir), f"Cache directory {cache_dir} does not exist"
    cache_files = [os.path.join(root, f) for root, _, files in os.walk(cache_dir) for f in files if f.endswith(".cfc")]
    assert len(cache_files) >= 1, f"Expected at least one .cfc file in {cache_dir}"

    # Corrupt all cache files
    for cached_file in cache_files:
        with open(cached_file, "wb") as fh:
            fh.write(b"this is not valid pickle data")
        # Make sure corrupted cache is newer than source
        sleep(0.001)
        Path(cached_file).touch()

    # Re-parse: should fall back to re-parsing, not crash
    parser.cache_manager.reset_stats()
    snippetcompiler._load_project(autostd=True, install_project=True)

    assert parser.cache_manager.failures >= 1


def test_cache_load_wrong_shape_pickle(snippetcompiler):
    """A valid-pickle-but-wrong-shape cache entry must degrade to a re-parse, not crash.

    The payload below unpickles part-way then raises IndexError, an exception that the
    previous narrow except tuple did not catch (R10).
    """
    parser.cache_manager.reset_stats()
    snippetcompiler.setup_for_snippet("a=1\n", autostd=True)

    cache_dir = os.path.join(snippetcompiler.project_dir, ".cfcache")
    cache_files = [os.path.join(root, f) for root, _, files in os.walk(cache_dir) for f in files if f.endswith(".cfc")]
    assert cache_files, f"Expected at least one .cfc file in {cache_dir}"

    for cached_file in cache_files:
        with open(cached_file, "wb") as fh:
            fh.write(b"]K\x01K\x02s.")
        sleep(0.001)
        Path(cached_file).touch()

    parser.cache_manager.reset_stats()
    snippetcompiler._load_project(autostd=True, install_project=True)

    assert parser.cache_manager.failures >= 1


def test_cache_filename_includes_backend(tmp_path):
    """The .cfc cache filename includes the backend name so switching INMANTA_PARSER
    never replays the other backend's cached AST (R7)."""
    from inmanta.parser.cache import CacheManager

    root_ns = Namespace("__root__")
    ns = Namespace("__config__")
    ns.parent = root_ns

    ply_mgr = CacheManager("ply")
    lark_mgr = CacheManager("lark")
    ply_mgr.attach_to_project(str(tmp_path))
    lark_mgr.attach_to_project(str(tmp_path))

    ply_path = ply_mgr._ensure_cache_path(ns, "main.cf")
    lark_path = lark_mgr._ensure_cache_path(ns, "main.cf")

    assert ply_path != lark_path
    assert ".ply." in os.path.basename(ply_path)
    assert ".lark." in os.path.basename(lark_path)


def test_grammar_cache_wrong_shape_rebuilds(tmp_path):
    """A valid-pickle-but-wrong-shape grammar cache file is ignored so the caller
    rebuilds, instead of raising past the loader (R9)."""
    import pickle

    from inmanta.parser import lark_parser

    cache_file = str(tmp_path / "grammar.cache")
    with open(cache_file, "wb") as fh:
        pickle.dump({"not": "a lark parser"}, fh)

    assert lark_parser._load_parser_from_cache(cache_file) is None


def test_grammar_cache_save_is_atomic(tmp_path):
    """Grammar cache save writes atomically (temp file + os.replace), leaves no temp
    files behind, and round-trips (R9)."""
    from inmanta.parser import lark_parser

    cache_file = str(tmp_path / "grammar.cache")
    built = lark_parser._build_lark_parser()

    assert lark_parser._save_parser_to_cache(built, cache_file)
    assert os.path.exists(cache_file)
    assert os.listdir(tmp_path) == ["grammar.cache"]
    assert lark_parser._load_parser_from_cache(cache_file) is not None
