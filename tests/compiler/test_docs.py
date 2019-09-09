"""
    Copyright 2018 Inmanta

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
import inmanta.compiler as compiler


def test_doc_string_on_new_relation(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity File:
end

entity Host:
end

File.host [1] -- Host
\"""
Each file needs to be associated with a host
\"""
"""
    )
    (types, _) = compiler.do_compile()
    assert types["__config__::File"].get_attribute("host").comment.strip() == "Each file needs to be associated with a host"


def test_doc_string_on_relation(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity File:
end

entity Host:
end

File file [1] -- [0:] Host host
\"""
Each file needs to be associated with a host
\"""
"""
    )
    (types, _) = compiler.do_compile()
    assert types["__config__::File"].get_attribute("host").comment.strip() == "Each file needs to be associated with a host"
    assert types["__config__::Host"].get_attribute("file").comment.strip() == "Each file needs to be associated with a host"


def test_function_in_typedef(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
import tests
typedef notempty as string matching tests::length(self) > 0
typedef uniquechars as string matching tests::empty(self)

entity A:
    notempty ne
    uniquechars uc
end

A(ne="aa", uc="")

implement A using std::none
"""
    )
    (types, _) = compiler.do_compile()


def test_doc_string_on_typedef(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
typedef foo as string matching /^a+$/
\"""
    Foo is a stringtype that only allows "a"
\"""
"""
    )
    (types, _) = compiler.do_compile()
    assert types["__config__::foo"].comment.strip() == 'Foo is a stringtype that only allows "a"'


def test_doc_string_on_typedefault(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity File:
    number x
end

typedef Foo as File(x=5)
\"""
    Foo is a stringtype that only allows "a"
\"""
"""
    )
    (types, _) = compiler.do_compile()
    assert types["__config__::Foo"].comment.strip() == 'Foo is a stringtype that only allows "a"'


def test_doc_string_on_impl(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Host:
end

implementation test for Host:
    \"""
        Bla bla
    \"""
end
"""
    )

    (types, _) = compiler.do_compile()
    assert types["__config__::Host"].implementations[0].comment.strip() == "Bla bla"


def test_doc_string_on_implements(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Host:
end

implementation test for Host:
end

implement Host using test
\"""
    Always use test!
\"""
"""
    )
    (types, _) = compiler.do_compile()

    assert types["__config__::Host"].implements[0].comment.strip() == "Always use test!"
