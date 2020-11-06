Model Design Guidelines
=======================

This section provides design guidelines for experienced developers. 
It is intended as a way of sharing experience and improving design. 

.. warning::

    We provide guidelines here. These are not absolute rules and not all rules are appropriate at all times.
    Trust your own good judgement before anything else. 

Overview
--------

South Bound Integration:

#. Keep close to the API. Keep the structure of the inmanta model as close as possible to the API you model. Refrain from adding abstraction layers when doing pure integration.
#. Prefer modeling relations as relations, avoid reference by string.

Keep close to the API
---------------------

When doing south bound integrations, it is tempting to *improve* the existing API.
Resist this temptation. It leads to the following problems:

#. It costs a lot of effort to integrate the API and redesign it at the same time. 

#. Often, you don't understand the API as well as the people who designed it. The improvements you make when starting
   out often lead to dead ends. Some features that are trivial to represent in the original API become impossible to
   express in your improved API. 

#. APIs evolve. When the API changes in the future, it may become very hard to maintain you improved API.

When you want to offer an improved API, do it in two stages: first model and integrate the existing API, 
then add an abstraction layer in the model. This neatly separates the integration and abstraction effort. 

Prefer modeling relations as relations
--------------------------------------

Often, APIs have relations. For example, when creating a virtual machine on AWS EC2, it can refer to one or more SecurityGroups.
This is modeled in the AWS handler as an explicit relation: :inmanta:relation:`aws::VirtualMachine.security_groups`. 

There are different modeling styles possible:
1. Model the relation as a relation between two model entities. (e.g. :inmanta:relation:`aws::VirtualMachine.security_groups`)
2. Model the relation as a (textual) reference. (e.g. :inmanta:relation:`aws::database::RDS.subnet_group`.)

These styles can be mixed within one module.

Explicit relations have the advantage that consistency can be enforced within the model. 
Type errors and dangling reference are easily prevented. 
Higher functionality, like correct ordering of the deployment is easy to implement.

Textual references have the advantage that it is easy to refer to things that are not in the model. 

When starting to build up a model, textual reference are attractive, as the modeling effort required is very limited. 
It is however difficult to migrate away from the textual references later on, because this is a breaking change for any existing model.

One solution to allow reference to unmanaged entities is to extend :inmanta:entity:`std::ManagedResource`. 
This allows an entity to exist in the model, but when ``managed`` is set to ``false``, it will never become a resource. 
However, the entity must still be valid. All attributes and relations still have to be filled in correctly.
For entities with many non-optional relations, this is also not the best solution. 

Another solution is to introduce a parent entity type that explicitly represents the unmanaged entity. 
It has only those attributes that are required to correctly refer to it.
The concrete, managed entity is a subtype of the unmanaged version. 
This requires a bit more types, but it is most evolution friendly. 
No naming convention for the unmanaged parent has been established. 

As an example, we could implement :inmanta:relation:`aws::VirtualMachine.security_groups` as follows:

.. image:: /_static/relation_pattern_simple.*
   :width: 90%
   :alt: Simple example of the relation pattern

In cases where there is a single relation that can point to multiple specific subtypes, 
we can use the existing supertype entity to represent unmanaged entities.

.. image:: /_static/relation_pattern_inherited.*
   :width: 90%
   :alt: Example of the relation pattern with inherited