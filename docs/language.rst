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

Variables from other modules can be referenced by prefixing them with the module name (or alias)


.. code-block:: inmanta

    import redhat
    os = redhat::fedora23
    import ubuntu as ubnt
    os2 = ubnt::ubuntu1204


Literals values
===============
Literal values can be assigned to variables

.. code-block:: inmanta

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

For example

.. code-block:: inmanta

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


Function calls / Plugins
========================

Each module can define plugins. Plugins can contribute functions to the module's namespace. The function call syntax is

.. code-block:: antlr

    functioncall : moduleref '.' ID '(' arglist? ')';
    arglist : value
            | arglist ',' value

For example

.. code-block:: inmanta

    std::familyof(host.os, "rhel")
    a = param::one("region", "demo::forms::AWSForm")

.. _lang-entity:

Entities
========

Entities model configuration concepts. They are like classes in other object oriented languages: they can be instantiated and they define the structure of their instances.

Entity names must start with an upper case character and can consist of the characters: ``a-zA-Z_0-9-``

Entities can have a number of attributes and relations to other entities. Entity attributes have primitive types, with an optional default value. An attribute has to have
a value unless the nulable variant of the primitive type is used. An attribute that can be null uses a primitive type with a ``?`` such as ``string?``. A value can also be assigned
only once to an attribute that can be null. To indicate that no value will be assigned, the literal ``null`` is available. ``null`` can also be the default value of an
attribute.

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

Defining entities in a configuration model

.. code-block:: inmanta

    entity File:
       string path
       string content
       number mode = 640
       string[] list = []
       dict things = {}
    end



.. _lang-relation:

Relations
=========

A Relation is a unidirectional or bidirectional relation between two entities. The consistency of a bidirectional double binding is maintained by the compiler: assignment to one side of the relation is an implicit assignment of the reverse relation.

Relations are defined by specifying each end of the relation together with the multiplicity of each relation end. Each end of the relation is named and is maintained as a double binding by the compiler.

Defining relations between entities in the domain model

.. code-block:: antlr

   relation: class '.' ID multi '--' class '.' ID multi
           | class '.' ID multi annotation_list class '.' ID multi ;
   annotation_list: value
           | annotation_list ',' value

For example a bidirectional relation:

.. code-block:: inmanta

    File.service [1] -- Service.file [1:]


Or a unidirectional relation

.. code-block:: antlr

    uni_relation : class '.' ID multi '--' class
           | class '.' ID multi annotation_list class;


For example

.. code-block:: inmanta

    Service.file [1:] -- File

Relation multiplicities are enforced by the compiler. If they are violated a compilation error
is issued.

.. note::

    In previous version another relation syntax was used that was less natural to read and allowed only bidirectional relations. The relation above was defined as ``File file [1:] -- [1] Service service``
    This synax is deprecated but still widely used in many modules.


.. _lang-instance:

Instantiation
=============

Instances of an entity are created with a constructor statement

.. code-block:: inmanta

    File(path="/etc/motd")

A constructor can assign values to any of the properties (attributes or relations) of the entity. It can also leave the properties unassigned.
For attributes with default values, the constructor is the only place where the defaults can be overridden.

Values can be assigned to the remaining properties as if they are variables. To relations with a higher arity, multiple values can be assigned

.. code-block:: inmanta

    Host.files [0:] -- File.host [1]

    h1 = Host("test")
    f1 = File(host=h1, path="/opt/1")
    f2 = File(host=h1, path="/opt/2")
    f3 = File(host=h1, path="/opt/3")

    // h1.files equals [f1, f2, f3]

    FileSet.files [0:] -- File.set [1]

    s1 = FileSet()
    s1.files = [f1,f2]
    s1.files = f3

    // s1.files equals [f1, f2, f3]

    s1.files = f3
    // adding a value twice does not affect the relation,
    // s1.files still equals [f1, f2, f3]

Refinements
===========

Entities define what should be deployed. Entities can either be deployed directly (such as files and packages) or they can be
refined. Refinement expands an abstract entity into one or more more concrete entities.

For example, :inmanta:entity:`apache::Server` is refined as follows

.. code-block:: inmanta

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

When an instance of an entity is constructed, the runtime searches for refinements. One or more refinements are selected based
on the associated conditions. When no implementation is found, an exception is raised. Entities for which no implementation is
required are implemented using :inmanta:entity:`std::none`.

In the implementation block, the entity instance itself can be accessed through the variable self.

``implement`` statements are not inherited, unless a statement of the form ``implement ServerX using parents`` is used.
When it is used, all implementations of the direct parents will be inherited, including the once with a where clause.


The syntax for implements and implementation is:

.. code-block:: antlr

    implementation: 'implementation' ID 'for' class ':' statement* 'end';
    implement: 'implement' class 'using' ID ('when' condition)?
    		 | 'implement' class 'using' 'parents';


Indexes and queries
===================

Index definitions make sure that an entity is unique. An index definition defines a list of properties that uniquely identify an instance of an entity.
If a second instance is constructed with the same identifying properties, the first instance is returned instead.

All identifying properties must be set in the constructor.

Indices are inherited. i.e. all identifying properties of all parent types must be set in the constructor.

Defining an index

.. code-block:: inmanta

    entity Host:
        string  name
    end

    index Host(name)

Explicit index lookup is performed with a query statement

.. code-block:: inmanta

    testhost = Host[name="test"]

For indices on relations (instead of attributes) an alternative syntax can be used

.. code-block:: inmanta

    entity File:
        string path
    end

    Host.files [0:] -- File.host [1]

    index File(host, path)

    a = File[host=vm1, path="/etc/passwd"]  # normal index lookup
    b = vm1.files[path="/etc/passwd"]  # selector style index lookup
    # a == b


For loop
=========

To iterate over the items of a list, a for loop can be used

.. code-block:: inmanta

    for i in std::sequence(size, 1):
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

Interpolating strings

.. code-block:: inmanta

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

Using a template to transform variables to a configuration file

.. code-block:: inmanta

    hostname = "wwwserv1.example.com"
    admin = "joe@example.com"
    motd_content = std::template("motd/message.tmpl")

The template used in the previous listing

.. code-block:: inmanta

    Welcome to {{ hostname }}
    This machine is maintainted by {{ admin }}


.. _lang-plugins:

Plug-ins
===========

For more complex operations, python plugins can be used. Plugins are exposed in the Inmanta language as function calls, such as the template function call. A template
accepts parameters and returns a value that it computed out of the variables. Each module that is included can also provide plug-ins. These plug-ins are accessible within the namespace of the
module. The :ref:`module-plugins` section of the module guid provides more details about how to write a plugin.
