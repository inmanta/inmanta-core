"""
    Copyright 2018 Inmanta

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

# Snapshot and Restore
PRIO_LOW = 10000
# Dryrun and deploy
PRIO_NOMINAL = 1000
PRIO_MID = 200
# Get Facts
PRIO_HIGH = 100


class PriorityProvider(object):

    def set_priorities(self, generation: "Dict[str, ResourceAction]"):
        """Set scheduling priorities on the resource actions"""
        pass


class StaticChangesFirst(object):

    def __init__(self):
        self.previous = {}

    def is_changed(self, a, b):
        if a is None or b is None:
            return True
        if not a.__class__.fields == b.__class__.fields:
            return True
        for field in a.__class__.fields:
            if getattr(a, field) != getattr(b, field):
                return True
        return False

    def set_priorities(self, generation: "Dict[str, ResourceAction]"):
        changed = []

        for name, ra in generation.items():
            if name not in self.previous:
                changed.append(ra)
            else:
                if self.is_changed(self.previous[name].resource, generation[name].resource):
                    changed.append(ra)

        while changed:
            item = changed.pop()
            if item.priority != PRIO_MID:
                item.priority = PRIO_MID
                changed.extend(item.dependencies)
        self.previous = generation
