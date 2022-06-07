    .. vim: spell

Quickstart
***************

Inmanta is intended to manage complex infrastructures, often in the cloud or other virtualized environments.
In this guide, we go for a less complex setup: Installing `containerlab <https://containerlab.dev/>`_ and configuring `SR Linux <https://learn.srlinux.dev/>`_ containers using **Inmanta service orchestrator** and ``gNMI``.


1. First, we use `Containerlab` to spin-up Inmanta server and its PostgreSQL database, then three `SR Linux` containers, connected in a CLOS like topology
2. After that, we configure IP addresses and OSPF on them using **Inmanta**.

.. note::

    This guide is meant to quickly set up an Inmanta LAB environment to experiment with.
    It is not recommended to run this setup in production, as it might lead to instabilities in the long term.


Prerequisites
----------------------------

``Docker``, ``Containerlab`` and ``Inmanta`` need to be installed on your machine and our ``SR Linux`` repository has to be cloned in order to proceed. Please make sure to follow the links below to that end.

1. `Install Docker <https://docs.docker.com/install/>`_.
2. `Install Containerlab <https://containerlab.dev/install/>`_.
3. Prepare a development environment by creating a `python virtual environment` and installing Inmanta:

   .. code-block:: sh

       mkdir -p ~/.virtualenvs
       python3 -m venv ~/.virtualenvs/srlinux
       source ~/.virtualenvs/srlinux/bin/activate
       pip install inmanta-core

4. Clone the `SR Linux examples <https://github.com/inmanta/examples/tree/master/Networking/SR%20Linux>`_ repository:

   .. code-block:: sh

       git clone https://github.com/inmanta/examples.git


The cloned repository contains a **project.yml**, which looks like this:

    .. code-block:: yaml

        name: SR Linux Examples
        description: Provides examples for the SR Linux module
        author: Inmanta
        author_email: code@inmanta.com
        license: ASL 2.0
        copyright: 2022 Inmanta
        modulepath: libs
        downloadpath: libs
        repo:
            - https://github.com/inmanta/
        install_mode: release
        requires:


The ``modulepath`` setting defines that modules will be stored in ``libs`` directory.
The ``repo`` setting points to one or more Git repositories containing Inmanta modules.
The ``requires`` setting is used to pin versions of modules, otherwise the latest version is used.

5. Install the required modules:

   .. code-block:: sh

       cd Networking/SR\ Linux/
       inmanta project install

   .. note::

        should you face any errors at this stage, please contact us.


In the next sections we will showcase how to set up and configure ``SR Linux`` devices.


.. _lab:

Setting up the LAB
_________________________

Go to the `SR Linux` folder and then `containerlab` to spin-up the containers:

.. code-block:: sh

    cd Networking/SR\ Linux/containerlab
    sudo clab deploy -t topology.yml

`Containerlab` will spin-up:

1. an `Inmanta` server
2. a `PostgreSQL` Database server
3. Three `SR Linux` network operating systems.


Depending on your system's horsepower, give them a few seconds/minutes to fully boot-up.


Connecting to the containers
______________________________

At this stage, you should be able to view the **Web Console** by navigating to:

http://172.30.0.3:8888/dashboard

To get an interactive shell to the Inmanta server:

.. code-block:: sh

    docker exec -it clab-srlinux-inmanta-server /bin/bash


In order to connect to `SR Linux` containers, there are two options:

1. Using Docker:

.. code-block:: sh

    docker exec -it clab-srlinux-spine sr_cli
    # or
    docker exec -it clab-srlinux-leaf1 sr_cli
    # or
    docker exec -it clab-srlinux-leaf2 sr_cli


2. Using SSH (username and password is `admin`):

.. code-block:: sh

   ssh admin@clab-srlinux-spine
   ssh admin@clab-srlinux-leaf1
   ssh admin@clab-srlinux-leaf2

Then enter the `configuration mode` by typing:

.. code-block:: sh

    enter candidate

The output should look something like this:

.. code-block::

    Welcome to the srlinux CLI.
    Type 'help' (and press <ENTER>) if you need any help using this.


    --{ running }--[  ]--
    A:spine#

Exit the session by typing:

.. code-block:: sh

    quit

Now that we have the needed containers, we will need to go up a directory where the project files exist:

.. code-block:: sh

    cd ..

.. note::

    The rest of the this guide assumes commands are executed from the root path of the `SR Linux` folder, unless noted otherwise.


.. _inenv:

