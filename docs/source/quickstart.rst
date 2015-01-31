.. vim: spell

Getting started
***************

This tutorial gets you started with Impera. You will learn how to:

   * Install Impera
   * Create an Impera project
   * Use existing configuration modules
   * Create a configuration model to deploy a LAMP (Linux, Apache, Mysql and PHP) stack
   * Deploy the configuration


Impera exists of several components:

   * A compiler that builds the configuration model,
   * The central Impera server that stores states,
   * Impera agents on each managed system that deploy configuration changes.

In the remainder of this chapter we will install the framework but use it without external server and without agents.

.. warning::

   DO NOT run this guide on your own machine, or it will be reconfigured. Use two virtual machines,
   with hostnames vm1 and vm2 to be fully compatible with this guide. This guide has been tested on Fedora
   21 and Ubuntu 14.04.

Installing Impera
=================

For Ubuntu 14.04 (trusty) and Fedora 21, follow the instructions below. For other distributions,
install from `source <https://github.com/impera-io/impera>`_. The
`readme <https://github.com/impera-io/impera/blob/master/Readme.md>`_ contains installation instructions to
install Impera from source.


Fedora
------

The packages to install Impera are available in a yum/dnf repository. Following
instructions add the repository and install Impera on vm1:

.. code-block:: sh

    sudo curl -o /etc/yum.repos.d/impera.repo https://impera.io/repo/impera.repo
    sudo yum install -y python3-impera

On vm2 Impera is not required, as we will do an agentless install. However, `this requires python3 to be installed on all machines <https://github.com/impera-io/impera/issues/1>`_. To install Python 3 on vm2:

.. code-block:: sh

    sudo yum install -y python3

Ubuntu
------

The packages to install Impera on Ubuntu are available in a ppa. The following instructions add the
repository and install Impera:

.. code-block:: sh

    echo "deb https://impera.io/repo/trusty/ /" | sudo su -c "cat > /etc/apt/sources.list.d/impera.list"
    sudo apt-get update
    sudo apt-get install python3-impera

Apt might warn about unauthenticated packages, because the packages in our repository have not been
signed.


SSH Root access
---------------

In this tutorial we use agentless deployments, with vm1 as the management machine. 
This means that it will manage itself and vm2 over SSH, thus requiring SSH root access to vm1 and vm2. 
Therefore your public SSH key needs to be installed in the ``authorized_keys`` file of the root user on both machines. 

If your public key is already installed in the current user, you can copy it to the root user with the following commands:

.. code-block:: sh

    sudo cp -a .ssh /root/
    sudo chown -R root:root /root/.ssh


In this guide we assume that you can login into vm2 using the same SSH keypair as you used to
login into vm1.  Therefore, use agent forwarding (the -A option) when you login into the vm1, 
*before you continue with this guide*.

Check from the user on vm1 if you can login into vm1 and vm2 as root and accept the host key.

.. code-block:: sh

    ssh root@IP_OF_VM1
    ssh root@IP_OF_VM2

SELinux
-------

In a default Fedora, SELinux and possibly the firewall are configured and activated. This may cause
problems because managing these services is not covered here. We recommend that
you either set SELinux to permissive mode and disable the firewall with:

.. code-block:: sh

   sudo setenforce 0
   sudo sed -i "s/SELINUX=enforcing/SELINUX=permissive/g" /etc/sysconfig/selinux
   sudo systemctl stop firewalld

Or consult the Fedora documentation and change the firewall settings and set the correct SELinux
booleans.


Create an Impera project
========================

An Impera project bundles modules that contain configuration information. A project is nothing more
than a directory with an .impera file, which contains parameters such as the location to search for
modules and where to find the server.

Here we will create an Impera project ``quickstart`` with a basic configuration file.

.. code-block:: sh

    mkdir quickstart
    cd quickstart
    cat > .impera <<EOF
    [config]
    export=
    git-http-only=true
    EOF
    touch main.cf
    cat > project.yml <<EOF
    name: quickstart
    modulepath: libs
    downloadpath: libs
    description: A quickstart project that installs a drupal website.
    EOF


The configuration file ``project.yml`` defines that re-usable modules are stored in ``libs``. The Impera compiler looks
for a file called ``main.cf`` to start the compilation from.  The last line, creates an empty file.

In the next section we will re-use existing modules to deploy our LAMP stack.

Re-use existing modules
=======================

At GitHub, we host already many modules that provide types and refinements for one or more
operating systems. Our modules are available in the https://github.com/impera-io/ repositories.

Impera downloads these modules and their dependencies. For this tutorial, we need the
apache and drupal configuration modules, and the redhat and ubuntu modules for the correct refinements.
We add these requirements in the ``project.yml`` file under the ``requires:`` attribute. Open the ``project.yml``
file and add the following lines:

.. code-block:: yaml

    requires:
        drupal: git@github.com:impera-io/drupal, ">= 0.1"
        apache: git@github.com:impera-io/apache, ">= 0.1"
        redhat: git@github.com:impera-io/redhat, ">= 0.1"
        ubuntu: git@github.com:impera-io/ubuntu, ">= 0.1"

