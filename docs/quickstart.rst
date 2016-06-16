.. vim: spell

Getting started
***************

This tutorial gets you started with Inmanta. You will learn how to:

* Use vagrant to make a basic Inmanta install
* Create an Inmanta project
* Use existing configuration modules
* Create a configuration model to deploy a LAMP (Linux, Apache, MySQL and PHP) stack
* Deploy the configuration

An Inmanta setup has several parts: 

.. image:: _static/overview.svg
   :width: 70%
   :alt: Overview of the Inmanta platform

* The central Inmanta server. This server manages the deployment process.
* A mongodb database. The central Inmanta server stores it state in a mongo database.
* The git server. The source code of the configuration models is stored in (one or more) git repositories.  
* The compiler. To convert the source code into deployable artifacts, it is compiled and sent to the server. If the model consists of multiple modules, these are downloaded automatically from the git server. The compiler can run either on a developer machine or on the server. 
* CLI and Dashboard. To control the server, you can use either the web dashboard or the command line tools. 
* The Inmanta agents. Agents deploy configuration to the target machines. Agent can run on the server, or on the machines they manage. 


The Goal
=========

The goal of this tutorial is to set up a Drupal CMS.  Drupal itself has a number of dependencies:

1. A web server to server Drupal
2. A `vhost <https://en.wikipedia.org/wiki/Virtual_hosting>`_ in the webserver 
3. A database server to store data in
4. A database configured in the database server (with a username and password and the proper permissions configured)

A such, setting up drupal is quite a lot of work. All parts must be installed and configured. Depending on the operating system, the configuration can be different,...

In this tutorial, we will set up Drupal using Impera, automatically.

Setting up the tutorial
=========================

To get started on Inmanta, we use vagrant to set up the server and some machines to manage. 
Before starting this tutorial, first `install vagrant on your machine <https://www.vagrantup.com/docs/installation/>`_. 

 
Next, grab vagrant box from out git repo and let vagrant do the setup

.. code-block:: sh

    git clone git@git.inmanta.com:demo/tutorial-vagrant.git
    cd tutorial-vagrant
    vagrant up
    
When vagrant is ready, you should be able to open the dashboard at http://127.0.0.1:8888.  

To get a shell on the Inmanta Server machine:

.. code-block:: sh

    vagrant ssh server
    
    
.. warning::

    When using modules from a private git repo, use the following command to enable agents forwarding. (In this case, compiling from the server is not possible)
    
    .. code-block:: sh

        vagrant ssh-config >ssh-cfg
        ssh -F ssh-cfg server -A


Create an Inmanta project
========================

An Inmanta project bundles modules that contain configuration information. A project is nothing more
than a directory with an .inmanta file, which contains parameters such as the location to search for
modules and where to find the server.

Here we will create an Inmanta project ``quickstart`` with a basic configuration file.

.. code-block:: sh

    mkdir quickstart
    cd quickstart
    cat > .inmanta <<EOF
    [config]
    export=
    git-http-only=true
    EOF
    touch main.cf
    cat > project.yml <<EOF
    name: quickstart
    modulepath: libs
    downloadpath: libs
    repo: git@git.inmanta.com:modules/
    description: A quickstart project that installs a drupal website.
    EOF

    
The configuration file ``project.yml`` defines that re-usable modules are stored in ``libs``. The Inmanta compiler looks for a file called ``main.cf`` to start the compilation from.  The last line, creates an empty file.


In the next section we will re-use existing modules to deploy our LAMP stack.

Re-use existing modules
=======================

At GitHub, we host already many modules that provide types and refinements for one or more
operating systems. Our modules are available in the https://github.com/inmanta/ repositories.

When you use an import statement in your model, Inmanta downloads these modules and their dependencies. 



The configuration model
=======================

In this section we will use the configuration concepts defined in the existing
modules to create a new composition that defines the final configuration model. In
this guide we assume a server called ``vm1`` on which we will install Drupal.

Compose a configuration model
-----------------------------

In this section we will make
a composition of the configuration modules to deploy and configure a Drupal
website. This composition has to be specified in the ``main.cf`` file:

.. code-block:: ruby
    :linenos:

    import ip
    import redhat
    import apache
    import mysql
    import web
    import drupal

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::fedora23, ip="192.168.33.101")

    # add a mysql and apache http server
    web_server=apache::Server(host=vm1)
    mysql_server=mysql::Server(host=vm1)

    # deploy drupal in that virtual host
    name=web::Alias(hostname="localhost")
    db=mysql::Database(server=mysql_server, name="drupal_test", user="drupal_test",
                       password="Str0ng-P433w0rd")
    drupal::Application(name=name, container=web_server, database=db, admin_user="admin",
                        admin_password="test", admin_email="admin@example.com", site_name="localhost")


