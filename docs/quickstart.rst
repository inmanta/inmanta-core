.. vim: spell

Quickstart
***************

This tutorial gets you started with the Inmanta orchestration tool.

Inmanta is intended to manage complex infrastructures, often in the cloud or other virtualized environments.
In this guide, we go for a less complex setup: install the Drupal CMS on two VMs.
First, we use vagrant to setup a basic environment with two empty VMs and an Inmanta server.
Then, we use Inmanta to install Drupal on these VMs.

Setting up the tutorial
_________________________

To quickly get started with Inmanta, use Vagrant to set up an environment to host the Inmanta server and some machines to be
managed. Before starting this tutorial, first `install vagrant on your machine <https://www.vagrantup.com/docs/installation/>`_.


Next, grab the Vagrant box from our Git repo and let Vagrant do the setup of the Inmanta server.

.. code-block:: sh

    git clone https://github.com/inmanta/quickstart-vagrant.git
    cd quickstart-vagrant
    ./make_keys.sh
    vagrant up

Vagrant will set up the Inmanta server and two VMs to experiment on.
When Vagrant is ready, you should be able to open the dashboard at http://127.0.0.1:8888.

.. warning::

    When using Vagrant in combination with VirtualBox, there is a known issue with SSH keys.
    If this problem occurs to you, add the following lines to the Vagrantfile:

    .. code-block:: sh

        config.ssh.insert_key = false

    Notice that you are using a default key, this is insecure.

To get a shell on the Inmanta server:

.. code-block:: sh

    vagrant ssh server


Automatically deploying Drupal
_______________________________

At this point, you can go through the quickstart guide in two ways: via the dashboard or via the command line interface.
For the CLI, go to the next section. For the Dashboard, go to :ref:`qsdashboard`.

.. _cli:

Single machine deployment using the CLI
=======================================

An Inmanta project bundles modules that contain configuration information. A project is nothing more
than a directory with a project.yml file, which contains parameters such as the location to search for
modules and where to find the server.

Here we will get a project from github.

.. code-block:: sh

    git clone https://github.com/inmanta/quickstart.git
    cd quickstart


The configuration file ``project.yml`` defines that reusable modules are stored in ``libs``.

In the next section we will use existing modules to deploy our LAMP stack.

Reuse existing modules
------------------------------

At GitHub, we host modules to setup and manage many systems. Our modules are available in the https://github.com/inmanta/ repositories.

When you use an import statement in your model, Inmanta downloads these modules and their dependencies automatically.

.. _qsconfigmodel:

The configuration model
------------------------------

In this section we will use the configuration concepts defined in the existing modules to set up Drupal on the host named ``vm1``.

First, create a new ``main.cf`` file or execute ``git checkout single_machine``:


.. code-block:: inmanta
    :linenos:

    import ip
    import redhat
    import redhat::epel
    import apache
    import mysql
    import web
    import drupal

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::centos7, ip="192.168.33.101", remote_agent=true,
                 remote_user="vagrant")

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
* Line 9 defines on which machine we want to deploy Drupal.

 * The *name* attribute is the host name of the machine, which is later used to determine what configuration needs to be deployed on which machine.
 * The *os* attribute defines which operating system this server runs. This is used to select the right tools (yum or dnf or apt).
 * The *ip* attribute is the IP address of this host. At this moment we define this attribute manually, later in the tutorial we let Inmanta discover this automatically.

* Lines 12 and 13 deploy an Apache server and MySQL server on our host.
* Line 16 defines the name (host name) of the web application.
* Lines 17-18 define a database for our Drupal website.
* Lines 19-20 define the actual Drupal application.



Deploy the configuration model
-------------------------------

To deploy the project, we must first register it with the management server, by creating a project and an environment. A project is a collection of related environments. (e.g. development, testing, production, qa,...)
An environment is associated with a branch in a git repository. This allows the server to recompile the model when the environment changes.

.. code-block:: sh

    inmanta-cli project create -n test
    inmanta-cli environment create -n quickstart-env -p test -r https://github.com/inmanta/quickstart.git -b master --save

.. note::

    The ``--save`` option tells ``inmanta-cli`` to store the environment config in the ``.inmanta`` file. The compiler uses this file to find the server and to export to the right environment.

Then compile the project and send it to the server:

.. code-block:: sh

    inmanta -vvv  export -d

The first time you run this command may take a while, as all dependencies are downloaded.

When the model is sent to the server, it will start deploying the configuration.
To track progress, you can go to the `dashboard <http://127.0.0.1:8888>`_.

.. note::

    The ``-vvv`` option sets the output of the compiler to very verbose.
    The ``-d`` option instructs the server to immediately start the deploy.

Accessing your new Drupal server
----------------------------------

When the installation is done, you can access your new Drupal server at `http://localhost:8080/ <http://localhost:8080/>`_.


Multi-machine deployment using the CLI
=======================================

The real power of Inmanta appears when you want to manage more than one machine. In this section we will
move the MySQL server from ``vm1`` to a second virtual machine called ``vm2``.


Update the configuration model
------------------------------

