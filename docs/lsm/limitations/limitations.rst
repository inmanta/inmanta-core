***********
Limitations
***********

This section describes some limitations of the ``lsm`` module.

A ServiceEntity cannot contain resource in the undefined state
##############################################################

The ``resources`` attribute of a ``ServiceEntity`` cannot contain resources which are in the deployment state ``undefined``. If
the ``resources`` attribute does contain such a resource, the lifecycle state machine will get stuck in its current state and
the deployment of the service will hang.
