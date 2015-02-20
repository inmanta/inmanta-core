Language reference
******************

This chapter is a reference for the Impera DSL. The Impera language is a declarative
language to model the configuration of an infrastructure. The evaluation order of statements in the
Impera modeling language is determined by their dependencies on other statements and not based on
the lexical order. The correct evaluation order is determined by the language runtime.


Literal values and variables
============================

This section first introduces the basics of the DSL: literal values. The values can be of the type
``string``, ``number`` or ``bool``. Impera also provides lists of values. When a value is assigned to a
variable, this variable becomes read-only. Because variables can only be assigned once, it is not
necessary to declare the type of the variable. The runtime is dynamically typed.

Assigning literal values to variables::

    var1 = 1 # assign an integer, var1 contains now a number
    var2 = 3.14 # assign a float, var2 also contains a number
    var3 = "This is a string" # var3 contains a string

    # var 4 and 5 are both booleans
    var4 = true
    var5 = false

    # var6 is a list of values
    var6 = ["fedora", "ubuntu", "rhel"]

    # var 7 is a label for the same value as var 2
    var7 = var2

    # next assignment will return an error because var1 is read-only after it was
    # assigned the value 1
    var1 = "test"


Constraining literal types
==========================

Literal values are often values of configuration parameters that end up directly in configuration
files or after transformations such as templates. These parameters often have particular formats or
only a small range of valid values. Examples of such values are tcp port numbers or a MAC address of
an Ethernet interface.

A typedef statement creates a new literal type which is based on one of the basic types with an
additional constraint. A typedef statement starts with the ``typedef`` keyword, followed by a
name that identifies the type. This name should start with a lowercase character and is followed by
uppercase and lowercase characters, numbers, a dash and an underscore. After name an expression
follows which is started by the ``matching`` keyword. The expression is either an Impera
expression or a regular expression. A regular expression is demarcated with slashes.

Impera expressions can use logical operators such as greater than, smaller than, equality and
inclusions together with logical operators. The keyword ``self`` refers to the value that is
assigned to a variable of the constrained type.

Constraining types as validation constraints::

    typedef tcp_port as number matching self > 0 and self < 65565
    typedef mac_addr as string matching /([0-9a-fA-F]{2})(:[0-9a-fA-F]{2}){5}$/


Transformations: string interpolation, templates and plug-ins
=============================================================

At the lowest level of abstraction the configuration of an infrastructure often consists of
configuration files or attributes that are set to certain values. These configuration files and
attribute values are a transformation of one or more parameters that are available in the
configuration model. In Impera there are three mechanism available to perform such transformation:
string interpolation, templates and plugins. In the next subsection each of these mechanisms are
explained.

String interpolation
--------------------

The easiest transformation but also the least powerful is string interpolation. It enables the
developer to include variables as parameters inside a string. The included variables are dynamically
looked up at the location where the string they are included in is instantiated. This is important
to note for later in this chapter when the language constructs are introduced that provide
encapsulation.

Interpolating strings::

    hostname = "wwwserv1.example.org"
    motd = """Welcome to {{{hostname }}}\n"""


Templates
---------

Impera has a built-in template engine that has been tightly integrated into the platform. Impera
integrated the Jinja2 template engine. A template is evaluated in the location and
scope where the \keyword{template} function is called. This function accepts as an argument the
location of the template. A template is identified with a path: the first item of the path is
the module that contains the template and the remainder of the path is the path within the template
directory of the module.

The integrated Jinja2 engine is limited to the entire Jinja feature set, except for subtemplates
which are not supported. During execution Jinja2 has access to all variables and plug-ins that are
available in the scope where the template is evaluated. Fully qualified names in the Impera model use
``::`` as a path separator. This syntax is reserved in Jinja2, so ``::`` needs to be replaced with a
``.``. The result of the template is returned by the template function.

Using a template to transform variables to a configuration file::

    hostname = "wwwserv1.example.com"
    admin = "joe@example.com"
    motd_content = template("motd/message.tmpl")

The template used in the previous listing::

    Welcome to {{ hostname }}
    This machine is maintainted by {{ admin }}


Transformation plug-ins
-----------------------

Transformation plug-ins provide an interface to define a transformation in Python. Plugins are
exposed in the Impera language as function calls, such as the template function call. A template
accepts parameters and returns a value that it computed out of the variables.

Impera has a list of built-in plug-ins that are accessible without a namespace. Each module that is
included can also provide plug-ins. These plug-ins are accessible within the namespace of the
module. Each of the Impera native plug-ins and the plug-ins provided by modules are also registered as
filters in the Jinja2 template engine. Additionally plug-ins can also be called from within
expressions such as those used for constraining literal types. The validation expression will in
that case be reduced to a transformation of the value that needs to be validated to a boolean value.


Entities
========

The types that a system administrator uses to model concepts from the configuration are entities.
Entities are defined with the keyword ``entity`` followed by a name that starts with an
uppercase character. The other characters of the name may contains upper and lower case characters,
numbers, a dash and an underscore. With a colon the body of the definition of an entity is started.
In this body the attributes of the entity are defined. The body ends with the keyword ``end``.