Each line under the ``requires:`` attribute lists a required Impera module. The key is the name of the
module and the value is the location of the git project, followed by the version identifier (after the comma).

Next, we instruct Impera to download all modules and install the required python modules for the
plugins and resource handlers. These modules are installed in a virtualenv. Execute the following
command in the quickstart directory:

.. code-block:: sh

    impera modules install


The configuration model
=======================

In this section we will use the configuration concepts defined in the existing
modules to create a new composition that defines the final configuration model. In
this guide we assume a server called ``vm1`` on which we will install Drupal.

Compose a configuration model
-----------------------------

The modules we installed in the previous section contain the configuration
required for certain services or subsystems. In this section we will make
a composition of the configuration modules to deploy and configure a Drupal
website. This composition has to be specified in the ``main.cf`` file:

.. code-block:: ruby
    :linenos:

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::fedora21, ip="IP_OF_VM1")
    #vm1=ip::Host(name="vm1", os=ubuntu::ubuntu1404, ip="IP_OF_VM1")

    # add a mysql and apache http server
    web_server=apache::Server(host=vm1)
    mysql_server=mysql::Server(host=vm1)

    # deploy drupal in that virtual host
    name=web::Alias(hostname="localhost")
    db=mysql::Database(server=mysql_server, name="drupal_test", user="drupal_test",
                       password="Str0ng-P433w0rd")
    drupal::Application(name=name, container=web_server, database=db, admin_user="root",
                        admin_password="test", admin_email="admin@example.com", site_name="localhost")


On line 2 we define the server on which we want to deploy Drupal. The *name* attribute is the hostname of the
machine, which is later used to determine what configuration needs to be deployed on which machine.
The *os* attribute defines which operating system this server runs. This attribute can be used to
create configuration modules that handle the heterogeneity of different operating systems. 
The current value refers to Fedora. To deploy this on Ubuntu, change this value to
ubuntu::ubuntu1404. The *ip* attribute is the IP address of this host. In this introduction 
we define this attribute manually, later on we will let Impera manage this automatically. 

Lines 6 and 7 deploy an httpd server and mysql server on our server.

Line 10 defines the name (hostname) of the web application, and line 13 defines the actual Drupal
website to deploy.

Line 11 defines a database for our Drupal website.


Deploy the configuration model
------------------------------

The normal mode of operation of Impera uses a central server to deploy configurations. Each managed host
runs a configuration agent that receives configuration updates from a central server. This setup is
quite elaborate and in this introduction we will use the single shot *deploy* command. This command
compiles, exports and enforces the configuration for a single machine.

The configuration we made in the previous section can be deployed by executing the deploy command in
the Impera project.

.. code-block:: sh

    impera deploy --dry-run -a vm1 -i IP_OF_VM1
    impera deploy -a vm1 -i IP_OF_VM1

The first command compiles the configuration model and does a dry run of the deployment process and
lists the changes that should be made. The second command does the actual deployment. We could use
a local deployment, but that means we should run Impera as root and this would create permission
problems when we deploy changes on the second VM.



Accessing your new Drupal install
---------------------------------

Use SSH port-forwarding to forward port 80 on vm1 to your local machine, for example to
port 2080 (ssh -L 2080:localhost:80 USERNAME@IP_OF_VM1). This enables you to surf to
http://localhost:2080/

.. warning::

   Using "localhost" in the url is essential because the configuration model
   generates a name-based virtual host that matches the name *localhost*.

On the first access the database will not have been initialised. Surf to
http://localhost:2080/install.php

The database has already been configured and Drupal should skip this setup to
the point where you can configure details such as the admin user.

.. note::

   Windows users can use putty for SSH access to their servers. Putty also
   allows port forwarding. You can find more information on this topic here:
   http://the.earth.li/~sgtatham/putty/0.63/htmldoc/Chapter3.html#using-port-forwarding


Managing multiple machines
==========================

The real power of Impera appears when you want to manage more than one machine. In this section we will
move the mysql server from vm1 to a second virtual machine called vm2. We will still manage this
additional machine in ``single shot mode`` using a remote deploy.




Update the configuration model
------------------------------

A second virtual machine is easily added to the system by adding the definition
of the virtual machine to the configuration model and assigning the mysql server
to the new virtual machine.

.. code-block:: ruby
    :linenos:

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::fedora21, ip="IP_OF_VM1")
    vm2=ip::Host(name="vm2", os=redhat::fedora21, ip="IP_OF_VM2")

    # add a mysql and apache http server
    web_server=apache::Server(host=vm1)
    mysql_server=mysql::Server(host=vm2)

    # deploy drupal in that virtual host
    name=web::Alias(hostname="localhost")
    db=mysql::Database(server=mysql_server, name="drupal_test", user="drupal_test",
                       password="Str0ng-P433w0rd")
    drupal::Application(name=name, container=web_server, database=db, admin_user="root",
                        admin_password="test", admin_email="admin@example.com", site_name="localhost")

