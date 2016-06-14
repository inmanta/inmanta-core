.. vim: spell

Getting started
***************

This tutorial gets you started with Inmanta. You will learn how to:

   * Install Inmanta
   * Create an Inmanta project
   * Use existing configuration modules
   * Create a configuration model to deploy a LAMP (Linux, Apache, MySQL and PHP) stack
   * Deploy the configuration


Inmanta exists of several components:

   * A compiler that builds the configuration model,
   * The central Inmanta server that stores states,
   * Inmanta agents on each managed system that deploy configuration changes.


This tutorial requires three machines: a management server (e.g. your own machine) and two VM's to deploy software to. 

.. warning::

   DO NOT run this guide on your own machine, or it will be reconfigured. Use two virtual machines,
   with host names vm1 and vm2 to be fully compatible with this guide. This guide has been tested on Fedora
   21 and Ubuntu 14.04.

Installing Inmanta
=================

For Ubuntu 14.04 (trusty) and Fedora 21, follow the instructions below. For other distributions,
install from `source <https://github.com/inmanta>`_. The
`readme <https://github.com/inmanta>`_ contains installation instructions to
install Inmanta from source.

From Source
------------

.. code-block:: sh

    sudo dnf install git python3 python3-devel gcc python3-virtualenv python-virtualenv vim redhat-rpm-config
    # todo: add /bin/virtualenv3 to search path, don't install python-virtualenv
    git clone git@git.inmanta.com:platform/inmanta.git
    cd inmanta
    sudo pip3 install -r requirements.txt
    sudo python3 setup.py install
    sudo inmanta

Fedora
------

The packages to install Inmanta are available in a yum/dnf repository. Following
instructions add the repository and install Inmanta on vm1:

.. code-block:: sh

    sudo curl -o /etc/yum.repos.d/inmanta.repo https://inmanta.io/repo/inmanta.repo
    sudo yum install -y python3-inmanta

On vm2 Inmanta is not required, as we will do an agentless install. However, `this requires python3 to be installed on all machines <https://github.com/inmanta>`_. To install Python 3 on vm2:

.. code-block:: sh

    sudo yum install -y python3

Ubuntu
------

The packages to install Inmanta on Ubuntu are available in a ppa. The following instructions add the
repository and install Inmanta:

.. code-block:: sh

    echo "deb https://inmanta.io/repo/trusty/ /" | sudo su -c "cat > /etc/apt/sources.list.d/inmanta.list"
    sudo apt-get update
    sudo apt-get install python3-inmanta

Apt might warn about unauthenticated packages, because the packages in our repository have not been
signed.


Server Setup
------------

First create a server config file (replace 'IP_OF_THE_SERVER' with the actual IP of the server):

.. code-block:: sh

    sudo mkdir /var/log/inmanta
    sudo chmod a+rw /var/log/inmanta
    sudo dnf install mongodb-server
    sudo systemctl start mongod
    
    cat > server.cfg <<EOF
    [config]
    state-dir=/tmp/inmanta
    heartbeat-interval = 60
    fact-expire = 3600

    [dashboard]
    enabled=True
    path=/home/fedora/impera-dashboard/dist

    [server]
    server_address= IP_OF_THE_SERVER
    EOF
    
    cd
    git clone git@git.inmanta.com:platform/impera-dashboard.git
    
    
    
To start the server

.. code-block:: sh
    
    inmanta -vvv -c server.cfg server
    
    

    
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
    inmanta modules install
    inmanta-cli project-create -n test
    inmanta-cli environment-create  -n test -p test -r $(pwd) -b master
    ENV_ID=$(inmanta-cli environment-list |grep "| test"| cut -d "|" -f 5)

    

The configuration file ``project.yml`` defines that re-usable modules are stored in ``libs``. The Inmanta compiler looks
for a file called ``main.cf`` to start the compilation from.  The last line, creates an empty file.

In the next section we will re-use existing modules to deploy our LAMP stack.

Re-use existing modules
=======================

At GitHub, we host already many modules that provide types and refinements for one or more
operating systems. Our modules are available in the https://github.com/inmanta/ repositories.

