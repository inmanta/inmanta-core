'''
Created on May 30, 2016

@author: wouter
'''

import ruamel.yaml
import os


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
        #print(item, x)
        out.extend(depthFirst(graph, todo, x))
    out.append(item)
    
    return out

if __name__ == '__main__':
    run()
