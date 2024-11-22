import dataclasses

import pytest

from inmanta import compiler


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
    with pytest.raises(Exception):
        compiler.do_compile()
