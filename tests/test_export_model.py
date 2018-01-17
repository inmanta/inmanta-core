import inmanta.compiler as compiler
from inmanta.export import ModelExporter
import yaml


def test_basic_model_export(snippetcompiler):
    snippetcompiler.setup_for_snippet("""
entity One:
    string name = "a"
end

entity Two:
end

One.two [1] -- Two.one [1]

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
    
    model_rr = yaml.load(model)
    
    one = {"name":"a", "provides":[], "requires":[]}
    two = {"one":one, "provides":[], "requires":[]}
    one["two"] = two
    rr = [one, two]
    
    print(rr)
    print(model_rr)
    
    model_rr = sorted(model_rr, key=lambda x: dir(x))
    
    assert model_rr==rr