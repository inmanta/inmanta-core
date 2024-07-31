*********************
Transfer optimization
*********************

By default, the Inmanta server performs a new compile every time the state of a service instance changes.
However, in practice it often happens that a transition between two states doesn't result in a new desired state for
the service instance. To prevent unnecessary compiles, the LSM module has support to indicate which
transfers in a lifecycle preserve the desired state. The Inmanta server can then use this information to improve the
performance of state transitions. This page describes how to mark transfers in a lifecycle as state-preserving
and how to enable the transfer optimization feature on the server.

Annotating desired state-preserving transfers
=============================================

The ``lsm::StateTransfer`` entity has two attributes to indicate that a transfer preserves the desired state:

* `bool target_same_desired_state (default=false)`: True iff following the success edge doesn't change the desired state.
* `bool error_same_desired_state (default=false)`: True iff following the error edge doesn't change the desired state.

The code snippet below models a lifecycle that contains state-preserving transfers:

.. literalinclude:: sources/basic_lifecycle.cf
    :language: inmanta
    :lines: 1-100
    :linenos:

Let's discuss the transfers that are not marked as state-preserving and why:

* start -> creating: Not a state-preserving transfer because it moves the instances from a non-exporting
  state to an exporting state.
* up -> deleting: Not a state-preserving transfer because this state transfer flips the ``purge_resources`` flag,
  which will have an effect on the desired state being deployed.
* deleting -> terminated: Not a state-preserving transfer because it moves the instance from an exporting to a
  non-exporting state.

All other transfers were marked as state-preserving transfers. This decision was based on the assumption that not
changing the high-level intent (active attribute set) doesn't change the low-level intent (what is deployed to the
infrastructure). This assumption doesn't hold in all situations. The service model could for example change the
low-level intent based on the current state of the service instance. Caution is advised when modelling a lifecycle
with state-preserving transfer, as incorrectly marking a transfer as state-preserving will cause the orchestrator
to behave incorrectly.

Enabling the transfer optimization feature
==========================================

The environment setting :inmanta.environment-settings:setting:`enable_lsm_transfer_optimization` can be used to enable
the transfer optimization feature. When enabled, the LSM extension will perform a compile only when transitioning between
two states that don't preserve the desired state. When disabled, a recompile will be done for each state transition.
Validation compiles are not impacted by this setting. They are always executed.

Testing
=======

The Inmanta server validates every lifecycle that is exported to the server and it will reject any lifecycle with
incorrect state-preserving transfers. The server will for example reject lifecycles with state-preserving transfers
that connect a state that exports resources with a state that doesn't export resources. However, the server cannot
exhaustively detect all cases where transfers are incorrectly marked as state-preserving. As such, it's important to
add tests that validate whether the service model behaves consistently, whether or not the
:inmanta.environment-settings:setting:`enable_lsm_transfer_optimization` environment setting is enabled.
