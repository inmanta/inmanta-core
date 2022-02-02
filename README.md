# Inmanta
[![pypi version](https://img.shields.io/pypi/v/inmanta.svg)](https://pypi.python.org/pypi/inmanta-core/)


Inmanta is an automation and orchestration tool to efficiently deploy and manage your software
services, including all (inter)dependencies to other services and the underpinning infrastructure.
It eliminates the complexity of managing large-scale, heterogeneous infrastructures and highly
distributed systems.

The key characteristics of Inmanta are:
 * Integrated: Inmanta integrates configuration management and orchestration into a single tool,
   taking infrastructure as code to a whole new level.
 * Powerful configuration model: Infrastructure and application services are described using a
   high-level configuration model that allows the definition of (an unlimited amount of) your own
   entities and abstraction levels. It works from a single source, which can be tested, versioned,
   evolved and reused.
 * Dependency management: Inmanta's configuration model describes all the relations between and
   dependencies to other services, packages, underpinning platforms and infrastructure services.
   This enables efficient deployment as well as provides an holistic view on your applications,
   environments and infrastructure.
 * End-to-end compliance: The architecture of your software service drives the configuration,
   guaranteeing consistency across the entire stack and throughout distributed systems at any time.
   This compliance with the architecture can be achieved thanks to the integrated management
   approach and the configuration model using dependencies.

Currently, the Inmanta project is mainly developed and maintained by Inmanta NV.

## Links

* [Documentation](https://docs.inmanta.com/community/latest/)
* [Quickstart](https://github.com/inmanta/quickstart-docker)

## Install

* [Install Guide](https://docs.inmanta.com/community/latest/install.html)

## Running the tests using tox

```
$ python3 -m venv env
$ source env/bin/activate
$ pip install -U pip tox
$ tox
```

Additional pytest arguments can be passed to tox via the `INMANTA_EXTRA_PYTEST_ARGS` environment variable.
In order to run the test suite in fast mode, set `INMANTA_EXTRA_PYTEST_ARGS='--fast'`.