Create an Inmanta environment
_______________________________

We need to have an environment to manage our infrastructure. An environment is a collection of resources, such as servers, switches, routers, etc.

There are two ways to create a project and an environment:

1. Using Inmanta CLI (**recommended**):
    .. code-block:: sh

        inmanta-cli --host 172.30.0.3 project create -n test
        inmanta-cli --host 172.30.0.3 environment create -p test -n SR_Linux --save

2. Using the Web Console: Connect to the Inmanta container http://172.30.0.3:8888/dashboard, click on the `Create new environment` button, provide a name for the project and the environment then click `submit`.

The first option, ``inmanta-cli``, will automatically create a ``.inmanta`` file that contains the required information about the server and environment ID. The compiler uses this file to find the server and to export to the right environment.


If you have chosen the second option; the Web Console, you need to copy the environment ID for later use, either:

 - from the URL, e.g. ec05d6d9-25a4-4141-a92f-38e24a12b721 from the http://172.30.0.3:8888/console/desiredstate?env=ec05d6d9-25a4-4141-a92f-38e24a12b721.
 - or by clicking on the gear icon on the top right of the Web Console, then click on Environment, scroll down all the way to the bottom of the page and copy the environment ID.


Configuring SR Linux
_______________________________

There are a bunch of examples present inside the `SR Linux` folder of the `examples` repository that you have cloned in the previous step, setting up the lab_.

In this guide, we will showcase two examples on a small **CLOS** `topology <https://github.com/inmanta/examples/tree/master/Networking/SR%20Linux#sr-linux-topology>`_ to get you started:

1. `interface <https://github.com/inmanta/examples/blob/master/Networking/SR%20Linux/interfaces.cf>`_ configuration.
2. `OSPF <https://github.com/inmanta/examples/blob/master/Networking/SR%20Linux/ospf.cf>`_ configuration.

It could be useful to know **Inmanta** uses ``gNMI`` protocol to interface with ``SR Linux`` devices.

.. note::

    In order to make sure that everything is working correctly, run ``inmanta compile -f main.cf``. This will ensure that the modules are in place and the configuration is valid. If you face any errors at this stage, please contact us.


SR Linux interface configuration
__________________________________

The `interfaces.cf <https://github.com/inmanta/examples/blob/master/Networking/SR%20Linux/interfaces.cf>`_ file contains the required configuration model to set IP addresses on point-to-point interfaces between the ``spine``, ``leaf1`` and ``leaf2`` devices according to the `aforementioned topology <https://github.com/inmanta/examples/tree/master/Networking/SR%20Linux#sr-linux-topology>`_.

Let's have a look at the partial configuration model:


.. code-block:: inmanta
    :linenos:

    import srlinux
    import srlinux::interface as srinterface
    import srlinux::interface::subinterface as srsubinterface
    import srlinux::interface::subinterface::ipv4 as sripv4
    import yang



    ######## Leaf 1 ########

    leaf1 = srlinux::GnmiDevice(
        auto_agent = true,
        name = "leaf1",
        mgmt_ip = "172.30.0.210",
        yang_credentials = yang::Credentials(
            username = "admin",
            password = "admin"
        )
    )

    leaf1_eth1 = srlinux::Interface(
        device = leaf1,
        name = "ethernet-1/1",
        mtu = 9000,
        subinterface = [leaf1_eth1_subint]
    )

    leaf1_eth1_subint = srinterface::Subinterface(
        parent_interface = leaf1_eth1,
        x_index = 0,
        ipv4 = leaf1_eth1_subint_address
    )

    leaf1_eth1_subint_address = srsubinterface::Ipv4(
        parent_subinterface = leaf1_eth1_subint,
        address = sripv4::Address(
            parent_ipv4 = leaf1_eth1_subint_address,
            ip_prefix = "10.10.11.2/30"
        )
    )


* Lines 1-5 import the required modules/packages.
* Lines 11-19 instantiate the device; ``GnmiDevice`` object and set the required parameters.
* Lines 21-26 instantiate the ``Interface`` object by selecting the parent interface, ``ethernet-1/1`` and setting the MTU to 9000.
* Lines 28-32 instantiate the ``Subinterface`` object, link to the parent interface object, set an `index` and link to the child ``Ipv4`` object.
* Lines 34 to 40 instantiate the ``Ipv4`` object, link to the parent ``Subinterface`` object, set the IP address and prefix.


