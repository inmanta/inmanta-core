import inmanta.compiler as compiler
from inmanta.export import ModelExporter
import yaml
import logging


class entity_builder(object):

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


class type_builder(object):

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
    """,  autostd=False)

    (types, scopes) = compiler.do_compile()

    rootType = types["std::Entity"]
    exporter = ModelExporter(rootType, types)

    model = exporter.export_model()
    types = exporter.export_types()

    LOGGER.debug(yaml.dump(model))
    LOGGER.debug(yaml.dump(types))

    result = entity_builder().entity("__config__::One", 1).\
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

    result = type_builder().entity("std::Entity", "internal", 0).\
        relation("requires", "std::Entity", "internal", 0, [0, None], "std::Entity.provides").\
        relation("provides", "std::Entity", "internal", 0, [0, None], "std::Entity.requires").\
        entity("__config__::Two", main, 9, 'std::Entity').\
        relation("one", "__config__::One", main, 14, [0, None], "__config__::One.two").\
        target_annotate(annota).target_annotate(annotb).\
        entity("__config__::One", main, 4, 'std::Entity').\
        relation("two", "__config__::Two", main, 14, [1, 1], "__config__::Two.one").\
        source_annotate(annota).source_annotate(annotb).\
        attribute("hostname", "__config__::hoststring", main, 6).\
        attribute("name", "string", main, 5).get_model()

    assert result == types
