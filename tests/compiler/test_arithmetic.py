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
            """\
            #####################
            # Untyped variables #
            #####################

            var1 = 1 + 2
            var1 = 3

            var2 = 1.5 + 2
            var2 = 3.5

            var3 = "hello" + "world"
            var3 = "helloworld"

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

            val = 55

            entity TestIntAndFloat:
                int val1
                float val2
                float result
            end
            implement TestIntAndFloat using testIntAndFloat when val + 1 == 56
            implement TestIntAndFloat using raiseError when val + 1 == 55

            implementation testIntAndFloat for TestIntAndFloat:
                self.result = val1 + val2
            end

            implementation raiseError for TestIntAndFloat:
                std::assert(false)
            end

            t_int_and_float = TestIntAndFloat(val1=1, val2=2.5)
            t_int_and_float.result = 3.5

            #####################
            # Test if-statement #
            #####################

            if 1 + 1 != 2:
               fail = 1
               fail = 2
            end

            ######################
            # List comprehension #
            ######################

            seq = std::sequence(2)
            filtered = [elem + 10 for elem in seq if elem + 1 < 2]
            std::assert(10 in filtered)
            std::assert(11 not in filtered)
            """
        ),
        autostd=True,
    )
    compiler.do_compile()


def test_min(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
            #####################
            # Untyped variables #
            #####################

            var1 = 1 - 2
            var1 = -1

            var2 = 3.5 - 2
            var2 = 1.5

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
                self.result = val1 - val2
            end

            t_int = TestInt(val1=1, val2=2)
            t_int.result = -1

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
                self.result = val1 - val2
            end

            t_float = TestFloat(val1=1.5, val2=2.0)
            t_float.result = -0.5

            ###################
            # TestIntAndFloat #
            ###################

            val = 55

            entity TestIntAndFloat:
                int val1
                float val2
                float result
            end
            implement TestIntAndFloat using testIntAndFloat when val - 1 == 54
            implement TestIntAndFloat using raiseError when val - 1 == 55

            implementation testIntAndFloat for TestIntAndFloat:
                self.result = val1 - val2
            end

            implementation raiseError for TestIntAndFloat:
                std::assert(false)
            end

            t_int_and_float = TestIntAndFloat(val1=5, val2=2.5)
            t_int_and_float.result = 2.5

            #####################
            # Test if-statement #
            #####################

            if 1 - 1 != 0:
               fail = 1
               fail = 2
            end

            ######################
            # List comprehension #
            ######################

            seq = std::sequence(2, start=10)
            filtered = [elem - 10 for elem in seq if elem - 10 < 1]
            std::assert(0 in filtered)
            std::assert(1 not in filtered)
            """
        ),
        autostd=True,
    )
    compiler.do_compile()


def test_multiplication(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
            #####################
            # Untyped variables #
            #####################

            var1 = 1 * -2
            var1 = -2

            var2 = 1.5 * 2
            var2 = 3

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
                self.result = val1 * val2
            end

            t_int = TestInt(val1=-4, val2=2)
            t_int.result = -8

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
                self.result = val1 * val2
            end

            t_float = TestFloat(val1=1.6, val2=2.0)
            t_float.result = 3.2

            ###################
            # TestIntAndFloat #
            ###################

            val = 55

            entity TestIntAndFloat:
                int val1
                float val2
                float result
            end
            implement TestIntAndFloat using testIntAndFloat when val * 2  == 110
            implement TestIntAndFloat using raiseError when val * 2 == 111

            implementation testIntAndFloat for TestIntAndFloat:
                self.result = val1 * val2
            end

            implementation raiseError for TestIntAndFloat:
                std::assert(false)
            end

            t_int_and_float = TestIntAndFloat(val1=3, val2=2.5)
            t_int_and_float.result = 7.5

            #####################
            # Test if-statement #
            #####################

            if 2 * 3 != 6:
               fail = 1
               fail = 2
            end

            ######################
            # List comprehension #
            ######################

            seq = [1, 2]
            filtered = [elem * 10 for elem in seq if elem * 10 < 20]
            std::assert(10 in filtered)
            std::assert(20 not in filtered)
            """
        ),
        autostd=True,
    )
    compiler.do_compile()


