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

import sys
from typing import Callable, TextIO

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


data_export: Option[bool] = Option(
    "compiler", "data_export", False, "Export structured json containing compile data such as occurred errors.", is_bool,
)


STDOUT_REPR = "-"


data_export_file: Option[str] = Option(
    "compiler",
    "data_export_file",
    STDOUT_REPR,
    "File to export compile data to. If omitted or set to %s stdout is used." % STDOUT_REPR,
    is_str,
)


def do_data_export(do_write: Callable[[TextIO], None]) -> None:
    """
        Exports to the configured file, using do_write to do the actual export. Overwrites file content.
        :param do_write: function that writes export data to a given file.
    """
    file_name: str = data_export_file.get()
    if file_name == STDOUT_REPR:
        do_write(sys.stdout)
    else:
        with open(file_name, "w") as f:
            do_write(f)