The rest of the configuration model follows the same method for ``leaf2`` and ``spine`` devices, with the only difference being the ``spine`` having two interfaces, subinterfaces and IP addresses.


Deploy the interfaces configuration
____________________________________

To deploy the project, we must first register it with the management server by creating a project and an environment. A project is a collection of related environments. (e.g. development, testing, production, qa,...). We have covered this earlier at `Create an Inmanta environment`_ section.

Export the configuration model to the Inmanta server:

.. code-block:: sh

    inmanta -vvv export interfaces.cf

Then, head to the ``resources`` page on the Web Console to view the progress.


When the model is sent to the server, it will start deploying the configuration.
To track progress, you can go to the `dashboard <http://172.30.0.3:8888/dashboard>`_, select the `test` project and then the
`quickstart-env` environment. When the deployment fails for some reason, consult the
:ref:`troubleshooting page<troubleshooting>` to investigate the root cause of the issue.

.. note::

    The ``-vvv`` option sets the output of the compiler to very verbose.
    The ``-d`` option instructs the server to immediately start the deploy.


Resetting the LAB environment
_______________________________________________

To fully clean up or reset the LAB, go to the **containerlab** folder and run the following commands:

.. code-block:: sh

    cd containerlab
    sudo clab destroy -t topology.yml

This will give you a clean LAB the next time you run:

.. code-block:: sh

    sudo clab deploy -t topology.yml --reconfigure






Reusing existing modules
------------------------------

We host modules to set up and manage many systems on our Github. These are available under https://github.com/inmanta/.

When you use an import statement in your model, Inmanta downloads these modules and their dependencies when you run ``inmanta project install``.
V2 modules (See :ref:`moddev-module-v2`) need to be declared as Python dependencies in addition
to using them in an import statement. Some of our public modules are hosted in the v2 format on https://pypi.org/.



Accessing your new Drupal server
----------------------------------

When the installation is done, you can access your new Drupal server at `http://localhost:8080/ <http://localhost:8080/>`_.


Multi-machine deployment using the CLI
=======================================

The real power of Inmanta becomes apparent when managing more than one machine. In this section we will
move the MySQL server from ``vm1`` to a second machine called ``vm2``.


Update the configuration model
------------------------------

A second machine is easily added to the system by adding the definition
of the machine to the configuration model and assigning the MySQL server
to the new machine.

Update ``main.cf`` to the following:

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
    vm1=ip::Host(name="vm1", os=redhat::centos7, ip="172.28.0.4", remote_agent=true, remote_user="root")
    vm2=ip::Host(name="vm2", os=redhat::centos7, ip="172.28.0.5", remote_agent=true, remote_user="root")

    # add a mysql and apache http server
    web_server=apache::Server(host=vm1)
    mysql_server=mysql::Server(host=vm2)

    # deploy drupal in that virtual host
    name=web::Alias(hostname="localhost")
    db=mysql::Database(server=mysql_server, name="drupal_test", user="drupal_test", password="Str0ng-P433w0rd")
    drupal::Application(name=name, container=web_server, database=db, admin_user="admin",
                        admin_password="test", admin_email="admin@example.com", site_name="localhost")

On line 11 the definition of the new machine is added. On line 15 the
MySQL server is assigned to vm2.

Deploy the configuration model
------------------------------

To deploy the configuration model, compile the project and deploy it.
In the Inmanta server container terminal:

.. code-block:: sh

    inmanta -vvv export -d


If you browse to the Drupal site again, the database should be empty once more. When the deployment fails for some reason,
consult the :ref:`troubleshooting page<troubleshooting>` to investigate the root cause of the issue.

.. note::

    When moving the database, a new database is created and the content of the old database is not migrated automatically.

.. _qsdashboard:

Using the dashboard
------------------------------

Inmanta can deploy from the server using only the dashboard. All changes have to go through the repository in this case.

#. Clone the quickstart project on github (or to another repository location).
#. Go to the `dashboard <http://127.0.0.1:8888/dashboard>`_.
#. Create a new project with the name ``test`` by clicking *Add new project*.
#. Go into the new project and create a new environment by clicking *Add new environment*:

    * Select the ``test`` project.
    * Give the environment a name, e.g. ``env-quickstart``.
    * Specify the repo: for example ``https://github.com/user/quickstart``.
    * Specify the branch: ``master``.

#. Checkout your clone of the quickstart repository and make changes to the main.cf file, for example add the contents
   of single_machine.cf to the main.cf file. Commit the changes and push them to your repository.