On lines 1-6 we import all required packages.  
On line 9 we define the server on which we want to deploy Drupal. The *name* attribute is the hostname of the
machine, which is later used to determine what configuration needs to be deployed on which machine.
The *os* attribute defines which operating system this server runs. This attribute can be used to
create configuration modules that handle the heterogeneity of different operating systems.
The current value refers to Fedora. To deploy this on Ubuntu, import ubuntu and change this value to
ubuntu::ubuntu1404. The *ip* attribute is the IP address of this host. In this introduction
we define this attribute manually, later on we will let Inmanta manage this automatically.

Lines 12 and 13 deploy an httpd server and mysql server on our server.

Line 16 defines the name (hostname) of the web application, and line 18 defines the database used by Drupal.

Line 19 defines a database for our Drupal website.


Deploy the configuration model
------------------------------

The first step is creating a project and an environment on the server. This can be done via the dashboard, or via the CLI. 
For the CLI:

.. code-block:: sh

    inmanta-cli project-create -n test
    inmanta-cli environment-create  -n test -p test -r $(pwd) -b master
    
When the environment is created, its UUID will be reported. This UUID is needed for the compiler to correctly contact the server.
To compile the model and send it to the server:

.. code-block:: sh 

    inmanta -vvv  export -e [ENV_ID] --server_address 127.0.0.1  --server_port 8888

Then go to the `dashboard <http://127.0.0.1:8888>`_.  Go to your environment, and press Deploy.

Accessing your new Drupal install
---------------------------------

When the install is done, you can find the new drupal at `http://localhost:8080/ <http://localhost:8080/>`_ to access your Drupal server.

.. warning::

   Using "localhost" in the url is essential because the configuration model
   generates a name-based virtual host that matches the name *localhost*.


Managing multiple machines
==========================

The real power of Inmanta appears when you want to manage more than one machine. In this section we will
move the MySQL server from ``vm1`` to a second virtual machine called ``vm2``.


Update the configuration model
------------------------------

A second virtual machine is easily added to the system by adding the definition
of the virtual machine to the configuration model and assigning the MySQL server
to the new virtual machine.

.. code-block:: ruby
    :linenos:

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::fedora23, ip="192.168.33.101")
    vm2=ip::Host(name="vm2", os=redhat::fedora23, ip="192.168.33.102")

    # add a mysql and apache http server
    web_server=apache::Server(host=vm1)
    mysql_server=mysql::Server(host=vm2)

    # deploy drupal in that virtual host
    name=web::Alias(hostname="localhost")
    db=mysql::Database(server=mysql_server, name="drupal_test", user="drupal_test",
                       password="Str0ng-P433w0rd")
    drupal::Application(name=name, container=web_server, database=db, admin_user="admin",
                        admin_password="test", admin_email="admin@example.com", site_name="localhost")

On line 3 the definition of the new virtual machine is added. On line 7 the
MySQL server is assigned to vm2.

Deploy the configuration model
------------------------------

Deploy the new configuration model by invoking a local deploy on vm1 and a
remote deploy on vm2. Because the vm2 name that is used in the configuration model does not resolve
to an IP address we provide this address directly with the -i parameter.

.. code-block:: sh 

    inmanta -vvv  export -e [ENV_ID] --server_address 127.0.0.1  --server_port 8888


If you browse to the drupal site again, the database should be empty once more.

Create your own modules
=======================

Inmanta enables developers of a configuration model to make it modular and
reusable. In this section we create a configuration module that defines how to
deploy a LAMP stack with a Drupal site in a two- or three-tiered deployment.

Module layout
-------------
A configuration module requires a specific layout:

    * The name of the module is determined by the top-level directory. Within this
      module directory, a ``module.yml`` file has to be specified.
    * The only mandatory subdirectory is the ``model`` directory containing a file
      called ``_init.cf``. What is defined in the ``_init.cf`` file is available in the namespace linked with
      the name of the module. Other files in the model directory create subnamespaces.
    * The files directory contains files that are deployed verbatim to managed
      machines.
    * The templates directory contains templates that use parameters from the
      configuration model to generate configuration files.
    * Python files in the plugins directory are loaded by the platform and can
      extend it using the Inmanta API.


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


