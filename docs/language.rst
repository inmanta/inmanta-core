Language Reference
******************

The Inmanta language is a declarative language to model the configuration of an infrastructure.

The evaluation order of statements is determined by their dependencies on other statements and not based on the lexical order. i.e. The code is not necessarily executed top to bottom.


Modules
============================

The source is organized in modules. Each module is a git repository with the following structure::

    module/
    +-- files/
    +-- model/
    |  +-- _init.cf
    +-- plugins/
    +-- templates/
    +-- module.yaml

The ``module.yaml`` file, the ``model`` directory and the ``model/_init.cf`` are required.

For example::

    test/
    +-- files/
    +-- model/
    |  +-- _init.cf
    |  +-- services.cf
    |  +-- policy
    |  |  +-- _init.cf
    |  |  +-- other.cf
    +-- plugins/
    +-- templates/
    +-- module.yaml

The model code is in the ``.cf`` files. Each file forms a namespace. The namespaces for the files are the following.

+-----------------------------------------+----------------------------------+
| File                                    | Namespace                        |
+=========================================+==================================+
| test/model/_init.cf                     | test                             |
+-----------------------------------------+----------------------------------+
| test/model/services.cf                  | test::services                   |
+-----------------------------------------+----------------------------------+
| test/model/policy/_init.cf              | test::policy                     |
+-----------------------------------------+----------------------------------+
| test/model/policy/other.cf              | test::policy::other              |
+-----------------------------------------+----------------------------------+

Modules are only loaded when they are imported by a loaded module or the ``main.cf`` file of the project.

To access members from another namespace, it must be imported into the current namespace.::

    import test::services

Imports can also define an alias, to shorten long names::

    import test::services as services



Variables
==========

Variables can be defined in any lexical scope. They are visible in their defining scope and its children.
A lexical scope is either a namespaces or a code block (area between ``:`` and ``end``).

Variable names must start with a lower case character and can consist of the characters: ``a-zA-Z_0-9-``

A value can be assigned to a variable exactly once. The type of the variable is the type of the value.
Assigning a value to the same variable twice will produce a compiler error, unless the values are identical.

Variables from other modules can be referenced by prefixing them with the module name (or alias)::

    import redhat
    os = redhat::fedora23
    import ubuntu as ubnt
    os2 = ubnt::ubuntu1204


Literals values
==============================
Literal values can be assigned to variables::

    var1 = 1 # assign an integer, var1 contains now a number
    var2 = 3.14 # assign a float, var2 also contains a number
    var3 = "This is a string" # var3 contains a string

    # var 4 and 5 are both booleans
    var4 = true
    var5 = false

    # var6 is a list of values
    var6 = ["fedora", "ubuntu", "rhel"]

    # a dictionary with string keys and any type of values is also a primitive
    var7 = { "foo":"bar", "baz": 1}

    # var8 contains the same value as var2
    var8 = var2

    # next assignment will not return an error because var1 already contains this value
    var1 = 1

    # next assignment would return an error because var1 already has a different value
    #var1 = "test"

    #ref to a variable from another namespace
    import ip::services
    sshservice = ip::services::ssh



Primitive types
==============================

The basic primitive types are ``string``, ``number`` or ``bool``.

Constrained primitive types can be derived from the basic primitive type with a typedef statement.
Constrained primitive types add additional constraints to the basic primitive type with either a regex or a logical condition.
The name of the constrained primitive type must not collide with the name of a variable or type in the same lexical scope.

.. code-block:: antlr

    typedef : 'typedef' ID 'as' PRIMITIVE 'matching' condition|regex;

For example::

    typedef tcp_port as number matching self > 0 and self < 65565
    typedef mac_addr as string matching /([0-9a-fA-F]{2})(:[0-9a-fA-F]{2}){5}$/


Lists of primitive types are also primitive types: ``string[]``, ``number[]``, ``bool[]`` or ``mac_addr[]``

``dict`` is the primitive type that represents a dictionary


Conditions
==========================

Conditions can have the following forms

.. code-block:: antlr

    condition : '(' condition ')'
        | condition 'or' condition
        | condition 'and' condition
        | 'not' condition
        | value ('>' | '>=' | '<' | '<=' | '==' | '!=') value
        | value 'in' value
        | 'true'
        | 'false'
        | functioncall
        ;


Function calls
==========================

Each module can define plugins. Plugins can contribute functions to the module's namespace. The function call syntax is

.. code-block:: antlr

    functioncall : moduleref '.' ID '(' arglist? ')';
    arglist : value
            | arglist ',' value

For example::

    std::familyof(host.os, "rhel")
    a = param::one("region", "demo::forms::AWSForm")

Entities
========

Entities model configuration concepts. They are like classes in other object oriented languages: they can be instantiated and they define the structure of their instances.

Entity names must start with an upper case character and can consist of the characters: ``a-zA-Z_0-9-``

Entities can have a number of attributes and relations to other entities.
Entity attributes have primitive types, with an optional default value.