Entity attributes are used to add properties to an entity that are represented by literal values.
Properties of entities that represent a relation to an instance of an entity should be represented
using relations which are explained further on. On each line of the body of an entity definition a
literal attribute can be defined. The definition consists of the literal type, which is either
``string``, ``number`` or ``bool`` and the name of the attribute. Optionally a default value can be added.

Entities can inherit from multiple other entities, thus multiple inheritance. Inheritance implies
that an entity inherits attributes and relations from parent entities. Inheritance also introduces a
is-a relationship. It is however not possible to override or rename attributes. Entities that do
not explicitly inherit from an other entity inherit from ``{std::Entity``.

Instances of an entity are created with a constructor statement. A constructor statement consists
of the name of the entity followed by parenthesis. Optionally between these parenthesis attributes
can be set. Attributes can also be set in separate statements. Once an attribute is set, it becomes
read-only.

In a configuration often default values for parameters are used because only in specific case an
other values is required. Attributes are read-only once they are set, so in the definition of an
entity default values for attributes can be provided. In the cases where multiple default values are
used a default constructor can be defined using the ``typedef`` keyword, followed by the name
of the constructor and the keyword ``as``, again followed by the constructor with the default
values set. Both mechanisms have the same semantics. The default value is used for an attribute when
an instance of an entity is created and no value is provided in the constructor for the attributes
with default values.

Defining entities in a configuration model::

    entity File:
       string path
       string content
       number mode = 640
    end

    motd_file = File(path = "/etc/motd")
    motd_file.content = "Hello world\n"

    entity ConfigFile extends File:

    end

    typedef PublicFile as File(mode = 0644)


Relations
=========

IMP makes from the relations between entities a first class language construct. Literal value
properties are modeled as attributes, properties that have an other entity as type are modeled as a
relation between those entities. Relations are defined by specifying each end of the relation
together with the multiplicity of each relation end. Each end of the relation is named and is
maintained as a double binding by the Impera runtime.

Defining relations between entities in the domain model::

    # Each config file belongs to one service.
    # Each service can have one or more config files
    ConfigFile configfile [1:] -- [1] Service service

    cf = ConfigFile()
    service = Service()

    cf.service = service

The listing above shows the definition of a relation. Relations do not start with a
specific keyword such as most other statements. Each side of a relation is defined an each side of
the ``--`` keyword. Each side is the definition of the property of the entity on the other
side. Such a definition consists of the name of the entity, the name of the property and a
multiplicity which is listed between square brackets. This multiplicity is either a single integer
value or a range which is separated by a colon. If the upper bound is infinite the value is left
out. Relation multiplicities are enforced by the runtime. If they are violated a compilation error
is issued.

Relations also add properties to entities. Relation can be set in the constructor or using a
specific set statement. Properties of a relations with a multiplicity higher than one, can hold
multiple values. These properties are implemented as a list. When a value is assigned to a property
that is a list, this value is added to the list. When this value is also a list the items in the
list are added to the property. This behavior is caused by the fact that variables and properties
are read-only and in the case of a list, append only.


Refinements
===========

Entities define a domain model that is used to express a configuration in. For each entity one or
more refinements can be defined. When an instance of an entity is constructed, the runtime
searches for refinements. Refinements are defined within the body of an ``implementation``
statement. After the implementation keyword the name of the refinement
follows. The name should start with a lowercase character. A refinement is closed with the
``end`` keyword.

In the body of an refinement statements are defined. This can be all statements except for
statements that define types and refinements such as entities, refinements and relations.

An implement statement connects refinements with entities. As such the entity is used as an
interface to one or more refinements that encapsulate implementation details. An refine
statement starts with the ``implements`` keyword followed by the name of the entity that it
defines a refinement for. Next the keyword ``using`` follows after which refinements
are listed, separated by commas. Such a statement defines refinements for instances of an entity
when no more specific refinements have been defined. In an implement statement after the
refinements list the ``when`` keyword is followed by an expression that defines when this
refinement needs to be chosen.

In some cases each instance of an entity requires an other refinement. For these cases
anonymous refinements are available. Directly after the constructor that instantiates an entity,
a refinement body follows that defines the refinements for this specific instance of an
entity. This construction does not provide the ability to provide multiple refinements like the
implement statement does. Instead it is possible to use the ``include`` keyword followed by the
name of the refinement that needs to be included.

Refinements for an entity::

    # Defining refinements and connecting them to entities
    implementation file1 for File:
    end

    implement File using file1

    host_a = std::Host(name = "hosta.example.com"):
        file_a = std::File(path = "/etc/motd", content = template("hosts/motd.tmpl"))
    end


Indexes and queries
===================

One of the key features of Impera is modeling relations in a configuration. To help maintaining these
relations the language provides a query function to lookup the other end of relations. This query
function can be used to lookup instances of an entity. A query is always expressed in function of
the properties of an entity. The properties that can be used in a query have to have an index
defined over them.

An index is defined with a statement that starts with the ``index`` keyword, followed by the entity
thats to be indexed. Next, between parenthesis a list of properties that belong to that index is
listed. Every combination of properties in an index should always be unique.

A query on a type is performed by specifying the entity type and between square brackets the query
on an index. A query should always specify values for all properties in an index, so only one value
will be returned.

Define an index over attributes::

    entity File:
        string path
        string content
    end

    index File(path)

    # search for a file
    file_1 = File[path = "/etc/motd"]

