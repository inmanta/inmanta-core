Glossary
========

.. glossary::
    :sorted:


    configuration model
        The :term:`desired state` of the an :term:`environment` is expressed in the configuration
        model. This model defines the desired state of all resources that need to be managed by
        Inmanta.

    project
        The management server of the Inmanta orchestrator can manage distinctive infrastructures.
        Each distinct infrastructure is defined in the server as a project. Each project consists of
        one or more :term:`environment` such as development, integration and production.

    environment
        Each environment represents a target infrastructure that inmanta manages. At least
        environment is required, but often multiple environments of the same infrastructure are
        available such as development, integration and testing.

    agent
        Agents group :term:`resources<resource>` This grouping is free to choose by the designer of
        a resource, however this determines

    resource
        Inmanta orchestrates and manages resources, of any abstraction level, in an infrastructure.
        Examples of resources are: files and packages on a server, a virtual machine on a
        hypervisor, a managed database as a PaaS provider, a switch port on a switch, ...

        A resource has attributes that express the desired value of a property of the resource it
        represents in the infrastructure. For example the
        :inmanta:attribute:`mode<std::File.mode>` attribute of the the :inmanta:entity:`std::File`
        resource. This attribute indicates the desired permissions of a UNIX file.

        A resource needs to have a unique identifier in an environment. This identifier needs to be
        derived from attributes of the resource. This ensures that the orchestrator can (co-)manage
        existing resources and allows quick recovery of the orchestrator in failure conditions. This
        unique identifier is consists of multiple fields. For example,
        ``std::File[vm1,path="/etc/motd"]`` This id contains the type of the resource, the name of
        the :term:`agent` and the unique id with its value for this resource. The resource designer
        determines how this id is derived.

        The fields in the id are:

        * The first field is the type of the resource. For example: ``std::File``
        * The second field is the name of the agent that manages/groups the resource. For example:
          the name of the machine on  which the file is defined ``vm1``
        * The third field is the identifying attribute and the value of this attribute. For example:
          the ``path`` of the file uniquely idenfies a file on a machine.

    module
        A :term:`configuration model` consists of multiple configuration modules. A module provides
        a partial and reusable configuration model and its related resources such as files,
        templates, ... The :doc:`module developer guide<guides/modules>` provides more details.

    resource handler
        See :term:`handler`

    handler
        A handler provides the interface between a resource in the model and the resource in the
        infrastructure. The agent loads the handler and uses it to read the current state, discover
        :term:`facts` and make changes to the real resource.

    desired state
        The desired state expresses the state of all resources that Inmanta manages. Expressing a
        configuration in function of desired state makes the orchestrator more robust to failures
        compared to imperative based orchestration. An agent uses a :term:`handler` to read the
        current state of the a resource and derive from the difference between current and desired
        state the actions required to change the state of the resource. Desired state has the
        additional benefit that Inmanta can show a dry run or execution plan of what would change if
        a new configuration is deployed.

        Imperative solutions require scripts that execute low level commands and handle all possible
        failure conditions. This is similar to how a 3D printer functions: a designer send the
        desired object (desired state) to the 3D printer software and this printer converts this to
        layers that need to be printed. An imperative 3D model, would require the designer to define
        all layers and printer head movements.

    orchestration
        Orchestration is the process of provisioning resources in the correct order and when they
        are available configuring them. Inmanta support both provisioning and configuring resources
        but can also delegate tasks to other (existing) tools.

    plugin
        A plugin is a python function that can be used in the :term:`DSL`. This function recieves
        arguments from the configuration model and navigate relations and read attributes in the
        runtime model. Each function can also return a value to the model. Plugins are used for
        complex transformation based on data in the configuration model or to query external systems
        such as CMDBs or IPAM tools.

    DSL
        Domain specific language. An Inmanta configuration model is written in a the Inmanta
        modelling DSL.

    unknown
        A user always provides a complete configuration model to the orchestrator. Depending on what
        is already deployed, Inmanta will determine the correct order of provisioning and
        configuration. Many configuration parameters, such a the IP address of a virtual machine at
        a cloud provider will not be known upfront. Inmanta marks this parameters as **unknown**.
        The state of any resource that uses such an unknown parameter becomes undefined.

    entity
        Concepts in the infrastructure are modelled in the configuration with entities. An entity
        defines a new type in the configuration model. See :ref:`lang-entity`.

    instance
        An *instance* of an :term:`entity`. See also :ref:`lang-instance`.

    relation
        An attribute of an entity that references an other entity. Plugins, such as templates, can
        navigate relations. See also :ref:`lang-relation`.

    main.cf
        The file that defines the starting point of a configuration model. This file often only
        instantiates some high level entities and imports specific module.

    facts
        A resource in an infrastructure may have multiple properties that are not managed by Inmanta
        but their value is required as input in the configuration or for reporting purposes.
        :term:`handlers<handler>` take care of extracting these facts and reporting them back to the
        server.

    infrastructure
        That what Inmanta manages. This could be virtual machines with resources in these virtual
        machines. Physical servers and their os. Containers or resources at a cloud provider without
        any servers (e.g. "serverless")

    infrastructure-as-code
        Wikepedia defines "Infrastructure as code" as *the process of managing and provisioning
        computer data centers through machine-readable definition files, rather than physical
        hardware configuration or interactive configuration tools.* Inmanta achieves this by using a
        desired state configuration model that is entirely expressed in code.
