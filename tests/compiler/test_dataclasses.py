import pytest

from inmanta import compiler
from inmanta.ast import DataClassException


def test_dataclass_load(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses
""",
        ministd=True,
    )
    compiler.do_compile()


def test_dataclass_load_bad(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses::bad_sub
""",
        ministd=True,
    )
    with pytest.raises(DataClassException, match="Dataclasses must have a python counterpart that is a frozen dataclass"):
        compiler.do_compile()
