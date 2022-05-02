"""
    Copyright 2022 Inmanta

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
import math

from inmanta.plugins import PluginException, plugin


@plugin
def power(base: "int", exponent: "int") -> "int":
    return base**exponent


@plugin
def root(square: "int") -> "int":
    result: float = math.sqrt(square)
    if not result.is_integer():
        raise PluginException("%d is not a square of an integer" % square)
    return int(result)
