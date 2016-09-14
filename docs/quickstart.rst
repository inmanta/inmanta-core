.. vim: spell

Quickstart
***************

This tutorial gets you started with Inmanta. 

The objective of this tutorial is to set up a Drupal CMS.  

Along the way, you will learn how to:

* Use vagrant to make a basic Inmanta install
* Create an Inmanta project
* Use existing configuration modules
* Create a configuration model to deploy a LAMP stack (Linux, Apache, MySQL and PHP).
* Deploy the configuration


Setting up the tutorial
=========================

To get started on Inmanta, we use vagrant to set up the management server and some machines to manage. 
Before starting this tutorial, first `install vagrant on your machine <https://www.vagrantup.com/docs/installation/>`_. 

 
Next, grab the vagrant box from out git repo and let vagrant do the setup of the Inmanta server.

.. code-block:: sh

    git clone https://github.com/inmanta/quickstart-vagrant.git
    cd quickstart-vagrant
    ./make_keys.sh
    vagrant up
    
Vagrant will set up the Inmanta server and two VM's to experiment on.
When vagrant is ready, you should be able to open the dashboard at http://127.0.0.1:8888.  

To get a shell on the Inmanta Server:

.. code-block:: sh

    vagrant ssh server
    
    
.. warning::

    When using modules from a private git repo, use the following command to enable agents forwarding.
    
    .. code-block:: sh

        vagrant ssh-config >ssh-cfg
        ssh -F ssh-cfg server -A


Create an Inmanta project
==========================

An Inmanta project bundles modules that contain configuration information. A project is nothing more
than a directory with a project.yml file, which contains parameters such as the location to search for
modules and where to find the server. 

Here we will create an Inmanta project ``quickstart`` with a basic configuration file.

.. code-block:: sh

    mkdir quickstart
    cd quickstart
    cat > project.yml <<EOF
    name: quickstart
    modulepath: libs
    downloadpath: libs
    repo: https://github.com/inmanta/
    description: A quickstart project that installs a drupal website.
    EOF

    
The configuration file ``project.yml`` defines that re-usable modules are stored in ``libs``. 

In the next section we will use existing modules to deploy our LAMP stack.

Re-use existing modules
=======================

At GitHub, we host modules to setup and mange many systems. Our modules are available in the https://github.com/inmanta/ repositories.

When you use an import statement in your model, Inmanta downloads these modules and their dependencies automatically. 


The configuration model
=======================

In this section we will use the configuration concepts defined in the existing modules to set up Drupal on the host named ``vm1``.

First, create a new ``main.cf`` file:

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


* Lines 1-6 import all required packages.  
* Line 9 defines on which we want to deploy Drupal. 

 * The *name* attribute is the hostname of the machine, which is later used to determine what configuration needs to be deployed on which machine. 
 * The *os* attribute defines which operating system this server runs. This is used to select the right tools (yum or dnf or apt).
 * The *ip* attribute is the IP address of this host. Now, we define this attribute manually, later on we will let Inmanta discover this automatically.

* Lines 12 and 13 deploy an apache server and mysql server on our host.
* Line 16 defines the name (hostname) of the web application.
* Lines 17-18 define a database for our Drupal website.
* Lines 19-20 define the actual Drupal application.



Deploy the configuration model
------------------------------

To deploy the project, we must first register it with the management server, by creating a project and an environment. This can be done via the dashboard, or via the CLI. 
For the CLI:

.. code-block:: sh

    inmanta-cli project-create -n test
    inmanta-cli environment-create  -n test -p test -r $(pwd) -b master --save
    
.. note::

	The ``--save`` option tells ``inmanta-cli`` to store the environment config in the ``.inmanta`` file. The compiler uses this file to find the server and export to the right environment.
	
Then compile the project and send it to the server:

.. code-block:: sh 

    inmanta -vvv  export
    
The first time you run this command may take a while, as all dependencies are downloaded.  When it is done, go to the `dashboard <http://127.0.0.1:8888>`_.  

Go to your environment, and press Deploy.

Accessing your new Drupal install
---------------------------------

When the install is done, you can find the new drupal at `http://localhost:8080/ <http://localhost:8080/>`_ to access your Drupal server.


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

    inmanta -vvv  export


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
    * The plugins plugins directory contains python file that are loaded by the platform and can
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

Next, edit the ``lamp/module.yml`` file and add meta-data to it:

.. code-block:: yaml

    name: lamp
    license: Apache 2.0
    version: 0.1


Configuration model
-------------------

In ``lamp/model/_init.cf`` we define the configuration model that defines the *lamp*
configuration module.

.. code-block:: ruby
    :linenos:

    import ip
    import apache
    import mysql
    import web
    import drupal
    
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

* Lines 1 to 7 define an entity which is the definition of a *concept* in the configuration model. On lines 2 and 6 typed attributes are defined which we can later on use in the implementation of an entity instance.
* Line 9 defines that *hostname* is an identifying attribute for instances of the DrupalStack entity. This also means that all instances of DrupalStack need to have a unique *hostname* attribute.
* Lines 11 and 12 define a relation between a Host and our DrupalStack entity. The first relation reads as follows:

    * Each DrupalStack instance has exactly one ip::Host instance that is available
      in the webserver attribute.
    * Each ip::Host has zero or one DrupalStack instances that use the host as a
      webserver. The DrupalStack instance is available in the drupal_stack_webserver attribute.

* On lines 14 to 25 an implementation is defined that provides a refinement of the DrupalStack entity. It encapsulates the configuration of a LAMP stack behind the interface of the entity by defining DrupalStack in function of other entities, which on their turn do the same. Inside the implementation the attributes and relations of the entity are available as variables. 
* On line 27, the *implement* statement links the implementation to the entity.

The composition
---------------

With our new LAMP module we can reduce the amount of required configuration code in the ``main.cf`` file
by using more *reusable* configuration code. Only three lines of site-specific configuration code are
required.

.. code-block:: ruby
    :linenos:
    import ip
    import redhat
    import lamp
    
    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::fedora23, ip="192.168.33.101")
    vm2=ip::Host(name="vm2", os=redhat::fedora23, ip="192.168.33.102")

    lamp::DrupalStack(webhost=vm1, mysqlhost=vm2, hostname="localhost", admin_user="admin",
                      admin_password="test", admin_email="admin@example.com", site_name="localhost")


Deploy the changes
------------------

Deploy the changes as before and nothing should change because it generates exactly the same
configuration.

.. code-block:: sh

    inmanta -vvv export


Next steps
==============

:doc:guides