We will create our custom module in the ``libs`` directory of the quickstart project. Our new module
will be called *lamp*, and we require the ``_init.cf`` file (in the ``model`` subdirectory) and
the ``module.yml`` file to have a valid Inmanta module.
The following commands create all directories and files to develop a full-featured module:

.. code-block:: sh

    cd ~/quickstart/libs
    mkdir {lamp,lamp/model}
    touch lamp/model/_init.cf
    touch lamp/module.yml

    mkdir {lamp/files,lamp/templates}
    mkdir lamp/plugins
    touch lamp/plugins/__init__.py

Next, edit the ``lamp/module.yml`` file and add meta-data to it:

.. code-block:: yaml

    name: lamp
    license: Apache 2.0


Configuration model
-------------------

In ``lamp/model/_init.cf`` we define the configuration model that defines the *lamp*
configuration module.

.. code-block:: ruby
    :linenos:

    entity DrupalStack:
        string hostname
        string admin_user
        string admin_password
        string admin_email
        string site_name
    end

    index DrupalStack(hostname)

    ip::Host webhost [1] -- [0:1] DrupalStack drupal_stack_webhost
    ip::Host mysqlhost [1] -- [0:1] DrupalStack drupal_stack_mysqlhost

    implementation drupalStackImplementation for DrupalStack:
        # add a mysql and apache http server
        web_server=apache::Server(host=webhost)
        mysql_server=mysql::Server(host=mysqlhost)

        # deploy drupal in that virtual host
        name=web::Alias(hostname=hostname)
        db=mysql::Database(server=mysql_server, name="drupal_test", user="drupal_test",
                           password="Str0ng-P433w0rd")
        drupal::Application(name=name, container=web_server, database=db, admin_user=admin_user,
                            admin_password=admin_password, admin_email=admin_email, site_name=site_name)
    end

    implement DrupalStack using drupalStackImplementation

On lines 1 to 7 we define an entity which is the definition of a *concept* in
the configuration model. Entities behave as an interface to a partial
configuration model that encapsulates parts of the configuration, in this case
how to configure a LAMP stack. On lines 2 and 6 typed attributes are defined
which we can later on use in the implementation of an entity instance.

Line 9 defines that *hostname* is an identifying attribute for instances of
the DrupalStack entity. This also means that all instances of DrupalStack need
to have a unique *hostname* attribute.

On lines 11 and 12 we define a relation between a Host and our DrupalStack entity.
This relation represents a double binding between these instances and it has a
multiplicity. The first relation reads as follows:

    * Each DrupalStack instance has exactly one ip::Host instance that is available
      in the webserver attribute.
    * Each ip::Host has zero or one DrupalStack instances that use the host as a
      webserver. The DrupalStack instance is available in the drupal_stack_webserver attribute.

.. warning::

   On lines 11 and 12 we explicity give the DrupalStack side of the relation a
   multiplicity that starts from zero. Setting this to one would break the ip
   module because each Host would require an instance of DrupalStack.

On lines 14 to 25 an implementation is defined that provides a refinement of the DrupalStack entity.
It encapsulates the configuration of a LAMP stack behind the interface of the entity by defining
DrupalStack in function of other entities, which on their turn do the same. The refinement process
is evaluated by the compiler and continues until all instances are refined into instances of
entities that Inmanta knows how to deploy.

Inside the implementation the attributes and relations of the entity are available as variables.
They can be hidden by new variable definitions, but are also accessible through the ``self``
variable (not used in this example).

And finally the *implement* statement on line 27 links the implementation to the entity.

The composition
---------------

With our new LAMP module we can reduce the amount of required configuration code in the ``main.cf`` file
by using more *reusable* configuration code. Only three lines of site-specific configuration code are
required.

.. code-block:: ruby
    :linenos:

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::fedora21, ip="IP_OF_VM1")
    vm2=ip::Host(name="vm2", os=redhat::fedora21, ip="IP_OF_VM2")

    lamp::DrupalStack(webhost=vm1, mysqlhost=vm2, hostname="localhost", admin_user="admin",
                      admin_password="test", admin_email="admin@example.com", site_name="localhost")


Deploy the changes
------------------

Deploy the changes as before and nothing should change because it generates exactly the same
configuration.

.. code-block:: sh

    inmanta deploy -a vm1 -i IP_OF_VM1
    inmanta deploy -a vm2 -i IP_OF_VM2