#. Go into your new environment.
#. Press *Update & Recompile* (this may take a while, as all dependencies are downloaded).

    * Now the Inmanta server downloads the configuration model from your clone of the repository. It also downloads all required
      modules (i.e. dependencies). These modules contain the instructions to install specific parts of the setup such as for
      example `mysql` or `drupal` itself. To see the source go `here <https://github.com/inmanta/quickstart>`_, for a more
      in-depth explanation :ref:`see above <qsconfigmodel>`.
    * When this is done, it compiles all modules and integrates them into a new deployment plan.

#. When the compilation is done, a new version appears. This contains the new deployment plan. Click on this version to open it.
   This shows a list of all configuration items in this configuration.
#. Press *Deploy* to start rolling out this version.

    * An agent is now started that remotely logs in into the virtual machines (via SSH) and starts deploying the Drupal server.
    * It will automatically install the required software and configure it properly.

#. When the deployment is done, you can find your freshly deployed Drupal instance at `http://localhost:8080/ <http://localhost:8080/>`_.


Create your own modules
________________________

Inmanta enables developers of a configuration model to make it modular and
reusable. In this section we will create a configuration module that defines how to
deploy a LAMP stack with a Drupal site in a two- or three-tiered deployment.

.. note::
    This section describes how to create a v1 module. To create a v2 module instead see :ref:`module-creation-guide` and
    :ref:`moddev-module-v2`. Note that a v2 module can only depend on other v2 modules.


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

    mkdir ./quickstart-project/libs/{lamp,lamp/model}
    touch ./quickstart-project/libs/lamp/model/_init.cf
    touch ./quickstart-project/libs/lamp/module.yml

.. note::

    Running into permission errors at this point is normal if you followed the cli version of the quickstart.
    The best way to resolve these is to ``sudo mkdir ./quickstart-project/libs/lamp`` and then ``sudo chmod -R 777 ./quickstart-project/libs/lamp``.
    Now run the above commands again.

Next, edit the ``./quickstart-project/libs/lamp/module.yml`` file and add meta-data to it:

.. code-block:: yaml

    name: lamp
    license: Apache 2.0
    version: 0.1


Configuration model
==========================

In ``./quickstart-project/libs/lamp/model/_init.cf`` we define the configuration model that defines the *lamp*
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

    DrupalStack.webhost [1] -- ip::Host
    DrupalStack.mysqlhost [1] -- ip::Host

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
* Line 15 defines that *hostname* is an identifying attribute for instances of the DrupalStack entity. This also means that all instances of DrupalStack need to have a unique *hostname* attribute.
* Lines 17 and 18 define a relation between a Host and our DrupalStack entity. The first relation reads as follows:

    * Each DrupalStack instance has exactly one ip::Host instance that is available
      in the webhost attribute.
    * Each ip::Host has zero or one DrupalStack instances that use the host as a
      webserver. The DrupalStack instance is available in the drupal_stack_webhost attribute.

* On lines 20 to 31 an implementation is defined that provides a refinement of the DrupalStack entity. It encapsulates the configuration of a LAMP stack behind the interface of the entity by defining DrupalStack in function of other entities, which on their turn do the same. Inside the implementation the attributes and relations of the entity are available as variables.
* On line 33, the *implement* statement links the implementation to the entity.

The composition
==========================

With our new LAMP module we can reduce the amount of required configuration code in the ``./quickstart-project/main.cf`` file
by using more *reusable* configuration code. Only three lines of site-specific configuration code are required.

.. code-block:: inmanta
    :linenos:

    import ip
    import redhat
    import redhat::epel
    import lamp

    # define the machine we want to deploy Drupal on
    vm1=ip::Host(name="vm1", os=redhat::centos7, ip="172.28.0.4", remote_agent=true, remote_user="root")
    vm2=ip::Host(name="vm2", os=redhat::centos7, ip="172.28.0.5", remote_agent=true, remote_user="root")

    lamp::DrupalStack(webhost=vm1, mysqlhost=vm2, hostname="localhost", admin_user="admin",
                      admin_password="test", admin_email="admin@example.com", site_name="localhost")


Deploy the changes
==========================

Deploy the changes as before, by connection to the servers terminal.
Nothing will change because the generated configuration should be exactly the same.

.. code-block:: sh

    inmanta -vvv export -d

When the deployment fails for some reason, consult the :ref:`troubleshooting page<troubleshooting>` to investigate the root
cause of the issue.

Next steps
___________________

:doc:`model_developers`
