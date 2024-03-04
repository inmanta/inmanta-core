
"""
Resourceversion
 -> consists of several versioned resource sets

ActiveModel
 -> active resource version
 -> resource has
      - states https://docs.google.com/presentation/d/1F3bFNy2BZtzZgAxQ3Vbvdw7BWI9dq0ty5c3EoLAtUUY/edit#slide=id.g292b508a90d_0_5
      - relations to other resources (double bound)
      - outstanding tasks
      - propagate messages over provides relations (CAD,...)
 -> can splice in a new Resourceversion
     - lock
     - first build up list of actions
     - when approved run list of actions
     - unlock




"""
