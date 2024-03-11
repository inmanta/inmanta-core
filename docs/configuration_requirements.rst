Compatibility
*************

.. only:: iso

    This page shows the compatibility for version |version_major| of the Inmanta Service Orchestrator with other components.
    These compatible versions are defined for the whole lifetime of this major version i.e.
    they are not pinned to a specific three-digit version. Upper bounds may be added when a new major version is released.


.. only:: oss

    This page shows the compatibility of Inmanta version |release| with other components.


.. datatemplate:json:: compatibility.json
   :template: system_requirements.tmpl

.. only:: iso

    .. datatemplate:json:: compatibility.json
       :template: components_requirements.tmpl

    .. note::

        A machine-consumable json file with these versions is available at https://docs.inmanta.com/inmanta-service-orchestrator-dev/|version_major|/requirements.components.txt
