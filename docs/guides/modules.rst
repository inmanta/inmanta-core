Module Developers Guide
========================
In inmanta all configuration model code and related files, templates, plugins and resource handlers
are packaged in a module.


Module layout
-------------
Inmanta expects that each module is a git repository with a specific layout:

* The name of the module is determined by the top-level directory. Within this module directory, a
  ``module.yml`` file has to be specified.
* The only mandatory subdirectory is the ``model`` directory containing a file called ``_init.cf``.
  What is defined in the ``_init.cf`` file is available in the namespace linked with the name of the
  module. Other files in the model directory create subnamespaces.
* The ``plugins`` directory contains Python files that are loaded by the platform and can extend it
  using the Inmanta API.  This python code can provide plugins or resource handlers.

The template, file and source plugins from the std module expect the following directories as well:

* The ``files`` directory contains files that are deployed verbatim to managed machines.
* The ``templates`` directory contains templates that use parameters from the configuration model to
  generate configuration files.

A complete module might contain the following files:

.. code-block:: sh

    module
    |
    |__ module.yml
    |
    |__ files
    |    |__ file1.txt
    |
    |__ model
    |    |__ _init.cf
    |    |__ services.cf
    |
    |__ plugins
    |    |__ functions.py
    |
    |__ templates
         |__ conf_file.conf.tmpl


Module metadata
---------------
The module.yml file provides metadata about the module. This file is a yaml file with the following
three keys mandatory:

* *name*: The name of the module. This name should also match the name of the module directory.
* *license*: The license under which the module is distributed.
* *version*: The version of this module. For a new module a start version could be 0.1dev0 These
  versions are parsed using the same version parser as python setuptools.

For example the following module.yaml from the :doc:`../quickstart`

.. code-block:: yaml

    name: lamp
    license: Apache 2.0
    version: 0.1

Module depdencies are indicated by importing a module in a model file. However, these import do not
have a specifc version identifier. The version of a module import can be constrained in the
module.yml file. The *requires* key excepts a list of version specs. These version specs use `PEP440
syntax <https://www.python.org/dev/peps/pep-0440/#version-specifiers>`_.

To specify specific version are required, constraints can be added to the requires list::

    license: Apache 2.0
    name: ip
    source: git@github.com:inmanta/ip
    version: 0.1.15
    requires:
        net: net ~= 0.2.4
        std: std >1.0 <2.5

A module can also indicate a minimal compiler version with the *compiler_version* key.

*source* indicates the authoritative repository where the module is maintained.


Versioning
----------
Inmanta modules should be versioned. The current version is reflected in the module.yml file and in
the commit is should be tagged in the git repository as well. To ease the use inmanta provides a
command (inmanta modules commit) to modify module versions, commit to git and place the correct tag.

To make changes to a module, first create a new git branch::

    git checkout -b mywork

When done, first use git to add files::

    git add *

To commit, use the module tool. It will autmatically set the right tags on the module::

    inmanta moduletool commit -m "First commit"

This will create a new dev release. To make an actual release::

    inmanta moduletool commit -r -m "First Release"

To set a specific version::

    inmanta moduletool commit -r -m "First Release" -v 1.0.1

The module tool also support semantic versioning instead of setting versions directly. Use one
of ``--major``, ``--minor`` or ``--patch`` to update version numbers: <major>.<minor>.<patch>



Extending Inmanta
-----------------
Inmanta offers module developers an orchestration platform with many extension possibilities. When
modelling with existing modules is not sufficient, a module developer can use the Python SDK of
Inmanta to extend the platform. Python code that extends Inmanta is stored in the plugins directory
of a module. All python modules in the plugins subdirectory will be loaded by the compiler when at
least a ``__init__.py`` file exists, exactly like any other python package.

.. note::
    It is not possible to import python modules from other Inmanta modules.


The Inmanta Python SDK offerts several extension mechanism:

* Plugins
* Resources
* Resource handlers
* Dependency managers

Only the compiler and agents load code included in modules (See :doc:`/architecture`). A module can
include a requirements.txt file with all external dependencies. Both the compiler and the agent will
install this dependencies with ``pip install`` in an virtual environment dedicated to the compiler
or agent. By default this is in `.env` of the project for the compiler and in
`/var/lib/inmanta/agent/env` for the agent.

Inmanta uses a special format of requirements that was defined in a python PEP but never fully
implemented in all python tools (setuptools and pip). Inmanta rewrites this to the syntax pip
requires. This format allows module developers to specify a python dependency in a repo on a
dedicated branch. And it allows inmanta to resolve the requirements of all module to a
single set of requirements, because the name of module is unambiguously defined in the requirement.
The format for requires in requirements.txt is the folllowing:

 * Either, the name of the module and an optional constraint
 * Or a repository location such as  git+https://github.com/project/python-foo The correct syntax
   to use is then: eggname@git+https://../repository#branch with branch being optional.

.. _module-plugins:

Plugins
*******
Plugins provide :ref:`functions<lang-plugins>` that can be called from the :term:`DSL`. This is the
primary mechanism to interface Python code with the configuration model at compile time. This
mechanism is also used std::template or std::file. Inmanta also registers all plugins with the
template engine (Jinja2) to use as filter.

