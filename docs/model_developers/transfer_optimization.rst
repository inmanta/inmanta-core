*********************
Transfer optimization
*********************

By default, the Inmanta server performs a new compile every time a service instance transfers into a new state.
In practice it often happens that a transition between two states doesn't result in a new desired state for
the service instance. In these situations an unnecessary compile is done. The LSM module now has support to indicate
which transfers don't result in a new desired state, so that these redundant compilations can be prevented, resulting
in better performance.

Annotating transfers as desired state preserving
================================================

The ``lsm::StateTransfer`` entity has two attributes to indicate the transfer preserved the desired state:

* `bool target_same_desired_state=false`: True iff following the success edge doesn't change the desired state.
* `bool error_same_desired_state=false`: True iff following the error edge doesn't change the desired state.

The code snippet below models a lifecycle containing state preserving transitions:

.. todo::

    Add diagram + discuss


Enabling the transfer optimization feature
==========================================

The environment setting :inmanta.environment-settings:setting:`enable_lsm_transfer_optimization` can be used to enable
the transfer optimization feature. When enabled, the LSM extension will perform a compile when transitioning between
two states that don't preserve the desired state. When disabled, a recompile will be done for each state transition.
Validation compiles are not impacted by this setting. They are always executed.

.. todo::

    Explain common situation when transfers cannot be state preserving
