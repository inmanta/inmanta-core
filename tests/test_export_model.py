import inmanta.compiler as compiler
from inmanta.export import ModelExporter
import yaml


class entity_builder:

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


def test_basic_model_export(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity One:
    string name = "a"
end

entity Two:
end

One.two [1] -- Two.one [0:]

one = One(two=two)
two = Two(one=one)

implementation none for std::Entity:

end

implement One using none
implement Two using none
    """,  autostd=False)

    (types, scopes) = compiler.do_compile()

    rootType = types["std::Entity"]
    exporter = ModelExporter(rootType)

    model = exporter.export_model()

    result = entity_builder().entity("__config__::One", 1).\
        attribute("name").value("a").\
        relation("provides").\
        relation("requires").\
        relation("two").value("__config__::Two_1").\
        entity("__config__::Two", 1).\
        relation("provides").\
        relation("requires").\
        relation("one").value("__config__::One_1").\
        get_model()

    print(result)
    print(model)

    assert model == result
