.. _index:

.. only:: oss

    Inmanta Documentation
    *********************

    .. welcome

    Welcome to the Inmanta documentation!

    .. what

    Inmanta is an automation and orchestration tool to efficiently deploy and manage your software
    services, including all (inter)dependencies to other services and the underpinning infrastructure.
    It eliminates the complexity of managing large-scale, heterogeneous infrastructures and highly
    distributed systems.

    .. key characteristics

    The key characteristics of Inmanta are:

    * **Integrated**: Inmanta integrates configuration management and orchestration into a single tool, taking infrastructure as code to a whole new level.
    * **Powerful configuration model**: Infrastructure and application services are described using a high-level configuration model that allows the definition of (an unlimited amount of) your own entities and abstraction levels. It works from a single source, which can be tested, versioned, evolved and reused.
    * **Dependency management**: Inmanta's configuration model describes all the relations between and dependencies to other services, packages, underpinning platforms and infrastructure services. This enables efficient deployment as well as provides an holistic view on your applications, environments and infrastructure.
    * **End-to-end compliance**: The architecture of your software service drives the configuration, guaranteeing consistency across the entire stack and throughout distributed systems at any time. This compliance with the architecture can be achieved thanks to the integrated management approach and the configuration model using dependencies.

    The Inmanta project is mainly developed and maintained by `Inmanta <https://www.inmanta.com>`_.

.. only:: iso

    Inmanta Service Orchestrator Documentation
    ******************************************

    .. welcome

    Welcome to the Inmanta Service Orchestrator documentation!

    .. what

    Inmanta empowers telecom operators and service providers to speed up service delivery and reduce the total cost of ownership through efficient, end-to-end automation. No longer is automation limited to silos and vendor-specific solutions – you can now integrate with various domains and best-in-class components from any vendor.

    Inmanta Service Orchestrator is an automation and orchestration tool to efficiently deploy and manage your end-to-end services across physical and virtual domains and multi-vendor environments. Inmanta’s open and extensible micro-services architecture combined with powerful, intent-based service modelling provides the flexibility and efficiency to rapidly create, customize and roll-out new services, while eliminating costly operational errors.

    .. key characteristics

    The key characteristics of Inmanta Service Orchestrator are:

    * **End-to-end**: Inmanta Service Orchestrator ensures end-to-end consistency, higher flexibility and a shorter time to cash by enabling end-to-end automation of all service delivery aspects:

      * Multi-domain: designed to interact across physical and virtual domains, such as WAN, edge, access network, NFV, cloud, containers, and datacenter.
      * Holistic: A single, unifying automation solution, providing service orchestration, network orchestration, NFV orchestration (NFVO), as well as generic VNF management (gVNFM), cloud orchestration and configuration management. No other automation tools required.
      * Full lifecyle: Manage advanced service lifecycle, covering creation, on-boarding, provisioning, modification, scaling, upgrading and decommissioning.

    * **Intent-based programmability**: Inmanta optimizes service development and maintenance for telecom operators and service providers through its unifying, model-driven methodology for intent-based orchestration.

      * Inmanta's powerful domain-specific language (DSL) simplifies service creation and management, and is based on infrastructure as code (IaC) principles to provide a unified way to automate multi-domain and multi-vendor services. The embedded DSL enables the development of modular building blocks that make abstraction of low-level details, enabling re-usability across use cases.
      * Inmanta's intent-based programmability provides out-of-the-box self-healing, safe roll-back, detailed dry run and seamless service upgrades for enhanced stability and resilience.

    * **Vendor agnostic**: Inmanta Service Orchestrator is truly open and vendor agnostic for all network layers, domains and OSS/BSS. Service providers can integrate with 3rd party solutions as well as a wide range of open-source technologies to build a best-in-class, all-encompassing solution.

      * Interoperability through pluggable adapters and open APIs
      * API-ification of orchestrated services to easily plug services into the OSS/BSS environment
      * Support for brownfield environments by fine-grained roll-out

    The Inmanta Service Orchestrator product is based on mature technology backed by 15+ years of research and interaction with companies offering telecom and cloud services.


.. toctree::
    :maxdepth: 1

    quickstart
    install
    architecture
    language
    model_developers
    platform_developers
    lsm/index
    administrators
    faq
    glossary
    reference/index
    troubleshooting
    changelogs