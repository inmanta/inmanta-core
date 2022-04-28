"""
    Copyright 2020 Inmanta

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

from inmanta.config import Option, is_bool, is_str

datatrace_enable: Option[bool] = Option(
    "compiler",
    "datatrace_enable",
    False,
    "Enables the experimental datatrace application on top of the compiler."
    " The application should help in identifying the cause of compilation errors"
    " during the development process.",
    is_bool,
)

dataflow_graphic_enable: Option[bool] = Option(
    "compiler",
    "dataflow_graphic_enable",
    False,
    "Enables graphic visualization of the data flow in the model. Requires the datatrace_enable option. Requires graphviz.",
    is_bool,
)


def track_dataflow() -> bool:
    return datatrace_enable.get() or dataflow_graphic_enable.get()


feature_compiler_cache: Option[bool] = Option(
    "compiler",
    "cache",
    True,
    "Enables the caching of compiled files.",
    is_bool,
)


export_compile_data: Option[bool] = Option(
    "compiler",
    "export_compile_data",
    False,
    "Export structured json containing compile data such as occurred errors.",
    is_bool,
)


default_compile_data_file: str = "compile_data.json"


export_compile_data_file: Option[str] = Option(
    "compiler",
    "export_compile_data_file",
    default_compile_data_file,
    "File to export compile data to. If omitted %s is used." % default_compile_data_file,
    is_str,
)
