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
import time

from tornado import gen
from tornado.gen import sleep


@gen.coroutine
def retry_limited(fun, timeout):
    start = time.time()
    while time.time() - start < timeout and not fun():
        yield sleep(0.1)
    if not fun():
        raise AssertionError("Bounded wait failed")


UNKWN = object()


def assert_equal_ish(minimal, actual, sortby=[]):
    if isinstance(minimal, dict):
        for k in minimal.keys():
            assert_equal_ish(minimal[k], actual[k], sortby)
    elif isinstance(minimal, list):
        assert len(minimal) == len(actual), "list not equal %s != %s" % (minimal, actual)
        if len(sortby) > 0:
            def keyfunc(val):
                if not isinstance(val, dict):
                    return val
                key = [str(val[x]) for x in sortby if x in val]
                return '_'.join(key)
            actual = sorted(actual, key=keyfunc)
        for (m, a) in zip(minimal, actual):
            assert_equal_ish(m, a, sortby)
    elif minimal is UNKWN:
        return
    else:
        assert minimal == actual


def assert_graph(graph, expected):
    lines = ["%s: %s" % (f.id.get_attribute_value(), t.id.get_attribute_value()) for f in graph.values() for t in f.requires]
    lines = sorted(lines)

    elines = [x.strip() for x in expected.split("\n")]
    elines = sorted(elines)

    assert elines == lines, (lines, elines)


def expandToGraph(inp, types, version, values, agents, extra):
    """expect graph input in the form
            A1: B1 B2

        types = {"A": "test::Alpha", "B": "test::Beta", "C": "test::Gamma"}
    """
    lines = inp.split("\n")

    all_nodes = set()
    parts = {}
    for line in lines:
        if ":" not in line:
            parts[line.strip()] = []
            all_nodes.add(line.strip())
        else:
            k, v = line.split(": ")
            v = v.split(" ")
            k = k.strip()
            if k in parts:
                raise Exception("Bad test case %s in %s", k, parts)
            parts[k] = v
            all_nodes.add(k)
            all_nodes.update(set(v))

    # Also add nodes not having dependencies
    terminals = all_nodes.difference(parts.keys())

    for t in terminals:
        parts[t] = []

    out = []

    def id_for(k):
        mytype = types[k[0]]
        return '%s[%s,key=%s],v=%s' % (mytype, agents[k], k, version)

    for k, vs in parts.items():
        v = {
            'key': k,
            'value': values[k],
            'agent': agents[k],
            'id': id_for(k),
            'requires': [id_for(val) for val in vs],
        }
        v.update(extra)
        out.append(v)

    return out
