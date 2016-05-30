"""
    Copyright 2016 Inmanta

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

import os

import ruamel.yaml


def run():

    requires = {}

    for dirpath, dirnames, files in os.walk("."):
        for name in files:
            if name == "module.yml":
                name = os.path.join(dirpath, name)
                with open(name, "r") as fd:
                    data = ruamel.yaml.load(fd.read(), ruamel.yaml.RoundTripLoader)
                    if "requires" not in data:
                        requires[os.path.basename(dirpath)] = []
                    else:
                        requires[os.path.basename(dirpath)] = [x for x in data["requires"]]

    out = depthFirstWrapper(requires, set(requires.keys()))
    print('\n'.join(out))


def depthFirstWrapper(graph, todo):
    out = []
    while len(todo) > 0:
        item = next(iter(todo))
        out.extend(depthFirst(graph, todo, item))
    return out


def depthFirst(graph, todo, item):
    if item not in todo:
        return []
    deps = graph[item]
    out = []
    todo.remove(item)
    for x in deps:
        # print(item, x)
        out.extend(depthFirst(graph, todo, x))
    out.append(item)

    return out

if __name__ == '__main__':
    run()
