.. _arch:

Architecture
============

.. image:: _static/component.*
   :width: 100%
   :alt: Overview of the Inmanta platform

* The Inmanta **server**: This server manages the deployment process, it keeps track of all ongoing work.
  The server stores it state in PostgreSQL. All other state can be recovered after a server restart or failover.
* A **PostgreSQL database**: The Inmanta server stores its state in a PostgreSQL database.
* **Environment**: For multi-tenancy, one server can have multiple environments. Each environment performs its own deployments, without relation to other environments.
* The **compiler**: The compiler converts the source code into deployable resources and exports it to the server.
* CLI and **web-console**: To control the server, you can use either the web-console or the command line tools. Both communicate
  through the server rest API.
* The **scheduler**: The scheduler manages the deployment process for one specific environment.
* The **executors**: The executors execute configuration changes on targets. A target can be a server, a network device or an API
  or cloud service. The scheduler will create as many executors as it requires.
* **Smart Adaptors**: to be able to interface with target devices, the executors load smart adaptors, that allow the executor to communicate with the target device and enforce desired state on it



Resource deployment
-------------------

The scheduler deploys resources (through the executors and the smart adaptors) in 5 ways

1. Deployment of changes: when the intent (desired state) on the server changes, the scheduler will instruct the executors to update the infrastructure using the smart adapters.
2. Self-healing: when a resource has not been verified by the server for some time, it will verify the intent still holds. If it doesn't the intent is restored. This ensure that the managed infrastructure doesn't deteriorate over time.
3. Retry: when a deployment has previously failed, the scheduler will periodically retry all failed deploys.
4. User initiated deploy. The scheduler will immediately retry all previously failed resources.
5. User initiated repair. The scheduler will immediately perform self-healing on all resources.

Because of the intent based approach of the Inmanta orchestrator, the deployment code used in all 5 steps is the same.
Also onboarding of existing configuration is no different from a new deployment or self-healing: if we find that the system is already correctly configured, we leave it as is.

Additionally, we can perform *dryrun* on all intent, to determine what would change if we would deploy an intent. This also uses the same smart adaptor, but stops before actually enforcing the intent.

