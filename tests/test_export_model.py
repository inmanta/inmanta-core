import inmanta.compiler as compiler
from inmanta.export import ModelExporter
import yaml
import logging


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
