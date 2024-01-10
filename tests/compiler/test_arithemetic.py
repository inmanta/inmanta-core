"""
    Copyright 2023 Inmanta

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
import textwrap

from inmanta import compiler


def test_plus(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """
            var1 = 1 + 2
            var1 = 3

            var2 = 1.5 + 2
            var2 = 3.5

            ###########
            # TestInt #
            ###########

            entity TestInt:
                int val1
                int val2
                int result
            end
            implement TestInt using testInt

            implementation testInt for TestInt:
                self.result = val1 + val2
            end

            t_int = TestInt(val1=1, val2=2)
            t_int.result = 3

            #############
            # TestFloat #
            #############

            entity TestFloat:
                float val1
                float val2
                float result
            end
            implement TestFloat using testFloat

            implementation testFloat for TestFloat:
                self.result = val1 + val2
            end

            t_float = TestFloat(val1=1.5, val2=2.0)
            t_float.result = 3.5

            ###################
            # TestIntAndFloat #
            ###################

            entity TestIntAndFloat:
                int val1
                float val2
                float result
            end
            implement TestIntAndFloat using testIntAndFloat

            implementation testIntAndFloat for TestIntAndFloat:
                self.result = val1 + val2
            end

            t_int_and_float = TestIntAndFloat(val1=1, val2=2.5)
            t_int_and_float.result = 3.5
            """.strip(
                "\n"
            )
        )
    )
    compiler.do_compile()
