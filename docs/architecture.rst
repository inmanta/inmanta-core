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

  
Usage modes
-----------

Inmanta can be used in three modes:

* **embedded**: all components are started with the `deploy` command, the server is terminated after the deploy is finished. Suitable only for development.
* **push to server**: the server runs on a external machine. Models are compiled on the developer machine and pushed to the server directly. Suitable only for small setups or for developement/debug purposes.
* **autonomous server**: the server runs on a external machine. Models are stored in git repos and compiled by the server.

The last two modes support agents on same machine as the server and automatically started, or deployed as an external
process.

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


Agent modes
-----------

The Inmanta agent performs all changes in the infrastructure. Either the orchestration server starts an agents or
an agent is deployed as a separate process.

 * **agentless**: Autostarted agents allow for an agentless mode: no explicit agents need to be started. When the agent needs to make changes on machine/vm it can make the changes over remote over ssh. Autostarted agents are controlled by using :inmanta:entity:`std::AgentConfig`. :inmanta:entity:`ip::Host` and subclasses can automatically configure an agent with the `remote_agent` attribute.
 * **external agent**: External agent processes need explicit configuration to connect to the orchestration server. The aws and openstack modules use the platform module to generate a user_data bootscript for virtual machines to install an agent and connect to the orchestration server. The `install_agent` boolean controls this option.


Resource deployment
-------------------

The agent is responsible for:

 * repair the infrastructure at regular intervals
 * change the infrastructure at regular intervals
 * enforce desired state when the server requests it

Repair
******
At regular intervals the agent verifies that the current state of all resources it manages matches the desired state provided by the orchestration server. For a repair the agent verifies all resources, even if the last known current state already matches the desired state. In the current release all deploys are done through a repair and run by default every 600 seconds. This is controlled with :inmanta.config:option:`config.agent-repair-interval`, when this option is set to 0 no repairs are performed.

Deploy changes
**************
For very large infrastructures or infrastructure that is too slow (for example network devices with underpowered control planes or thousands of managed resources) a repair cannot run often. For example, only once a  week. When this is the case, the agent can deploy only known changes (based on the previous deployed state cached by the orchestration server). This interval is controlled by :inmanta.config:option:`config.agent-deploy-interval`. This interval should be a lot shorter than :inmanta.config:option:`config.agent-repair-interval`

When a repair is running and a deploy run is started, the repair is cancelled, the deploy is performed and then the repair is restarted. This repair starts again from scratch. So when repairs take a very long time, they might never finish completely when there is a high rate of change.

Push changes
************
For very interactive changes the server pushes changes to the agent. The server can push full and incremental desired state to the agent.

 * **incremental** only deploys resource for which the orchestrator knows there are changes, based on the last known deploy status of the resource.
 * **full** always deploys all resources even if the last know status of the resource already matches desired state.

    
