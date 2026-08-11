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

# Deliberately empty. inmanta.agent.handler is part of the module facing API and is imported by the compiler and by every
# module's Python code, so this package __init__ must stay free of expensive imports. Agent and collect_report used to be
# re-exported here; import them from inmanta.agent.agent_new and inmanta.agent.reporting instead.
