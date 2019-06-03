"""
    Copyright 2019 Inmanta

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
import pytest

from inmanta import compiler
from inmanta.ast import AttributeException
from inmanta.compiler.help.explainer import ExplainerFactory


def test_optional_loop_forward(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Thing:
    string name
end

implement Thing using std::none

Thing.other [0:1] -- Thing

implementation setother for Thing:
    self.other = Thing(name="it")
end

implement Thing using setother when not (other is defined)

Thing(name="a")
"""
    )
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()

    assert (
        ExplainerFactory().explain_and_format(e.value)
        == """
Exception explanation
=====================
The compiler could not figure out how to execute this model.

During compilation, the compiler has to decide when it expects an optional relation to remain undefined. In this compiler run, it guessed that the relation 'other' on the instance __config__::Thing (instantiated at %(dir)s/main.cf:16) would never get a value assigned, but the value __config__::Thing (instantiated at %(dir)s/main.cf:11) was assigned at %(dir)s/main.cf:11

This can mean one of two things:

1. The model is incorrect. Most often, this is due to something of the form:

    implementation mydefault for MyEntity:
        self.relation = "default"
    end

    implement MyEntity using mydefault when not (relation is defined)

  This is always wrong, because the relation can not at the same time be undefined and have the value "default".

2. The model is too complicated for the compiler to resolve.

The procedure to solve this is the following:

1. Ensure the model is correct by checking that the problematic assignment at %(dir)s/main.cf:11 is not conditional on the value it assigns.
2. Report a bug to the inmanta issue tracker at https://github.com/inmanta/inmanta/issues or directly contact inmanta. This is a priority issue to us, so you will be helped rapidly and by reporting the problem, we can fix it properly.
3. [does not apply here] If the exception is on the reverse relation, try to give a hint by explicitly using the problematic relation.
4. Simplify the model by relying less on `is defined` but use a boolean instead.
"""  # noqa: E501
        % {"dir": snippetcompiler.project_dir}
    )