A plugin is a python function, registered with the platform with the :func:`~inmanta.plugins.plugin`
decorator. This plugin accepts arguments from the DSL and can return a value. Both the arguments and
the return value must by annotated with the allowed types from the configuration model. Type
annotations are provided as a string (Python3 style argument annotation). ``any`` is the special
type that effectively disables type validation.

Through the arguments of the function, the Python code in the plugin can navigate the configuration
model. The compiler takes care of scheduling the execution at the correct point in the model
evaluation.

A simple plugin that accepts no arguments, prints out "hello world" and returns no value requires
the following code:

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin

    @plugin
    def hello():
        print("Hello world!")


If the code above is placed in the plugins directory of the example module
(``examples/plugins/__init__.py``) the plugin can be invoked from the configuration model as
follows:

.. code-block:: none

    import example

    example::hello()


The plugin decorator accepts an argument name. This can be used to change the name of the plugin in
the DSL. This can be used to create plugins that use python reserved names such as ``print``.

A more complex plugin accepts arguments and returns a value. The following example creates a plugin
that converts a string to uppercase:

.. code-block:: python
    :linenos:

    from inmanta.plugins import plugin

    @plugin
    def upper(value: "string") -> "string":
        return value.upper()


This plugin can be tested with:

.. code-block:: none

    import example

    std::print(example::upper("hello world"))


Argument type annotations are strings that refer to Inmanta primitive types or to entities. If an
entity is passed to a plugin, the python code of the plugin can navigate relations throughout the
configuration model to access attributes of other entities.

If your plugin requires external libraries, include a requirements.txt in the module. The libraries
listed in this file are automatically installed by the compiler and agents.

..todo:: context
..todo:: new statements

Resources and handlers
**********************

A module can add additional :term:`resources<resource>` and/or handlers for resources to Inmanta. A
resource defines a type that resembles an :term:`entity` but without any relations. This is required
for the serializing resources for communication between the compiler, server and agents.

Resource
^^^^^^^^
A resource is represented by a Python class that is registered with Inmanta using the
:func:`~inmanta.resources.resource` decorator. This decorator decorates a class that inherits from
the :class:`~inmanta.resources.Resource` class.

The fields of the resource are indicated with a ``fields`` field in the class. This field is a tuple
or list of strings with the name of the desired fields of the resource. The orchestrator uses these
fields to determine which attributes of the matching entity need to be included in the resource.

Fields of a resource cannot refer to instance in the configuration model or fields of other
resources. The resource serializers allows to map field values. Instead of referring directly to an
attribute of the entity is serializes (path in std::File and path in the resource map one on one).
This mapping is done by adding a static method to the resource class with ``get_$(field_name)`` as
name. This static method has two arguments: a reference to the exporter and the instance of the
entity it is serializing.


.. code-block:: python
    :linenos:

    from inmanta.resources import resource, Resource

    @resource("std::File", agent="host.name", id_attribute="path")
    class File(Resource):
        fields = ("path", "owner", "hash", "group", "permissions", "purged", "reload")

        @staticmethod
        def get_hash(exporter, obj):
            hash_id = md5sum(obj.content)
            exporter.upload_file(hash_id, obj.content)
            return hash_id

        @staticmethod
        def get_permissions(_, obj):
            return int(x.mode)


Classes decorated with :func:`~inmanta.resources.resource` do not have to inherit directly from
Resource. The orchestrator already offers two additional base classes with fields and mappings
defined: :class:`~inmanta.resources.PurgeableResource` and
:class:`~inmanta.resources.ManagedResource`. This mechanism is useful for resources that have fields
in common.

A resource can also indicate that it has to be ignored by raising the
:class:`~inmanta.resources.IgnoreResourceException` exception.

Handler
^^^^^^^
Handlers interface the orchestrator with resources in the :term:`infrastructure` in the agents.
Handlers take care of changing the current state of a resource to the desired state expressed in the
configuration model.

The compiler collects all python modules from Inmanta modules that provide handlers and uploads them
to the server. When a new configuration module version is deployed, the handler code is pushed to all
agents and imported there.

Handlers should inherit the class :class:`~inmanta.agent.handler.ResourceHandler`. The
:func:`~inmanta.agent.handler.provider` decorator register the class with the orchestrator. When the
agent needs a handler for a resource it will load all handler classes registered for that resource
and call the :func:`~inmanta.agent.handler.ResourceHandler.available`. This method should check
if all conditions are fulfilled to use this handler. The agent will select a handler, only when a
single handler is available, so the is_available method of all handlers of a resource need to be
mutually exclusive. If no handler is available, the resource will be marked unavailable.

:class:`~inmanta.agent.handler.ResourceHandler` is the handler base class.
:class:`~inmanta.agent.handler.CRUDHandler` provides a more recent base class that is better suited
for resources that are manipulated with Create, Delete or Update operations. This operations often
match managed APIs very well. The CRUDHandler is recommended for new handlers unless the resource
has special resource states that do not match CRUD operations.

Each handler basically needs to support two things: reading the current state and changing the state
of the resource to the desired state in the configuration model. Reading the state is used for dry
runs and reporting. The CRUDHandler handler also uses the result to determine whether create, delete
or update needs to be invoked.

The context (See :class:`~inmanta.agent.handler.HandlerContext`) passed to most methods is used to
report results, changes and logs to the handler and the server.
