# Intended module structure to prevent import loops

* Status: proposed  <!-- optional | rejected | accepted | deprecated | ... | superseded by [ADR-0000](0000-logging-warnings-using-the-python-warnings-or-logging-module.md)] -->
* Deciders: [wouter, ] <!-- optional -->
* Date: 19/12/2024

Technical Story: https://github.com/inmanta/inmanta-core/pull/8466

## Context and Problem Statement

Our import have become quite tangled, where every import imports most of the rest of the code.
This is inefficient, it leads to import loops and it makes the code hard to reason about.



## Considered Options

1. General import rules 1
2. [option 2]
3. [option 3]
* ... <!-- numbers of options can vary -->

## Decision Outcome

Chosen option: "[option 1]", because [justification. e.g., only option, which meets k.o. criterion decision driver | which resolves force force | ... | comes out best (see below)].

### Positive Consequences <!-- optional -->

* [e.g., improvement of quality attribute satisfaction, follow-up decisions required, ...]
* ...

### Negative Consequences <!-- optional -->

* [e.g., compromising quality attribute, follow-up decisions required, ...]
* ...

## Pros and Cons of the Options <!-- optional -->

### General import rules 1

- a module should have a clear responsibility,
   - which should be documented
   - from that responsibility can be derived its knowledge about the world around it,
   - which in turn drives which other modules it "sees"
-  keep `__init__` light, as it is always imported when a submodule is imported.
- a package can offer an interface module (called now something like `model`/`types`/`__init__`).....
  - The interface module contains the external interface of the module for other module to consume
    - superclasses
    - exceptions
    - interface types (executor.executor e.g),
    - datatypes,...
  - The interface module should import the least stuff possible
    - It should never import any non-interface modules
- typing only imports can do what they want
- Packages should roughly form a tree,
  - where only composing modules import the non-interface modules of composed packages.
  - composing interface modules should also only import interface modules of composed modules


e.g. consider `inmanta.agent.executor.executor` and `inmanta.deploy` packages and the new_agent
- `inmanta.agent.executor.executor` is the interface package for the executor framework
- `inmanta.deploy` is the package containing the scheduler (it has no external interface package)
- `inmanta.deploy` imports `inmanta.agent.executor.executor`
- `inmanta.agent.agent_new` imports both the interface and concrete implementations of both executor and deploy (top level)
- `inmanta.deploy` doesn't import the non-interface parts of `inmanta.agent.executor.executor` because it never constructs executors (it is constructed with a reference to a executor manager, which serves as a factory)
- `inmanta.agent.executor.executor` doesn't know about deploy at all


* Good, because it offers guidance
* Good, because reduces loops
* Bad, because not super exact

### [option 2]

[example | description | pointer to more information | ...] <!-- optional -->

* Good, because [argument a]
* Good, because [argument b]
* Bad, because [argument c]
* ... <!-- numbers of pros and cons can vary -->

### [option 3]

[example | description | pointer to more information | ...] <!-- optional -->

* Good, because [argument a]
* Good, because [argument b]
* Bad, because [argument c]
* ... <!-- numbers of pros and cons can vary -->

## Links <!-- optional -->

* [Link type] [Link to ADR] <!-- example: Refined by [ADR-0000](0000-logging-warnings-using-the-python-warnings-or-logging-module.md) -->
* ... <!-- numbers of links can vary -->
