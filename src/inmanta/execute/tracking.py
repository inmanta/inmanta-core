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


"""
This module enables tracking of object construction.

Tracker object are attached to all created Instances in the field trackers. Every Instance can have one or more Trackers.

If the Tracker object is a ModuleTracker, the object is created at module level
If the Tracker object is an ImplementsTracker, the object is created in an Implementation block

"""


class Tracker(object):

    pass


class ModuleTracker(Tracker):

    def __init__(self, block):
        self.block = block
        self.namespace = block.namespace

    def get_next(self):
        return []


class ImplementsTracker(Tracker):

    def __init__(self, subc, instance):
        self.instance = instance
        self.subc = subc
        self.implements = subc.implements
        self.implementations = self.implements.implementations

    def get_next(self):
        return self.instance.trackers
