Inmanta Expert Features
=======================

This page documents the set of expert features for the Inmanta application and extensions.

.. attention::

        "With great power comes great responsibility"

    These features have to be used with extreme caution. Make sure you are fully aware of what they do before using
    them. These feature allow you to bypass safety checks that the product offers and/or that were put in place by
    the model developers.

Compiler expert features
########################

Allow handler code update during a partial compile
--------------------------------------------------


By default, updating handler code is only allowed during full compiles. A
safety check is performed during partial compiles to make sure that inmanta
module code remains consistent across partial versions.

If a full compile cannot be performed and handler code update is necessary,
it is possible to disable the version consistency check and to allow handler
code update in a manual export as follows:



.. danger::
    The updated code will be used for all handlers and resources, even if they are not in this partial compile.
    Make sure the updated handler code is compatible with all resource
    schemas it might have to process. Uploading incompatible handler code can lead
    to very hard to diagnose issues.

.. admonition::
    How-to

    To allow handler code update during a partial compile, pass the
    :command:`--allow-handler-code-update` option to the :command:`export` command.

    .. code-block:: bash

        inmanta -vv -X export --partial --allow-handler-code-update



.. only:: iso

    Lsm extension expert features
    #############################

    To access expert features of the lsm extension, toggle the
    :inmanta.environment-settings:setting:`enable_lsm_expert_mode` environment setting. This will unlock
    the features described below as long as the setting is still enabled. Make sure you disable it again when
    you're done.

    .. danger::
        A service lifecycle describes how a service can/cannot evolve during its lifespan as a finite state
        machine. An integral part of The LSM extension is to uphold these constraints by performing safety
        check on each transition request.

        Using LSM expert features explicitly bypasses these safety checks, which means that incorrect usage
        can lead to a broken desired state and break future compilations.

        These features should never be used, unless you have a very good reason to, you fully understand
        why the safety checks are there in the first place, and why it is ok to bypass them for your
        specific use case.



    Forcefully set a service in a state
    -----------------------------------

    .. danger::
        This will forcefully set the service in the selected state, regardless of the limitations
        imposed by the lifecycle. This will bypass all safety checks performed during regular
        "update" state transfer.


    .. admonition::
        How-to

        In the service instance view, click the :command:`Expert Actions` button, and then
        select the new state from the :command:`Force state` section of the drop-down menu.


    Forcefully destroy a service
    ----------------------------

    .. danger::
        This will forcefully delete the service, regardless of the limitations
        imposed by the lifecycle. This will bypass all safety checks performed during regular
        "delete" state transfer. This will make the orchestrator "forget" the service ever existed
        without performing the on-delete cleanup actions registered in the lifecycle.
        The resources associated with this service would only be removed in the following compile
        involving this service.


    .. admonition::
        How-to

        In the service instance view, click the :command:`Expert Actions` button, and then
        select :command:`Destroy` from the drop-down menu.


    Forcefully update attributes of a service
    -----------------------------------------

    .. danger::
        This will forcefully update attributes of a service, regardless of their attribute modifier. This will bypass
        all safety checks performed during regular "update" state transfer and will not trigger a state transfer.
        No validation check is performed on the provided attributes. E.g. for ``r`` attributes, the associated inventory
        will not be notified that a given value is now being used/no longer being used.


    .. admonition::
        How-to

        In the service instance view, select the :command:`Attributes` tab, and then
        select the :command:`JSON` tab. Update the attributes and click the :command:`Force Update` button.

