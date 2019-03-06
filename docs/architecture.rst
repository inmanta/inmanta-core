Architecture
============

The Inmanta orchestrator consists of several components:

.. image:: _static/component.*
   :width: 90%
   :alt: Overview of the Inmanta platform

* The Inmanta **server**: This server manages the deployment process, it keeps track of all agents and the current state of all
  projects. The server stores it state in mongodb. All other state can be recovered after a server restart or failover.
* A mongodb database: The Inmanta server stores it state in a mongo database.
* The git server: The source code of the configuration models is stored in (one or more) git repositories.
* The **compiler**: The compiler converts the source code into deployable resources and exports it to the server.
* CLI and Dashboard: To control the server, you can use either the web dashboard or the command line tools. Both communicate
  through the server rest API.
* The Inmanta **agents**: Agents execute configuration changes on targets. A target can be a server, a network switch or an API
  or cloud service. An agent can manage local and remote resources. This provides the flexibility to work in an agent based or
  agent-less architecture, depending on the requirements.

  
Deployment
----------

Inmanta can be deployed/used in three variants:

* **embedded**: all components are started with the deploy command, the server is terminated after the deploy is finished. Suitable only for development.
* **push to server**: the server runs on a external machine. Models are compiled on the developer machine and pushed to the server directly. Suitable only for small setups or for developement/debug purposes.
* **autonomous server**: the server runs on a external machine. Models are stored in git repos and compiled by the server.

The last two variants support agents on the same machine as the server or deployed on the management targets.

Embedded
********

.. image:: _static/embedded.*
   :width: 90%
   :alt: Embedded deployment


In a embedded deployment, all components (server, agent and mongo) are started embedded in the compiler and terminated after
the deploy is complete. No specific setup is required. To deploy the current model, use::

   inmanta deploy


State related to orchestration is stored locally in data/deploy. This model is ideal of testing, development and one-off
deployments.


Push to server
**************

.. image:: _static/pushtoserver.*
   :width: 90%
   :alt: Embedded deployment

In a push to server model, the server is deployed on an external machine, but models are still compiled on the developer
machine. This gives faster feedback to developers, but makes the compilation less reproducible. It also complicates
collaboration.


Autonomous server
*****************

.. image:: _static/overview.*
   :width: 90%
   :alt: Embedded deployment

With an autonomous server, developers can no longer push models into production directly. Only the server itself compiles the
models. This ensures that every compile is repeatable and allows collaboration because all changes *have* to be committed.


Agentless
----------------------

The inmanta agent can work both locally and remote. 
A local agent is deployed on the system it manages. 
A server side agent runs on the inmanta server and is used for 'agentless' operation. 
Server side agent are started using :inmanta:entity:`AgentConfig`.


Deployment Modes
------------------

Inmanta supports two deployment modes: full and incremental.

**Full deployments** always deploy all resources, even if the resource have been deployed before. 
**Incremental deployments** only deploy resources of which the desired state has been modified since the last successful
deployment.  

Full deployments are used for self-healing. 
If some resource have unauthorized changes, a full deploy will bring them back in line.
Incremental deployments are used to bring changes to production quickly.

Both full and incremental deploys can be pushed by the server to the agents. 
Each agent can also be configured to periodically perform incremental and full deployments. 
Pushed deployments always take precedence on periodic deployments.  
    
