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


def test_plugin_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
        import std
        std::template("/tet.tmpl")
""",
        """Exception in plugin std::template (reported in std::template('/tet.tmpl') ({dir}/main.cf:3))
caused by:
  jinja2.exceptions.TemplateNotFound: /tet.tmpl
""",
    )