A second virtual machine is easily added to the system by adding the definition
of the virtual machine to the configuration model and assigning the MySQL server
to the new virtual machine. Update ``main.cf`` to the following:

.. code-block:: inmanta
    :linenos:

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::centos7, ip="192.168.33.101", remote_agent=true,
                 remote_user="vagrant")
    vm2=ip::Host(name="vm2", os=redhat::centos7, ip="192.168.33.102", remote_agent=true,
                 remote_user="vagrant")

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

To deploy the configuration model, compile the project and send it to the server:

.. code-block:: sh

    inmanta -vvv export -d


If you browse to the Drupal site again, the database should be empty once more.

.. note::

    When moving the database, a new database is created, thus the content of the old database is not migrated automatically.


.. _qsdashboard:

Using the dashboard
==========================

#. Go to the `dashboard <http://127.0.0.1:8888>`_.
#. Create a new project with the name ``test`` by clicking *Add new project*.
#. Go into the new project and create a new environment by clicking *Add new environment*:

    * Select the ``test`` project.
    * Give the environment a name, e.g. ``env-quickstart``.
    * Specify the repo: ``https://github.com/inmanta/quickstart``.
    * Specify the branch: ``master``.

#. Go into your new environment.
#. Press *Update & Recompile* (this may take a while, as all dependencies are downloaded).

    * Now the Inmanta server downloads the configuration model from GitHub. It also downloads all required modules (i.e. dependencies). These modules contain the instructions to install specific parts of the setup such as for example `mysql` or `drupal` itself. To see the source go `here <https://github.com/inmanta/quickstart>`_, for a more in-depth explanation :ref:`see above <qsconfigmodel>`.
    * When this is done, it compiles all modules and integrates them into a new deployment plan.

#. When the compilation is done, a new version appears. This contains the new deployment plan. Click on this version to open it. This shows a list of all configuration items in this configuration.
#. Press *Deploy* to start rolling out this version.

    * An agent is now started that remotely logs in into the virtual machines (via SSH) and starts deploying the Drupal server.
    * It will automatically install the required software and configure it properly.

#. When the deployment is done, you can find your freshly deployed Drupal instance at `http://localhost:8080/ <http://localhost:8080/>`_.


Create your own modules
_______________________

Inmanta enables developers of a configuration model to make it modular and
reusable. In this section we create a configuration module that defines how to
deploy a LAMP stack with a Drupal site in a two- or three-tiered deployment.

Module layout
==========================
A configuration module requires a specific layout:

    * The name of the module is determined by the top-level directory. Within this
      module directory, a ``module.yml`` file has to be specified.
    * The only mandatory subdirectory is the ``model`` directory containing a file
      called ``_init.cf``. What is defined in the ``_init.cf`` file is available in the namespace linked with
      the name of the module. Other files in the model directory create subnamespaces.
    * The ``files`` directory contains files that are deployed verbatim to managed
      machines.
    * The ``templates`` directory contains templates that use parameters from the
      configuration model to generate configuration files.
    * The ``plugins`` directory contains Python files that are loaded by the platform and can
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
==========================

In ``lamp/model/_init.cf`` we define the configuration model that defines the *lamp*
configuration module.

.. code-block:: inmanta
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

* Lines 7 to 13 define an entity which is the definition of a *concept* in the configuration model. On lines 8 to 12, typed attributes are defined which we can later on use in the implementation of an entity instance.
* Line 9 defines that *hostname* is an identifying attribute for instances of the DrupalStack entity. This also means that all instances of DrupalStack need to have a unique *hostname* attribute.
* Lines 17 and 18 define a relation between a Host and our DrupalStack entity. The first relation reads as follows:

    * Each DrupalStack instance has exactly one ip::Host instance that is available
      in the webhost attribute.
    * Each ip::Host has zero or one DrupalStack instances that use the host as a
      webserver. The DrupalStack instance is available in the drupal_stack_webhost attribute.

* On lines 20 to 31 an implementation is defined that provides a refinement of the DrupalStack entity. It encapsulates the configuration of a LAMP stack behind the interface of the entity by defining DrupalStack in function of other entities, which on their turn do the same. Inside the implementation the attributes and relations of the entity are available as variables.
* On line 33, the *implement* statement links the implementation to the entity.

The composition
==========================

With our new LAMP module we can reduce the amount of required configuration code in the ``main.cf`` file
by using more *reusable* configuration code. Only three lines of site-specific configuration code are
required.

.. code-block:: inmanta
    :linenos:

    import ip
    import redhat
    import redhat::epel
    import lamp

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::centos7, ip="192.168.33.101", remote_agent=true,
                 remote_user="vagrant")
    vm2=ip::Host(name="vm2", os=redhat::centos7, ip="192.168.33.102", remote_agent=true,
                 remote_user="vagrant")

    lamp::DrupalStack(webhost=vm1, mysqlhost=vm2, hostname="localhost", admin_user="admin",
                      admin_password="test", admin_email="admin@example.com", site_name="localhost")


Deploy the changes
==========================

Deploy the changes as before and nothing should change because it generates exactly the same
configuration.

.. code-block:: sh

    inmanta -vvv export -d


Next steps
___________________

:doc:`guides`