Entities can inherit from multiple other entities. Entities inherits attributes and relations from parent entities.
All entities inherit from ``std::Entity``.

It is not possible to override or rename attributes or relations. However, it is possible to
override defaults. Default values for attributes defined in the class take precedence over those in
the parent classes. When a class has multiple parents, the left parent takes precedence over the
others. A default value can be removed by setting its value to ``undef``.

The syntax for defining entities is:

.. code-block:: antlr

    entity: 'entity' ID ('extends' classlist)? ':' attribute* 'end';

    classlist: class
              | class ',' classlist;

    attribute: primitve_type ID ('=' literal)?;

Defining entities in a configuration model::

    entity File:
       string path
       string content
       number mode = 640
       string[] list = []
       dict things = {}
    end

Default values can also be set using a type alias::

    typedef PublicFile as File(mode = 0644)

A constructor call using a type alias will result in an instance of the base type.

Relations
=========

A Relation is a bi-direction relation between two entities. Consistency of the double binding is maintained by the compiler: assignment to one side of the relation is an implicit assignment of the reverse relation.

Relations are defined by specifying each end of the relation together with the multiplicity of each relation end. Each end of the relation is named and is maintained as a double binding by the compiler.

Defining relations between entities in the domain model::

    # Each config file belongs to one service.
    # Each service can have one or more config files
    File file [1:] -- [1] Service service

    cf = ConfigFile()
    service = Service()

    cf.service = service
    # implies service.configfile == cf

Relation multiplicities are enforced by the compiler. If they are violated a compilation error
is issued.

New Relation syntax
====================

A new relation syntex is available, to give a more natural object oriented feeling.

.. code-block:: antlr

   relation: class '.' ID multi '--' class '.' ID multi
           | class '.' ID multi annotation_list class '.' ID multi ;
   annotation_list: value
           | annotation_list ',' value

For example (as above)::

    File.service [1] -- Service.file [1:]


.. warning:: The names and multiplicities are on the other side in the old and new syntax!

In this new syntax, relations can also be unidirectional

.. code-block:: antlr

    uni_relation : class '.' ID multi '--' class
           | class '.' ID multi annotation_list class;


For example)::

    Service.file [1:] -- File



Instantiation
=============================================================


Instances of an entity are created with a constructor statement::

    File(path="/etc/motd")

A constructor can assign values to any of the properties (attributes or relations) of the entity. It can also leave the properties unassigned.
For attributes with default values, the constructor is the only place where the defaults can be overridden.

Values can be assigned to the remaining properties as if they are variables. To relations with a higher arity, multiple values can be assigned::

    Host host [1] -- [0:] File files

    h1 = Host("test")
    f1 = File(host=h1, path="/opt/1")
    f2 = File(host=h1, path="/opt/2")
    f3 = File(host=h1, path="/opt/3")

    // h1.files equals [f1, f2, f3]

    FileSet set [1] -- [0:] File files

    s1 = FileSet()
    s1.files = [f1,f2]
    s1.files = f3

    // s1.files equals [f1, f2, f3]

    s1.files = f3
    // adding a value twice does not affect the relation,
    // s1.files still equals [f1, f2, f3]

Refinements
===========

Entities define what should be deployed.
Entities can either be deployed directly (such as files and packages) or they can be refined.
Refinement expands an abstract entity into one or more more concrete entities.

For example, ``apache.Server`` is refined as follows::

    implementation apacheServerDEB for Server:
        pkg = std::Package(host=host, name="apache2-mpm-worker", state="installed")
        pkg2 = std::Package(host=host, name="apache2", state="installed")
        svc = std::Service(host=host, name="apache2", state="running", onboot=true, reload=true, requires=[pkg, pkg2])
        svc.requires = self.requires

        # put an empty index.html in the default documentroot so health checks do not fail
        index_html = std::ConfigFile(host=host, path="/var/www/html/index.html", content="",
                                 requires=pkg)
        self.user = "www-data"
        self.group = "www-data"
    end

    implement Server using apacheServerDEB when std::familyof(host.os, "ubuntu")

For each entity one or more refinements can be defined with the ``implementation`` statement.
Implementation are connected to entities using the ``implement`` statement.

When an instance of an entity is constructed, the runtime searches for refinements.
One or more refinements are selected based on the associated conditions. When no implementation is found, an exception is raised.
Entities for which no implementation is required are implemented using ``std::none``.

In the implementation block, the entity instance itself can be accessed through the variable self.

``implement`` statements are not inherited.


The syntax for implements and implementation is:

.. code-block:: antlr

    implementation: 'implementation' ID 'for' class ':' statement* 'end';
    implement: 'implement' class 'using' ID ('when' condition)?;



Indexes and queries
===================

Index definitions make sure that an entity is unique. An index definition defines a list of properties that uniquely identify an instance of an entity.
If a second instance is constructed with the same identifying properties, the first instance is returned instead.

All identifying properties must be set in the constructor.

