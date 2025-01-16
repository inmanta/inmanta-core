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
        Each environment represents a target infrastructure that inmanta manages. At least one
        environment is required, but often multiple environments of the same infrastructure are
        available such as development, integration and testing.

    resource scheduler
        In each environment, this component manages the deployment of resources. It keeps track of
        resources' state and intent, schedules them for deploy / repair when appropriate, and maintains
        resource order as defined by the requires-provides relations.

        It groups the resources by their announced :term:`agent<agent>`, spawns :term:`executor<executor>` processes to
        host the handler code for each of those agents, and it works through its scheduled deploys (and other resource
        actions, e.g. dry-run) by directing those executors to execute appropriate handler operations.

    executor
        A process spawned on-demand by the :term:`resource scheduler<resource scheduler>` that hosts handler code.
        The resource scheduler instructs the executor to execute deploys (and other resource actions, e.g. dry-run).

    agent
        The logical component, identified by a name, that knows how to deploy a class of resources. The
        :term:`resource scheduler<resource scheduler>` ensures that deploy actions on a given agent are always
        sequential. It is a grouping (and concurrency control) mechanism for related resources (i.e. resources
        that go to a single device or API endpoint). Each logical agent has its own :term:`executor<executor>`
        process(es) on which to run handler code.

    resource
        Inmanta orchestrates and manages resources, of any abstraction level, in an infrastructure.
        Examples of resources are: files and packages on a server, a virtual machine on a
        hypervisor, a managed database as a PaaS provider, a switch port on a switch, ...

        A resource has attributes that express the desired value of a property of the resource it
        represents in the infrastructure. For example the
        :inmanta:attribute:`memory_mb<vcenter::VirtualMachine.memory_mb>` attribute of the :inmanta:entity:`vcenter::VirtualMachine`
        resource. This attribute indicates the memory size of a virtual machine.

        A resource needs to have a unique identifier in an environment. This identifier needs to be
        derived from attributes of the resource. This ensures that the orchestrator can (co-)manage
        existing resources and allows quick recovery of the orchestrator in failure conditions. This
        unique identifier consists of multiple fields. For example,
        ``vcenter::VirtualMachineFromTemplate[lab,name=srv_test]`` This id contains the type of the resource, the name of
        the :term:`agent` and the unique id with its value for this resource. The resource designer
        determines how this id is derived.

        The fields in the id are:

        * The first field is the type of the resource. For example: ``vcenter::VirtualMachineFromTemplate``
        * The second field is the name of the agent that manages/groups the resource. For example:
          the name of the vcenter cluster on which the virtual machine is defined ``lab``
        * The third field is the identifying attribute and the value of this attribute. For example:
          the ``name`` of the virtual machine uniquely identifies a virtual machine on a vcenter cluster.

    module
        A :term:`configuration model` consists of multiple configuration modules. A module provides
        a partial and reusable configuration model and its related resources such as files,
        templates, ... The :doc:`module developer guide <model_developers/modules>` provides more details.

    resource handler
        See :term:`handler`

    handler
        A handler provides the interface between a resource in the model and the resource in the
        infrastructure. The executor loads the handler and uses it to discover
        :term:`facts` and make changes to the real resource.

    desired state
        The desired state expresses the state of all resources that Inmanta manages. Expressing a
        configuration in function of desired state makes the orchestrator more robust to failures
        compared to imperative based orchestration. The :term:`resource scheduler` reads the
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

        For more context, see
        :ref:`how unknowns propagate through the configuration model <language_unknowns>` and
        :ref:`how the exporter deals with them <model_export_format>`.

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
        server. More information in the :ref:`using facts<Using facts>` section.

    infrastructure
        This is what Inmanta manages. This could be virtual machines with resources in these virtual
        machines. Physical servers and their os. Containers or resources at a cloud provider without
        any servers (e.g. "serverless")

    infrastructure-as-code
        Wikepedia defines "Infrastructure as code" as *the process of managing and provisioning
        computer data centers through machine-readable definition files, rather than physical
        hardware configuration or interactive configuration tools.* Inmanta achieves this by using a
        desired state configuration model that is entirely expressed in code.

    expert feature
        A feature that is stable, but requires great care and/or knowledge to use properly.
