Compatibility
*************

.. only:: iso

    This page shows the compatibility for version |version_major| of the Inmanta Service Orchestrator with other
    components on the host system running the orchestrator.
    It also shows advanced information for Inmanta extension developers regarding the compatible version ranges
    for the python packages that compose this version of the Inmanta Service Orchestrator.
    It also shows the set of Inmanta modules that come along with this release of the Inmanta Service Orchestrator
    and their respective version.

.. only:: oss

    This page shows the compatibility of Inmanta version |release| with other
    components on the host system running the orchestrator.
    It also shows the set of Inmanta modules that come along with this release of Inmanta and their respective version.

.. datatemplate:json:: /reference/compatibility.json
   :template: system_requirements.tmpl

.. only:: iso

    .. datatemplate:json:: /reference/compatibility.json
       :template: components_requirements.tmpl

.. datatemplate:json:: /reference/compatibility.json
   :template: module_sets.tmpl