Indices are inherited. i.e. all identifying properties of all parent types must be set in the constructor.

Defining an index::

    entity Host:
        string  name
    end

    index Host(name)

Explicit index lookup is performed with a query statement::

    testhost = Host[name="test"]


For loop
=========

To iterate over the items of a list, a for loop can be used::

    n_s = std::sequence(size, 1)
    for i in n_s:
        app_vm = Host(name="app{{i}}")
    end

The syntax is:

.. code-block:: antlr

    for: 'for' ID 'in' value ':' statement* 'end';



Transformations
==============================================================

At the lowest level of abstraction the configuration of an infrastructure often consists of
configuration files. To construct configuration files, templates and string interpolation can be used.


String interpolation
--------------------

String interpolation allows variables to be include as parameters inside a string.

The included variables are resolved in the lexical scope of the string they are included in.

Interpolating strings::

    hostname = "serv1.example.org"
    motd = """Welcome to {{hostname}}\n"""


Templates
---------

Inmanta integrates the Jinja2 template engine. A template is evaluated in the lexical
scope where the ``std::template`` function is called. This function accepts as an argument the
path of a template file. The first part of the path is the module that contains the template and the remainder of the path is the path within the template
directory of the module.

The integrated Jinja2 engine supports to the entire Jinja feature set, except for subtemplates. During execution Jinja2 has access to all variables and plug-ins that are
available in the scope where the template is evaluated. However, the ``::`` in paths needs to be replaced with a
``.``. The result of the template is returned by the template function.

Using a template to transform variables to a configuration file::

    hostname = "wwwserv1.example.com"
    admin = "joe@example.com"
    motd_content = std::template("motd/message.tmpl")

The template used in the previous listing::

    Welcome to {{ hostname }}
    This machine is maintainted by {{ admin }}


Plug-ins
===========

For more complex operations, python plugins can be used.
Plugins are exposed in the Inmanta language as function calls, such as the template function call. A template
accepts parameters and returns a value that it computed out of the variables.

Each module that is
included can also provide plug-ins. These plug-ins are accessible within the namespace of the
module.

To define a plugin, add a ``__init__.py`` file to the plugins directory.

In this file, plugins can be define according to the following template::

    from inmanta.plugins import plugin, Context
    from inmanta.execute.util import Unknown
    from inmanta.config import Config

    @plugin
    def example(ctx: Context, vm: "std::Host") -> "ip::ip":
        # get compiler config
        env = Config.get("config", "environment", None)

        # use exceptions
        if not env:
            raise Exception("The environment of this model should be configured in config>environment")

        # access compiler data via context
        scrapspace = ctx.get_data_dir()

        return "127.0.0.1"

Plugins have to be decorated with @plugin to work.

Arguments to the plugin have to be annotated with a type that is visible in the namespace of the module (or with ``any``).
An argument of the type ``inmanta.plugins.Context`` can be used to get access to the internal state of the compiler.

The ``inmanta.config.Config`` singleton can be used to get access to the configuration of the compiler.

Often, plugins are used to collect information from external systems, such as for example, the IP of virtual machine. When the virtual machine has not been created yet, the IP is not known yet. To indicate that situation (where information is not available yet), the type ``Unknown`` is used.
i.e. When the plugin is used to collect information from external systems, but this information is not available yet (but will be when the model deployment advances) then the plugin should return an instance of the type ``inmanta.execute.util.Unknown``.

Resources
============

Resources are entities that can be deployed directly, such as ``std::File`` or ``std::Package``.

Resource deployment has the following flow:
 1. a model is compiled
 2. all resources are identified and converted in serializeable form (``Resource`` object)
 3. all resources (and their associated python files) are uploaded to the server
 4. deploy is triggered
 5. resources are deployed to the agents that are responsible for this resource
 6. agents download the associated python code
 7. agents deserialize the resources
 8. agent execute the relevant handlers for the resources

To create new types of resource, two python objects are required: the ``Resource`` and the ``Handler``.

The resource convert a model object into a serializable form::

    @resource("std::File", agent="host.name", id_attribute="path")
    class File(Resource):
        """
            A file on a filesystem
        """
        fields = ("path", "owner", "hash", "group", "permissions", "purged", "reload")
        map = {"hash": store_file, "permissions": lambda y, x: int(x.mode)}


A resource is a subclass of ``inmanta.resources.Resource`` annotated with ``inmanta.resources.resource``. The annotation takes 3 parameters:
 * ``name``: the name of the entity to convert into a resource
 * ``agent``: the name of the agent that will deploy this resource. Often the name of the host on which the resource will be deployed.
 * ``id_attribute``: the attribute of the entity that uniquely distinguishes this instance from the others within its agent.

The class has two class fields:
 * ``fields``: the list of fields to be serialized and sent to the agent
 * ``map``: a dict, providing functions to generate values for fields that do not directly correspond to a property of the entity.


The handler is responsible for the actual deployment. For this, we refer to the examples available in the ``std`` module.
