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
import pytest

import inmanta.compiler as compiler
from inmanta.ast import AttributeException, OptionalValueException, RuntimeException


def test_list_atributes(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Jos:
  bool[] bar
  std::package_state[] ips = ["installed"]
  string[] floom = []
  string[] floomx = ["a", "b"]
  string box = "a"
end

implement Jos using std::none

a = Jos(bar = [true])
b = Jos(bar = [true, false])
c = Jos(bar = [])
d = Jos(bar = [], floom=["test","test2"])

"""
    )
    (_, root) = compiler.do_compile()

    def check_jos(jos, bar, ips=["installed"], floom=[], floomx=["a", "b"], box="a"):
        jos = jos.get_value()
        assert jos.get_attribute("bar").get_value() == bar
        assert jos.get_attribute("ips").get_value(), ips
        assert jos.get_attribute("floom").get_value() == floom
        assert jos.get_attribute("floomx").get_value() == floomx
        assert jos.get_attribute("box").get_value() == box

    scope = root.get_child("__config__").scope

    check_jos(scope.lookup("a"), [True])
    check_jos(scope.lookup("b"), [True, False])
    check_jos(scope.lookup("c"), [])
    check_jos(scope.lookup("d"), [], floom=["test", "test2"])


def test_list_atribute_type_violation_1(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Jos:
  bool[] bar = true
end
implement Jos using std::none
c = Jos()
"""
    )
    with pytest.raises(RuntimeException):
        compiler.do_compile()


def test_list_atribute_type_violation_2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Jos:
  bool[] bar = ["x"]
end
implement Jos using std::none
c = Jos()
"""
    )
    with pytest.raises(RuntimeException):
        compiler.do_compile()


def test_list_atribute_type_violation_3(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Jos:
  bool[] bar
end
implement Jos using std::none
c = Jos(bar = ["X"])
"""
    )
    with pytest.raises(RuntimeException):
        compiler.do_compile()


def test_issue_235_empty_lists(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test1:

end
implement Test1 using std::none

entity Test2:
end
implement Test2 using std::none

Test1 tests [0:] -- [0:] Test2 tests

t1 = Test1(tests=[])
std::print(t1.tests)
"""
    )
    (_, root) = compiler.do_compile()
    scope = root.get_child("__config__").scope

    assert scope.lookup("t1").get_value().get_attribute("tests").get_value() == []


def test_608_list_to_list(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1:] -- A

entity C:
    string name
end

C.a [0:] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")
a2 = A(name="a2")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = a1
b1.a = c1.a
"""
    )
    (_, scopes) = compiler.do_compile()


def test_608_list_to_single(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1] -- A

entity C:
    string name
end

C.a [0:] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")
a2 = A(name="a2")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = c1.a
"""
    )
    with pytest.raises(AttributeException):
        (_, scopes) = compiler.do_compile()


def test_608_opt_to_list(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1:] -- A

entity C:
    string name
end

C.a [0:1] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")
a2 = A(name="a2")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = a1
b1.a = c1.a
"""
    )
    with pytest.raises(OptionalValueException):
        (_, scopes) = compiler.do_compile()


def test_608_opt_to_single(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1] -- A

entity C:
    string name
end

C.a [0:1] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = a1
b1.a = c1.a
"""
    )
    with pytest.raises(OptionalValueException):
        (_, scopes) = compiler.do_compile()


def test_608_opt_to_single_2(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
implementation none for std::Entity:
end

entity A:
    string name
end

entity B:
    string name
end

B.a [1] -- A

entity C:
    string name
end

C.a [0:1] -- A

implement A using none
implement B using none
implement C using none

a1 = A(name="a1")

b1 = B(name="b1")

c1 = C(name="c1")

b1.a = a1
b1.a = c1.a

c1.a = a1
"""
    )
    (_, scopes) = compiler.do_compile()


def test_633_default_on_list(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Foo:
   list first=[]
   list second=["a", "b"]
   string[] third=["a", "b"]
end

implementation none for std::Entity:
end

implement Foo using none

foo = Foo()
"""
    )
    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    foo = root.lookup("foo").get_value()

    ab = foo.get_attribute("first").get_value()
    assert ab == []

    second = foo.get_attribute("second").get_value()
    assert second == ["a", "b"]

    third = foo.get_attribute("third").get_value()
    assert third == ["a", "b"]


def test_673_in_list(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Test:
    string[] attributes
end

implementation test for Test:

end

implement Test using test when "foo" in self.attributes

Test(attributes=["blah", "foo"])
"""
    )
    compiler.do_compile()


def test_552_string_rendering_for_lists(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Network:
    string[] tags=[]
end

implement Network using std::none

net1 = Network(tags=["vlan"])
a="Net has tags {{ net1.tags }}"
"""
    )

    (_, scopes) = compiler.do_compile()

    root = scopes.get_child("__config__")
    a = root.lookup("a").get_value()

    assert a == """Net has tags ['vlan']"""


def test_emptylists(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
    implement std::Entity using std::none

    a=std::Entity()
    b=std::Entity()
    c=std::Entity()

    a.provides = b.provides
    b.provides = c.provides
    """
    )
    compiler.do_compile()


def test_653_list_attribute_unset(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        entity Test:
            string[] bla
        end

        Test()

        implement Test using std::none
        """,
        "The object __config__::Test (instantiated at {dir}/main.cf:6) is not complete:"
        " attribute bla ({dir}/main.cf:3:22) requires 1 values but only 0 are set",
    )


def test_1422_gradual_array(snippetcompiler):
    snippetcompiler.setup_for_snippet(
        """
entity Cluster:
end

implement Cluster using agentConfig

implementation agentConfig for Cluster:
    a = std::AgentConfig(autostart=true, agentname="", uri="local:" )
    a.provides = [self, self.provides, self.provides]
end

entity K8sYamlResource extends std::PurgeableResource:
    string yamldict
end

K8sYamlResource.cluster [1] -- Cluster

implement K8sYamlResource using k8sYamlResource

implementation k8sYamlResource for K8sYamlResource:
    self.requires += self.cluster
end


entity K8sResource extends std::PurgeableResource:
end

K8sResource.clusters [1:] -- Cluster

entity Deployment extends K8sResource:
end

implement Deployment using deployment when self.security_capabilities is defined
implement Deployment using deployment when not self.security_capabilities is defined

implementation deployment for Deployment:
    YamlResource(yaml="", clusters=self.clusters)
end

entity YamlResource extends std::PurgeableResource:
    string yaml
end

implement YamlResource using yamlResource

YamlResource.clusters [1:] -- Cluster

implementation yamlResource for YamlResource:
    for cluster in self.clusters:
       K8sYamlResource(yamldict=self.yaml, cluster=cluster)
    end
end

Deployment.security_capabilities[0:1] -- SecurityCapabilities
entity SecurityCapabilities:
end
implement SecurityCapabilities using std::none

cluster = Cluster()
deployment2 = Deployment(
    clusters=cluster,
)
"""
    )

    (_, scopes) = compiler.do_compile()


def test_1435_instance_in_list(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity A:
end
implement A using std::none

entity ListContainer:
    list lst
end

implement ListContainer using std::none

x = ListContainer()
x.lst = [x]
        """,
        "Could not set attribute `lst` on instance `__config__::ListContainer (instantiated at {dir}/main.cf:12)`"
        " (reported in x.lst = List() ({dir}/main.cf:13))"
        "\n"
        "caused by:"
        "\n"
        "  Invalid value '__config__::ListContainer (instantiated at {dir}/main.cf:12)', expected Literal"
        " (reported in x.lst = List() ({dir}/main.cf:13))",
    )
