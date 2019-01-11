Inmanta Deployment Semantics
===============================

This document formalized the exact semantics of inmanta deployment.

Desired State
--------------
The goal of an inmanta deployment is to bring the target system into a specific state and keep it there.
This desired state is expressed by an inmanta model, that is compiled into a set of resources.

version


The deployment process realizes the desired state by taking the following steps for each resource:

1- reading out the current state of the resource in the target system
2- comparing the current state with the desired state
3- deciding on an action to take (do nothing, create, update, delete)
4- performing this action


To ensure proper ordering of execution, resources can `require` other resources.
*Inmanta guarantees that no resource will be altered unless the resources it requires have been confirmed to be in their desired state*


Agents
------

Resources
---------


Dryrun
------




Normal Deploy
-------------



Incremental Deploy
------------------