Inmanta downloads these modules and their dependencies. For this tutorial, we need the
apache and drupal configuration modules, and the redhat and ubuntu modules for the correct refinements.
We add these requirements in the ``project.yml`` file under the ``requires:`` attribute. Open the ``project.yml``
file and add the following lines:

.. code-block:: yaml

    requires:
        drupal: git@github.com:inmanta-io/drupal, ">= 0.1"
        apache: git@github.com:inmanta-io/apache, ">= 0.1"
        redhat: git@github.com:inmanta-io/redhat, ">= 0.1"
        ubuntu: git@github.com:inmanta-io/ubuntu, ">= 0.1"

Each line under the ``requires:`` attribute lists a required Inmanta module. The key is the name of the
module and the value is the location of the git project, followed by the version identifier (after the comma).

Next, we instruct Inmanta to download all modules and install the required python modules for the
plugins and resource handlers. These modules are installed in a virtualenv. Execute the following
command in the quickstart directory:

.. code-block:: sh

    inmanta modules install


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


On line 2 we define the server on which we want to deploy Drupal. The *name* attribute is the hostname of the
machine, which is later used to determine what configuration needs to be deployed on which machine.
The *os* attribute defines which operating system this server runs. This attribute can be used to
create configuration modules that handle the heterogeneity of different operating systems.
The current value refers to Fedora. To deploy this on Ubuntu, change this value to
ubuntu::ubuntu1404. The *ip* attribute is the IP address of this host. In this introduction
we define this attribute manually, later on we will let Inmanta manage this automatically.

Lines 6 and 7 deploy an httpd server and mysql server on our server.

Line 10 defines the name (hostname) of the web application, and line 13 defines the actual Drupal
website to deploy.

Line 11 defines a database for our Drupal website.


Deploy the configuration model
------------------------------

The normal mode of operation of Inmanta uses a central server to deploy configurations. Each managed host
runs a configuration agent that receives configuration updates from a central server. This setup is
quite elaborate and in this introduction we will use the single shot *deploy* command. This command
compiles, exports and enforces the configuration for a single machine.

The configuration we made in the previous section can be deployed by executing the deploy command in
the Inmanta project.

.. code-block:: sh

    inmanta modules install 
    inmanta -vvv  export -e $ENV_ID --server_address "127.0.0.1"  --server_port "8888"
    
.. code-block:: sh   

    sudo mkdir /var/log/inmanta
    sudo chmod a+rw /var/log/inmanta
    mkdir /tmp/lib
    mkdir /tmp/lib/impera
    
    cat > agent.cfg <<EOF
    [config]
    heartbeat-interval = 60
    state-dir=/tmp/lib/impera

    agent-names = vm1,vm2
    environment=b4c4ebef-3bc8-4c61-875f-868c795b4a96
    agent-map=vm1=172.17.3.67,vm2=172.17.3.68

    [agent_rest_transport]
    port = 8888
    host = 172.17.3.66
    EOF
    

The first command compiles the configuration model and does a dry run of the deployment process and
lists the changes that should be made. The second command does the actual deployment. We could use
a local deployment, but that means we should run Inmanta as root and this would create permission
problems when we deploy changes on the second VM.



Accessing your new Drupal install
---------------------------------

Use SSH port forwarding to forward port 80 on vm1 to your local machine, for example to
port 2080 (ssh -L 2080:localhost:80 USERNAME@IP_OF_VM1). As the database has already been configured,
you can then immediately surf to `http://localhost:2080/ <http://localhost:2080/>`_ to access your Drupal server.

.. warning::

   Using "localhost" in the url is essential because the configuration model
   generates a name-based virtual host that matches the name *localhost*.

.. note::

   Windows users can use PuTTY for SSH access to their servers. PuTTY also
   allows port forwarding.

Managing multiple machines
==========================

The real power of Inmanta appears when you want to manage more than one machine. In this section we will
move the MySQL server from ``vm1`` to a second virtual machine called ``vm2``. We will still manage this
additional machine in *single shot mode* using a remote deploy.




Update the configuration model
------------------------------

A second virtual machine is easily added to the system by adding the definition
of the virtual machine to the configuration model and assigning the MySQL server
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

    inmanta deploy -a vm2 -i IP_OF_VM2
    inmanta deploy -a vm1 -i IP_OF_VM1

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

