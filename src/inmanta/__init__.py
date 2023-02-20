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

COMPILER_VERSION = "2023.1"
RUNNING_TESTS = False
"""
    This is enabled/disabled by the test suite when tests are run.
    This variable is used to disable certain features that shouldn't run during tests.
"""

if __name__ == "__main__":
    import inmanta.app

    inmanta.app.app()
