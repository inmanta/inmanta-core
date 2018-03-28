'''
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
'''
import inmanta.compiler as compiler
from inmanta.export import ModelExporter
import logging
import inmanta.model


class EntityBuilder(object):

    def __init__(self):
        self._model = {}

    def get_model(self):
        return self._model

    def entity(self, type, idx):
        self._entity = {"relations": {}, "attributes": {}, "type": type}
        self._model["%s_%s" % (type, idx)] = self._entity
        return self

    def attribute(self, name):
        self._current = {"values": []}
        self._entity["attributes"][name] = self._current
        return self

    def relation(self, name):
        self._current = {"values": []}
        self._entity["relations"][name] = self._current
        return self

    def value(self, value):
        self._current["values"] += [value]
        return self

    def unknown(self, unknowns):
        if "unknowns" not in self._current:
            self._current["unknowns"] = []
        self._current["unknowns"] += [unknowns]
        return self

    def null(self):
        del self._current["values"]
        self._current["nones"] = [0]
        return self


class TypeBuilder(object):

    def __init__(self):
        self._model = {}

    def get_model(self):
        return self._model

    def entity(self, name, file, lnr, *parents):
        self._instance = {"parents": list(parents),
                          "attributes": {},
                          "relations": {},
                          "location": {"file": file, "lnr": lnr}}
        self._model[name] = self._instance
        return self

    def attribute(self, name, type, file, lnr, multi=False, nullable=False, comment=""):
        x = {"location": {"file": file, "lnr": lnr},
             "type": type,
             "multi": multi,
             "nullable": nullable,
             "comment": comment}

        self._instance["attributes"][name] = x
        return self

    def relation(self, name, type, file, lnr, multi, reverse="", comment=""):
        x = {"location": {"file": file, "lnr": lnr},
             "type": type,
             "multi": multi,
             "reverse": reverse,
             "comment": comment,
             "source_annotations": [],
             "target_annotations": []
             }
        self._instance["relations"][name] = x
        self._relation = x
        return self

    def source_annotate(self, value):
        self._relation["source_annotations"].append(value)
        return self

    def target_annotate(self, value):
        self._relation["target_annotations"].append(value)
        return self


LOGGER = logging.getLogger(__name__)


def test_basic_model_export(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
typedef hoststring as string matching /^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*$/

entity One:
    string name = "a"
    hoststring hostname="bazz"
end

entity Two:
end

dinges = "a"

One.two [1] dinges,one Two.one [0:]

one = One(two=two)
two = Two(one=one)

implementation none for std::Entity:

end

implement One using none
implement Two using none
    """, autostd=False)

    (types, scopes) = compiler.do_compile()

    exporter = ModelExporter(types)

    model = exporter.export_model()
    types = exporter.export_types()

#     LOGGER.debug(yaml.dump(model))
#     LOGGER.debug(yaml.dump(types))

    result = EntityBuilder().entity("__config__::One", 1).\
        attribute("name").value("a").\
        attribute("hostname").value("bazz").\
        relation("provides").\
        relation("requires").\
        relation("two").value("__config__::Two_1").\
        entity("__config__::Two", 1).\
        relation("provides").\
        relation("requires").\
        relation("one").value("__config__::One_1").\
        get_model()

    assert model == result

    main = snippetcompiler.main

    annota = {"value": "a"}
    annotb = {"reference": "__config__::One_1"}

    result = TypeBuilder().entity("std::Entity", "internal", 1).\
        relation("requires", "std::Entity", "internal", 1, [0, -1], "std::Entity.provides").\
        relation("provides", "std::Entity", "internal", 1, [0, -1], "std::Entity.requires").\
        entity("__config__::Two", main, 9, 'std::Entity').\
        relation("one", "__config__::One", main, 14, [0, -1], "__config__::One.two").\
        target_annotate(annota).target_annotate(annotb).\
        entity("__config__::One", main, 4, 'std::Entity').\
        relation("two", "__config__::Two", main, 14, [1, 1], "__config__::Two.one").\
        source_annotate(annota).source_annotate(annotb).\
        attribute("hostname", "__config__::hoststring", main, 6).\
        attribute("name", "string", main, 5).get_model()

    assert result == types

    for mytype in types.values():
        round = inmanta.model.Entity.from_dict(mytype).to_dict()
        assert round == mytype


def test_null_relation_model_export(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity One:
end

One.one [0:] -- One

a = One()
implementation none for std::Entity:

end
implement One using none
""", autostd=False)
    (types, scopes) = compiler.do_compile()
    exporter = ModelExporter(types)

    model = exporter.export_model()
    types = exporter.export_types()

    result = EntityBuilder().entity("__config__::One", 1).\
        relation("provides").\
        relation("requires").\
        relation("one").\
        get_model()

    assert model == result


def test_unknown_relation_model_export(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
import tests
entity One:
end

One.one [0:] -- One

a = One(one=tests::unknown())
implementation none for std::Entity:

end
implement One using none
""", autostd=False)
    (types, scopes) = compiler.do_compile()
    exporter = ModelExporter(types)

    model = exporter.export_model()
    types = exporter.export_types()

    result = EntityBuilder().entity("__config__::One", 1).\
        relation("provides").\
        relation("requires").\
        relation("one").\
        value("_UNKNOWN_").\
        get_model()

    assert model == result


def test_complex_attributes_model_export(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
import tests
entity Two:
    string[] odds
    string? b = null
end


Two(odds=["a",tests::unknown(), tests::unknown(),"d"])

implementation none for std::Entity:

end
implement Two using none

""", autostd=False)
    (types, scopes) = compiler.do_compile()
    exporter = ModelExporter(types)

    model = exporter.export_model()
    types = exporter.export_types()

    result = EntityBuilder().entity("__config__::Two", 1).\
        relation("provides").\
        relation("requires").\
        attribute("odds").\
        value("a").\
        value("d").\
        unknown(1).\
        unknown(2).\
        attribute("b").\
        null().\
        get_model()

    assert model == result

    main = snippetcompiler.main

    result = TypeBuilder().entity("std::Entity", "internal", 1).\
        relation("requires", "std::Entity", "internal", 1, [0, -1], "std::Entity.provides").\
        relation("provides", "std::Entity", "internal", 1, [0, -1], "std::Entity.requires").\
        entity("__config__::Two", main, 3, 'std::Entity').\
        attribute("odds", "string", main, 4, multi=True).\
        attribute("b", "string", main, 5, nullable=True).get_model()

    assert result == types
