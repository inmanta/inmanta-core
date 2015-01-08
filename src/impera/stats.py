"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contect: bart@impera.io
"""

import json


class Stats(object):
    _st = {}

    @classmethod
    def get(cls, name):
        """
            Get a reference to a stats object
        """
        if name not in cls._st:
            cls._st[name] = Stats(name)

        return cls._st[name]

    def __init__(self, name):
        self._counter = 0
        self._name = name

    def count(self):
        """
            Get the lock count
        """
        return self._counter

    def increment(self, step=1):
        """
            Increment the count
        """
        self._counter += step

    @classmethod
    def dump(cls):
        """
        Get all stats and dump them
        """
        data = {}
        for name, stat in cls._st.items():
            data[name] = stat.count()

        with open("stats.json", "w+") as fd:
            json.dump(data, fd)


class TemplateStats(object):
    instance = None

    def __init__(self, template_name):
        self._access = []
        self._template_name = template_name

        TemplateStats.instance = self

    def record_access(self, varstr, value, index, _type):
        self._access.append((varstr, value, index, _type))

    def get_stats(self):
        return self._access
