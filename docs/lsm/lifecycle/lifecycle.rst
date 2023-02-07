.. _lifecycle:

*********
Lifecycle
*********

Lifecycle State Labels
######################

Each state in the lifecycle has a ``label`` attribute, which is used by the UI to mark service instances in these states visually,
according to the labels.

The possible values are:

* **info**: This is the default label, it represents states the instance goes through normally, which don't require special attention.
* **success**: This label should be used for states when there are no problems with the instance, and it's stable in this state.
* **warning**: The warning label should be applied for states where the instance requires attention, because it might have run into some problems.
* **danger**: The danger label represents the situation when there are serious problems with the instance.


Lifecycle construction
######################
When creating a new lifecycle, it is important to know where validation states should be added in order to avoid invalid lifecycles.

Creating/deleting and exporting/not-exporting states
****************************************************
If services are guaranteed to be independent, the validation states can be ommited.
If one service depends on another, they could conflict when creating/exporting. If an Entity ``Child`` has an :ref:`inter_service_relation <inter_service_relations>` to another Entity ``Parent``, than the ``Parent`` instance should be created first. Otherwise ``Child`` will have a dangling reference.
Another way they could come into conflict is if they use any kind of identifier: Multiple instances could be created with the same identifier.
Conflicts could also arise when deleting/not-exporting: If the ``Parent`` instance used in a ``Child`` is deleted, ``Child`` will have a reference to something that no longer exist, which will result in an invalid desired state (see :ref:`delete_validating`).
