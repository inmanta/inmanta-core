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
import os

import pytest

from inmanta import compiler
from inmanta.module import InmantaModuleRequirement
from utils import module_from_template


@pytest.mark.parametrize("swap_order", [True, False])
@pytest.mark.parametrize_any("nested", [True, False])
def test_eager_promises_if(snippetcompiler, swap_order: bool, nested: bool) -> None:
    """
    Verify freeze order for a model that requires eager promises for accurate assignment tracking.
    This model compiles or fails without eager promising depending on the declaration order of the two relations (without
    promises, neither is preferred over the other and they are frozen in lexical order.
    """
    relations_raw: str = (
        """
            A.optional [0:1] -- A
            A.list [0:] -- A
        """
    ).strip()
    relations: str = relations_raw if not swap_order else "\n".join(reversed(relations_raw.splitlines()))

    body: str
    if nested:
        # nest some control flow statements to verify they propagate the promise appropriately
        body = """
            rhs = A()
            for x in [1,2,3,4,5]:
                if true:
                    a.optional = rhs
                end
            end
        """.strip()
    else:
        body = "a.optional = A()"

    snippetcompiler.setup_for_snippet(
        f"""
            entity A:
            end
            implement A using std::none

            {relations}

            a = A(list=A())

            if std::count(a.list) > 0:
                {body}
            end

            assert = true
            assert = a.optional is defined
            assert = not a.optional.optional is defined
        """
    )
    compiler.do_compile()


@pytest.mark.slowtest
def test_eager_promises_cross_namespace(
    snippetcompiler_clean,
    modules_v2_dir,
    tmpdir,
) -> None:
    """
    Verify that eager promises are applied to cross-namespace assignments as well.
    """
    # initialize snippetcompiler environment before installing module
    snippetcompiler_clean.setup_for_snippet("")
    module: str = """
        entity A:
        end
        implement A using std::none

        A.optional [0:1] -- A
        A.list [0:] -- A

        a = A(list=A())
    """
    module_from_template(
        os.path.join(modules_v2_dir, "minimalv2module"),
        str(tmpdir.join("mymod")),
        new_name="mymod",
        new_content_init_cf=module,
        new_requirements=[InmantaModuleRequirement.parse("std")],
        install=True,
    )
    snippetcompiler_clean.setup_for_snippet(
        """
            import mymod

            if std::count(mymod::a.list) > 0:
                mymod::a.optional = mymod::A()
            end

            assert = true
            assert = mymod::a.optional is defined
            assert = not mymod::a.optional.optional is defined
        """,
    )
    compiler.do_compile()


@pytest.mark.parametrize("swap_order", [True, False])
@pytest.mark.parametrize_any("when", [True, False])
def test_eager_promises_implementation(snippetcompiler, swap_order: bool, when: True) -> None:
    """
    Verify that eager promises are acquired on an implementation's instance.
    """
    if when:
        # TODO: is this ok? Should we just remove it?
        pytest.xfail(
            "Limitation of the current eager promising implementation: implementations can only acquire promises when emitted"
        )
    relations_raw: str = (
        """
            A.optional [0:1] -- A
            A.list [0:] -- A
        """
    ).strip()
    relations: str = relations_raw if not swap_order else "\n".join(reversed(relations_raw.splitlines()))

    implement: str = "implement A using a when std::count(self.list) > 0" if when else "implement A using a"
    body: str = "self.optional = A()" if when else "if std::count(self.list) > 0: self.optional = A() end"

    snippetcompiler.setup_for_snippet(
        f"""
            entity A:
            end
            implement A using std::none
            {implement}

            implementation a for A:
                {body}
            end

            {relations}

            a = A(list=A())

            assert = true
            assert = a.optional is defined
            assert = not a.optional.optional is defined
        """
    )
    compiler.do_compile()


@pytest.mark.parametrize("swap_order", [True, False])
def test_eager_promises_implementation_implicit_self(snippetcompiler, swap_order: bool) -> None:
    """
    Verify that assignment to a relation's subattribute in an implementation works as expected when the self keyword is not
    used for the reference.
    """
    relations_raw: str = (
        """
            A.optional [0:1] -- A
            A.list [0:] -- A
        """
    ).strip()
    relations: str = relations_raw if not swap_order else "\n".join(reversed(relations_raw.splitlines()))

    snippetcompiler.setup_for_snippet(
        f"""
            entity A:
            end
            implement A using std::none

            {relations}

            entity B:
            end
            B.a [1] -- A
            implement B using std::none
            implement B using b

            implementation b for B:
                # implicit self for references to a
                if std::count(a.list) > 0:
                    a.optional = A()
                end
            end

            a = A(list=A())
            b = B(a=a)

            assert = true
            assert = a.optional is defined
            assert = not a.optional.optional is defined
        """
    )
    compiler.do_compile()


def test_eager_promises_paired_lists(snippetcompiler) -> None:
    """
    Verify that a fragile model with a bidirectional dependency between two relations works as expected. This model compiled
    fine before the introduction of eager promises but could be broken by a naive promise implementation.
    """
    snippetcompiler.setup_for_snippet(
        """
            import math

            entity Int:
                int n
            end
            index Int(n)
            implement Int using std::none

            entity List:
            end
            List.elements [0:] -- Int
            implement List using std::none


            # l2 contains all values of l1 to the power of 2 and vice versa (bidirectionally linked)
            l1 = List()
            l2 = List()

            for element in l1.elements:
                l2.elements += Int(n=math::power(element.n, 2))
            end
            for element in l2.elements:
                l1.elements += Int(n=math::root(element.n))
            end

            l1.elements = [Int(n=1), Int(n=2), Int(n=3)]
            l2.elements = [Int(n=4), Int(n=25), Int(n=400)]


            assert = true
            assert = std::select(std::key_sort(l1.elements, "n"), "n") == [1, 2, 3, 5, 20]
            assert = std::select(std::key_sort(l2.elements, "n"), "n") == [1, 4, 9, 25, 400]
        """
    )
    compiler.do_compile()
