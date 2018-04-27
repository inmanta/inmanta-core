
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

    def set_priorities(self, generation: "Dict[str, ResourceAction]"):
        changed = []

        for name, ra in generation.items():
            if name not in self.previous:
                changed.append(ra)
            else:
                if changed(self.previous[name].resource, generation[name].resource):
                    changed.append(ra)

        while changed:
            item = changed.pop()
            if item.priority != PRIO_MID:
                item.priority = PRIO_MID
                changed.extend(item.dependencies)