def test_optional_loop_forward_tty(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Thing:
    string name
end

implement Thing using std::none

Thing.other [0:1] -- Thing

implementation setother for Thing:
    self.other = Thing(name="it")
end

implement Thing using setother when not (other is defined)

Thing(name="a")
"""
    )
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()

    value = ExplainerFactory().explain_and_format(e.value, plain=False)

    assert (
        value
        == """
\033[1mException explanation
=====================\033[0m
The compiler could not figure out how to execute this model.

During compilation, the compiler has to decide when it expects an optional relation to remain undefined. In this compiler run, it guessed that the relation '\033[4mother\033[0m' on the instance \033[4m__config__::Thing (instantiated at %(dir)s/main.cf:16)\033[0m would never get a value assigned, but the value \033[4m__config__::Thing (instantiated at %(dir)s/main.cf:11)\033[0m was assigned at \033[4m%(dir)s/main.cf:11\033[0m

This can mean one of two things:

1. The model is incorrect. Most often, this is due to something of the form:

    \033[1mimplementation mydefault for MyEntity:
        self.relation = "default"
    end

    implement MyEntity using mydefault when not (relation is defined)\033[0m

  This is always wrong, because the relation can not at the same time be undefined and have the value "default".

2. The model is too complicated for the compiler to resolve.

The procedure to solve this is the following:

1. Ensure the model is correct by checking that the problematic assignment at \033[4m%(dir)s/main.cf:11\033[0m is not conditional on the value it assigns.
2. Report a bug to the inmanta issue tracker at https://github.com/inmanta/inmanta/issues or directly contact inmanta. This is a priority issue to us, so you will be helped rapidly and by reporting the problem, we can fix it properly.
3. [does not apply here] If the exception is on the reverse relation, try to give a hint by explicitly using the problematic relation.
4. Simplify the model by relying less on `is defined` but use a boolean instead.
"""  # noqa: E501
        % {"dir": snippetcompiler.project_dir}
    )


def test_optional_loop_reverse(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Thing:
    string name
end

implement Thing using std::none

Thing.other [0:1] -- Thing.that [0:]

implementation setother for Thing:
    t = Thing(name="it")
    t.that = self
end

implement Thing using setother when not (other is defined)

Thing(name="a")
"""
    )
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()

    assert (
        ExplainerFactory().explain_and_format(e.value)
        == """
Exception explanation
=====================
The compiler could not figure out how to execute this model.

During compilation, the compiler has to decide when it expects an optional relation to remain undefined. In this compiler run, it guessed that the relation 'other' on the instance __config__::Thing (instantiated at %(dir)s/main.cf:17) would never get a value assigned, but the value __config__::Thing (instantiated at %(dir)s/main.cf:11) was assigned at %(dir)s/main.cf:12:14

This can mean one of two things:

1. The model is incorrect. Most often, this is due to something of the form:

    implementation mydefault for MyEntity:
        self.relation = "default"
    end

    implement MyEntity using mydefault when not (relation is defined)

  This is always wrong, because the relation can not at the same time be undefined and have the value "default".

2. The model is too complicated for the compiler to resolve.

The procedure to solve this is the following:

1. Ensure the model is correct by checking that the problematic assignment at %(dir)s/main.cf:12:14 is not conditional on the value it assigns.
2. Report a bug to the inmanta issue tracker at https://github.com/inmanta/inmanta/issues or directly contact inmanta. This is a priority issue to us, so you will be helped rapidly and by reporting the problem, we can fix it properly.
3. [applies] If the exception is on the reverse relation, try to give a hint by explicitly using the problematic relation: self.other = t.
4. Simplify the model by relying less on `is defined` but use a boolean instead.
"""  # noqa: E501
        % {"dir": snippetcompiler.project_dir}
    )


def test_optional_loop_list(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Thing:
    string name
end

implement Thing using std::none

Thing.other [0:] -- Thing.that [0:]

implementation setother for Thing:
    t = Thing(name="it")
    t.that = self
end

implement Thing using setother when std::count(other) == 1

t = Thing(name="a")
t.other = Thing(name="b")
"""
    )
    with pytest.raises(AttributeException) as e:
        compiler.do_compile()

    print(ExplainerFactory().explain_and_format(e.value))
    assert (
        ExplainerFactory().explain_and_format(e.value)
        == """
Exception explanation
=====================
The compiler could not figure out how to execute this model.

During compilation, the compiler has to decide when it expects a relation to have all its elements.
In this compiler run, it guessed that the relation 'other' on the instance __config__::Thing (instantiated at %(dir)s/main.cf:17) would be complete with the values [__config__::Thing (instantiated at %(dir)s/main.cf:18)], but the value __config__::Thing (instantiated at %(dir)s/main.cf:11) was added at %(dir)s/main.cf:12:14

This can mean one of two things:

1. The model is incorrect. Most often, this is due to something of the form:

    implementation mydefault for MyEntity:
      self.relation += "default"
    end

    implement MyEntity using mydefault when std::count(relation) == 0


   This is always wrong, because the relation can not at the same time have length 0 and contain the value "default"

2. The model is too complicated for the compiler to resolve.

The procedure to solve this is the following

1. Ensure the model is correct by checking that the problematic assignment at %(dir)s/main.cf:12:14 is not conditional on the value it assigns.
2. Report a bug to the inmanta issue tracker at https://github.com/inmanta/inmanta/issues or directly contact inmanta. This is a priority issue to us, so you will be helped rapidly and by reporting the problem, we can fix it properly.
3. [applies] If the exception is on the reverse relation, try to give a hint by explicitly using the problematic relation: self.other = t
4. Simplify the model by reducing the number of implements calls that pass a list into a plugin function in their when clause.

"""  # noqa: E501
        % {"dir": snippetcompiler.project_dir}
    )
