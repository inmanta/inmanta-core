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

from typing import TYPE_CHECKING

# flake8: noqa: F401
# Agent and collect_report are kept importable from this package for backward compatibility, but are resolved lazily by
# __getattr__ below. Importing agent_new eagerly pulls the scheduler and the whole server into the import graph of everything
# that touches inmanta.agent, including the compiler.
if TYPE_CHECKING:
    from inmanta.agent.agent_new import Agent
    from inmanta.agent.reporting import collect_report


def __getattr__(name: str) -> object:
    if name == "Agent":
        from inmanta.agent import agent_new

        return agent_new.Agent
    if name == "collect_report":
        from inmanta.agent import reporting

        return reporting.collect_report
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
