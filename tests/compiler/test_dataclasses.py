import dataclasses

from inmanta import compiler


def test_dataclass_load(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import dataclasses
""",
        ministd=True,
    )
    compiler.do_compile()


dataclasses
