"""
    Copyright 2017 Inmanta

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
import tempfile
import shutil
import os

from inmanta import module, config, compiler
import pytest


class Exporter(object):
    def __init__(self):
        self.project_dir = None

    def setup(self):
        self.project_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(self.project_dir, ".env"))
        os.mkdir(os.path.join(self.project_dir, "libs"))

        with open(os.path.join(self.project_dir, "project.yml"), "w") as cfg:
            yaml = """
            name: snippet test
            modulepath: [libs, %s]
            downloadpath: libs
            version: 1.0
            repo:
                - https://github.com/inmanta/
            """ % os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modules")
            cfg.write(yaml)

    def cleanup(self):
        if self.project_dir is not None:
            shutil.rmtree(self.project_dir)


    def export(self, code, json=True):
        with open(os.path.join(self.project_dir, "main.cf"), "w") as x:
            x.write(code)

        module.Project.set(module.Project(self.project_dir, autostd=True))

        config.Config.load_config()
        from inmanta.export import Exporter

        (types, scopes) = compiler.do_compile()

        class Options(object):
            pass

        options = Options()
        options.json = json
        options.depgraph = False
        options.deploy = False
        options.ssl = False

        export = Exporter(options=options)
        return export.run(types, scopes)


@pytest.fixture(scope="function")
def exporter():
    exp = Exporter()
    exp.setup()

    yield exp

    exp.cleanup()


def test_id_mapping_export(exporter):
    _version, json_value = exporter.export(code="""import exp

        exp::Test(name="a", agent="b")
        """)

    assert(len(json_value) == 1)
    resource = list(json_value.values())[0]
    assert(resource.id.attribute_value == "test_value_a")


def test_unknown_agent(exporter):
    _version, json_value = exporter.export(code="""import exp
        import tests

        exp::Test(name="a", agent=tests::unknown())
        """)

    assert(len(json_value) == 0)

def test_unknown_attribute_value(exporter):
    _version, json_value = exporter.export(code="""import exp
        import tests

        exp::Test(name=tests::unknown(), agent="b")
        """)

    assert(len(json_value) == 0)