def test_division(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
            #####################
            # Untyped variables #
            #####################

            var1 = 4 / -2
            var1 = -2

            var2 = 4.4 / 2
            var2 = 2.2

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
                self.result = val1 / val2
            end

            t_int = TestInt(val1=8, val2=2)
            t_int.result = 4

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
                self.result = val1 / val2
            end

            t_float = TestFloat(val1=-4.4, val2=2.2)
            t_float.result = -2.0

            ###################
            # TestIntAndFloat #
            ###################

            val = 44

            entity TestIntAndFloat:
                int val1
                float val2
                float result
            end
            implement TestIntAndFloat using testIntAndFloat when val / 2 == 22
            implement TestIntAndFloat using raiseError when val / 2 == 23

            implementation testIntAndFloat for TestIntAndFloat:
                self.result = val1 / val2
            end

            implementation raiseError for TestIntAndFloat:
                std::assert(false)
            end

            t_int_and_float = TestIntAndFloat(val1=-4, val2=2.0)
            t_int_and_float.result = -2.0

            #####################
            # Test if-statement #
            #####################

            if val / 2 == 22:
                # OK
            else:
               fail = 1
               fail = 2
            end

            ######################
            # List comprehension #
            ######################

            seq = [2, 4]
            filtered = [elem / 2 for elem in seq if elem / 2 < 2]
            std::assert(1 in filtered)
            std::assert(2 not in filtered)
            """
        ),
        autostd=True,
    )
    compiler.do_compile()


def test_modulo(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
            #####################
            # Untyped variables #
            #####################

            var1 = 3 % -2
            var1 = -1

            var2 = -1 % 2
            var2 = 1

            ###########
            # TestInt #
            ###########

            val = 7

            entity TestInt:
                int val1
                int val2
                int result
            end
            implement TestInt using testInt when val % 5 == 2
            implement TestInt using raiseError when val % 5 == 3

            implementation testInt for TestInt:
                self.result = val1 % val2
            end

            implementation raiseError for TestInt:
                std::assert(false)
            end

            t_int = TestInt(val1=5, val2=3)
            t_int.result = 2

            #####################
            # Test if-statement #
            #####################

            if 2 % 1 != 0:
               fail = 1
               fail = 2
            end

            ######################
            # List comprehension #
            ######################

            seq = [7, 8]
            filtered = [elem % 2 for elem in seq if elem % 2 > 0]
            std::assert(1 in filtered)
            std::assert(0 not in filtered)
            """
        ),
        autostd=True,
    )
    compiler.do_compile()


def test_exponentiation(snippetcompiler) -> None:
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
            #####################
            # Untyped variables #
            #####################

            var1 = -2 ** 2
            var1 = 4

            var2 = 2 ** -1
            var2 = 0.5

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
                self.result = val1 ** val2
            end

            t_int = TestInt(val1=1, val2=2)
            t_int.result = 1

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
                self.result = val1 ** val2
            end

            t_float = TestFloat(val1=0.2, val2=2.0)
            std::assert( t_float.result >= 0.04 and t_float.result < 0.041)

            ###################
            # TestIntAndFloat #
            ###################

            val = 2

            entity TestIntAndFloat:
                int val1
                float val2
                float result
            end
            implement TestIntAndFloat using testIntAndFloat when val ** 3 == 8
            implement TestIntAndFloat using raiseError when val ** 3 == 9

            implementation testIntAndFloat for TestIntAndFloat:
                self.result = val1 ** val2
            end

            implementation raiseError for TestIntAndFloat:
                std::assert(false)
            end

            t_int_and_float = TestIntAndFloat(val1=1, val2=3.5)
            t_int_and_float.result = 1.0

            #####################
            # Test if-statement #
            #####################

            if 3 ** 3 != 27:
               fail = 1
               fail = 2
            end

            ######################
            # List comprehension #
            ######################

            seq = [2, 3]
            filtered = [elem ** 2 for elem in seq if elem ** 2 < 5]
            std::assert(4 in filtered)
            std::assert(9 not in filtered)
            """
        ),
        autostd=True,
    )
    compiler.do_compile()

@pytest.mark.fundamental
def test_precedence_rules(snippetcompiler) -> None:
    """
    Verify the precedence rules for the arithmetic operations.
    """
    snippetcompiler.setup_for_snippet(
        textwrap.dedent(
            """\
            result1 = 34/2**2+2*3
            result1 = 14.5

            result2 = 15%2*7%4/2
            result2 = 1.5

            result3 = (6/2)**((2+2)*2)
            result3 = 6561
            """
        )
    )
    compiler.do_compile()


def test_error_reporting(snippetcompiler) -> None:
    """
    Verify the error reporting for the arithmetic operations.
    """
    snippetcompiler.setup_for_error(
        "1 + [1, 2]",
        "Unsupported operand type(s) for plus: 'int' (1) and 'list' ([1, 2]) (reported in (1 + [1, 2]) ({dir}/main.cf:1))",
    )
    snippetcompiler.setup_for_error(
        "[1, 2] + 1",
        "Unsupported operand type(s) for plus: 'list' ([1, 2]) and 'int' (1) (reported in ([1, 2] + 1) ({dir}/main.cf:1))",
    )
    snippetcompiler.setup_for_error(
        "1 + 'hello'",
        "Unsupported operand type(s) for plus: 'int' (1) and 'str' ('hello') (reported in (1 + 'hello') ({dir}/main.cf:1))",
    )
    snippetcompiler.setup_for_error(
        "'hello' + 1",
        "Can only concatenate str (not 'int' (1)) to str (reported in ('hello' + 1) ({dir}/main.cf:1))",
    )
