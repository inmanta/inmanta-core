
# Snapshot and Restore
PRIO_LOW = 10000
# Dryrun and deploy
PRIO_NOMINAL = 1000
PRIO_MID = 200
# Get Facts
PRIO_HIGH = 100


class PriorityProvider(object):

    def set_priorities(self, generation: "Dict[str, ResourceAction]"):
        """ set scheduling priorities on the resource actions"""
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