On line 3 the definition of the new virtual machine is added. On line 7 the
mysql server is assigned to vm2.

Deploy the configuration model
------------------------------

Deploy the new configuration model by invoking a local deploy on vm1 and a
remote deploy on vm2. Because the vm2 name that is used in the configuration model does not resolve
to an IP address we provide this address directly with the -i parameter.

.. code-block:: sh

    impera deploy -a vm2 -i IP_OF_VM2    
    impera deploy -a vm1 -i IP_OF_VM1
    
If you browse to the drupal site again, the database should be empty once more.

Create your own modules
=======================

Impera enables developers of a configuration model to make it modular and
reusable. In this section we create a configuration module that defines how to
deploy a LAMP stack with a Drupal site in a two or three tiered deployment.

Module layout
-------------
A configuration module requires a specific layout:

    * The name of the module is determined by the top-level directory. In this
      directory the only required directory is the ``model`` directory with a file
      called ``_init.cf``.
    * What is defined in the ``_init.cf`` file is available in the namespace linked with
      the name of the module. Other files in the model directory create subnamespaces.
    * The files directory contains files that are deployed verbatim to managed
      machines
    * The templates directory contains templates that use parameters from the
      configuration model to generate configuration files.
    * Python files in the plugins directory are loaded by the platform and can
      extend it using the Impera API.


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
will call ``lamp`` and the ``_init.cf`` file and the ``module.yml`` file is required to be a valid Impera
module. The following commands create all directories to develop a full-featured module.

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

In ``lamp/model/_init.cf`` we define the configuration model that defines the lamp
configuration module.

.. code-block:: ruby
    :linenos:

    entity DrupalStack:
        string stack_id
        string vhostname
    end

    index DrupalStack(stack_id)

    ip::Host webhost [1] -- [0:1] DrupalStack drupal_stack_webhost
    ip::Host mysqlhost [1] -- [0:1] DrupalStack drupal_stack_mysqlhost

    implementation drupalStackImplementation for DrupalStack:
        # add a mysql and apache http server
        web_server=apache::Server(host=webhost)
        mysql_server=mysql::Server(host=mysqlhost)

        # deploy drupal in that virtual host
        name=web::Alias(hostname="localhost")
        db=mysql::Database(server=mysql_server, name="drupal_test", user="drupal_test",
                           password="Str0ng-P433w0rd")
        drupal::Application(name=name, container=web_server, database=db, admin_user="root",
                            admin_password="test", admin_email="admin@localhost", site_name="localhost")
    end

    implement DrupalStack using drupalStackImplementation

On line 1 to 4 we define an entity which is the definition of a *concept* in
the configuration model. Entities behave as an interface to a partial
configuration model that encapsulates parts of the configuration, in this case
how to configure a LAMP stack. On line 2 and 3 typed attributes are defined
which we can later on use in the implementation of an entity instance.

Line 6 defines that stack_id is an identifying attribute for instances of
the DrupalStack entity. This also means that all instances of DrupalStack need
to have a unique stack_id attribute.

On lines 8 and 9 we define a relation between a Host and our DrupalStack entity.
This relation represents a double binding between these instances and it has a
multiplicity. The first relations reads as following:

    * Each DrupalStack instance has exactly one ip::Host instance that is available
      in the webserver attribute.
    * Each ip::Host has zero or one DrupalStack instances that use the host as a
      webserver. The DrupalStack instance is available in the drupal_stack_webserver attribute.

.. warning::

   On line 8 and 9 we explicity give the DrupalStack side of the relation a
   multiplicity that starts from zero. Setting this to one would break the ip
   module because each Host would require an instance of DrupalStack.

On line 11 to 26 an implementation is defined that provides a refinement of the DrupalStack entity.
It encapsulates the configuration of a LAMP stack behind the interface of the entity by defining
DrupalStack in function of other entities, which on their turn do the same. The refinement process
is evaluated by the compiler and continues until all instances are refined into instances of
entities that Impera knows how to deploy.

Inside the implementation the attributes and relations of the entity are available as variables.
They can be hidden by new variable definitions, but are also accessible through the ``self``
variable (not used in this example). On line 19 an attribute is used in an inline template with the
{{ }} syntax.

And finally on line 28 we link the implementation to the entity itself.

The composition
---------------

With our new LAMP module we can reduce the amount of required configuration code in the main.cf file
by using more *reusable* configure code. Only three lines of site specific configuration code are
left.

.. code-block:: ruby
    :linenos:

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::fedora21, ip="IP_OF_VM2")
    vm2=ip::Host(name="vm2", os=redhat::fedora21, ip="IP_OF_VM2")

    lamp::DrupalStack(webhost=vm1, mysqlhost=vm2, stack_id="drupal_test", vhostname="localhost")

Deploy the changes
------------------

Deploy the changes as before and nothing should change because it generates exactly the same
configuration.

.. code-block:: sh

    impera deploy -a vm1 -i IP_OF_VM1
    impera deploy -a vm2 -i IP_OF_VM2

