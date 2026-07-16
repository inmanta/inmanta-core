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
import pickle
from pathlib import Path
from pickle import UnpicklingError
from time import sleep
from typing import Callable

import pytest

from inmanta.ast import Namespace
from inmanta.ast.statements import Statement
from inmanta.parser import dispatch as parser
from inmanta.parser.pickle import ASTPickler, ASTUnpickler


def make_namespace(name: str) -> Namespace:
    """Build a namespace rooted under __root__, as the compiler does."""
    ns = Namespace(name)
    ns.parent = Namespace("__root__")
    return ns


def pickled(ns: Namespace, source: str) -> bytes:
    """Parse source in ns and return the pickled statements."""
    buf = io.BytesIO()
    ASTPickler(buf, protocol=4).dump(parser.base_parse(ns, "test", source))
    return buf.getvalue()


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
    """A pickled AST round-trips with its statements and namespace intact."""
    ns = make_namespace("__config__")

    source = 'x = 1\ny = "hello"'
    stmts = parser.base_parse(ns, "test", source)
    assert len(stmts) == 2

    restored = ASTUnpickler(io.BytesIO(pickled(ns, source)), ns).load()
    assert isinstance(restored, list)
    assert len(restored) == len(stmts)
    for orig, rest in zip(stmts, restored):
        assert type(orig) is type(rest)
        assert isinstance(rest, Statement)
        assert str(rest) == str(orig)
        assert rest.location.file == orig.location.file
        assert rest.location.lnr == orig.location.lnr
        assert rest.namespace is ns


def test_pickle_namespace_mismatch():
    """Unpickling into the wrong namespace is refused rather than silently rebinding."""
    ns_a = make_namespace("ns_a")
    ns_b = make_namespace("ns_b")

    with pytest.raises(UnpicklingError, match="Namespace mismatch"):
        ASTUnpickler(io.BytesIO(pickled(ns_a, "x = 1")), ns_b).load()


def test_pickle_namespace_not_restorable_outside_unpickler():
    """A cache file cannot be coerced into yielding a Namespace via a plain Unpickler."""
    ns = make_namespace("__config__")

    with pytest.raises(UnpicklingError, match="outside ASTUnpickler"):
        pickle.Unpickler(io.BytesIO(pickled(ns, "x = 1"))).load()


class NestedLoad:
    """Unpickling this triggers a second, nested ASTUnpickler load."""

    def __reduce__(self) -> tuple[Callable[..., object], tuple[()]]:
        return (load_inner, ())


def load_inner() -> object:
    inner_ns = make_namespace("inner")
    return ASTUnpickler(io.BytesIO(pickled(inner_ns, "y = 2")), inner_ns).load()


def test_pickle_nested_load_restores_outer_namespace():
    """A nested load must not leave the outer load bound to the inner namespace."""
    outer_ns = make_namespace("outer")

    # the nested load comes first, so the outer namespace is resolved only after it returns
    buf = io.BytesIO()
    ASTPickler(buf, protocol=4).dump([NestedLoad(), parser.base_parse(outer_ns, "test", "x = 1")])
    buf.seek(0)

    inner_stmts, outer_stmts = ASTUnpickler(buf, outer_ns).load()

    assert all(s.namespace is outer_ns for s in outer_stmts)
    assert all(s.namespace.get_full_name() == "inner" for s in inner_stmts)


def test_pickle_namespace_released_after_load():
    """The namespace does not stay published once load() returns."""
    ns = make_namespace("__config__")
    blob = pickled(ns, "x = 1")

    ASTUnpickler(io.BytesIO(blob), ns).load()

    with pytest.raises(UnpicklingError, match="outside ASTUnpickler"):
        pickle.Unpickler(io.BytesIO(blob)).load()


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
