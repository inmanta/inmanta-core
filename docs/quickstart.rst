    .. vim: spell

Quickstart
***************

This tutorial gets you started with the Inmanta orchestration tool.

Inmanta is intended to manage complex infrastructures, often in the cloud or other virtualized environments.
In this guide, we go for a less complex setup: install the Drupal CMS on two VM-like containers.
First, we use Docker to set up a basic environment with two empty VM-like containers, an Inmanta server and a postgres server used by inmanta as a database.
Then, we use Inmanta to install Drupal on these VM-like containers.

.. note::

    This is meant to get an example Inmanta environment set up and running quickly to experiment with.
    It is not recommended to run this setup in production, as it might lead to instabilities in the long term.

.. _qsetup:

Setting up the tutorial
_________________________

To quickly get started with Inmanta, use Docker Compose to set up an environment to host the Inmanta server and some machines to be managed.
Before starting this tutorial, first `install Docker on your machine <https://docs.docker.com/install/>`_.
Next `install Docker Compose on your machine <https://docs.docker.com/compose/install/>`_.

Then, grab the Docker quickstart from our Git repository.

.. code-block:: sh

    git clone https://github.com/inmanta/quickstart-docker.git
    cd quickstart-docker

Now that we have the needed docker files, we will need to get the `Inmanta quickstart project <https://github.com/inmanta/quickstart>`_ itself:

.. code-block:: sh

    git clone https://github.com/inmanta/quickstart.git quickstart-project

The quickstart project can now be found under the newly created `quickstart-project` directory.
It will be the basis for this quickstart.
The ``quickstart-project`` directory will also be shared with the Inmanta server container
(mounted to ``/home/inmanta/quickstart-project``).
We will come back to the files in this repository later.

.. note::

    If you are on `Windows`, be sure you make the drive with the quickstart project shareable with docker containers:

    1. In Powershell: ``$env:COMPOSE_CONVERT_WINDOWS_PATHS = 1``
    2. Restart Docker for Windows
    3. Go to Docker for Windows settings > Shared Drives > Reset credentials > select drive with quickstart project > set your credentials > Apply

Finally, have Docker Compose deploy the quickstart environment:

.. code-block:: sh

    docker-compose up

Docker Compose will set up the Inmanta server, a postgres server and two VM-like containers to experiment on.
When Docker Compose is done deploying and the Inmanta server is running, you will be able to open the dashboard at http://127.0.0.1:8888.
When you see the following output, the Inmanta server is ready to be used:

.. code-block:: sh

    inmanta_quickstart_server | inmanta.protocol.rest    DEBUG   Start REST transport
    inmanta_quickstart_server | inmanta                  INFO    Server startup complete

.. note::

    docker-compose will lock the current terminal and use it for output from all 4 containers.
    You will need to open a new terminal to continue with this quickstart

To get an interactive shell on the Inmanta server (this will be needed later):

.. code-block:: sh

    docker exec -it "inmanta_quickstart_server" bash

.. note::

    The rest of the quickstart guide assumes commands are executed from the root path of the quickstart-docker Git repository, unless noted otherwise.

Breaking down/Resetting the quickstart-docker environment
=========================================================

To fully clean up or reset the environment, run the following commands:

.. code-block:: sh

    docker-compose down
    docker volume prune -f
    docker image rmi inmanta-agent inmanta-server

This will give you a clean environment next time you run ``docker-compose up``.

Automatically deploying Drupal
_______________________________

At this point, you can go through the quickstart guide in one of two ways: via the dashboard or via the command line interface.
For the CLI, go to the next section. For the Dashboard, go to :ref:`qsdashboard`.

.. _cli:

Single machine deployment using the CLI
=======================================

To start a new project, all you need is a directory with a project.yml file,
defining the parameters like location to search for modules and where to find the server.
In this case we will be using the premade quickstart project we cloned in to ``./quickstart-project`` earlier.

That directory contains a project.yml, which looks like this:

.. code-block:: yaml

    name: quickstart
    modulepath: libs
    downloadpath: libs
    repo: https://github.com/inmanta/
    description: A quickstart project that installs a drupal website.
    requires:
        - apache ~= 0.3.1
        - drupal ~= 0.7.1
        - exec ~= 1.1.0
        - ip ~= 1.0.0
        - logging ~= 0.4.1
        - mysql ~= 0.6.0
        - net ~= 0.5.0
        - php ~= 0.3
        - redhat ~= 0.8.0
        - std ~= 0.26.2
        - web ~= 0.2.2
        - yum ~= 0.5.1

The ``modulepath`` setting defines that reusable modules will be stored in ``libs``.
The ``repo`` setting points to one or more Git projects containing Inmanta modules in Git repositories.
The ``requires`` setting is used to pin versions of modules, otherwise the latest version is used.

In the next section we will use existing modules to deploy a LAMP stack.

Reusing existing modules
------------------------------

We host modules to set up and manage many systems on our Github. These are available under https://github.com/inmanta/.

When you use an import statement in your model, Inmanta downloads these modules and their dependencies when you run ``inmanta project install``.
V2 modules (See :ref:`moddev-module-v2`) need to be declared as Python dependencies in addition
to using them in an import statement. Some of our public modules are hosted in the v2 format on https://pypi.org/.


.. _qsconfigmodel:

The configuration model
------------------------------

In this section we will use the configuration concepts defined in the existing modules to set up Drupal on the host named ``vm1``.

First delete the contents of ``./quickstart-project/main.cf``, then put in the following:

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

    # add a mysql and apache http server
    web_server=apache::Server(host=vm1)
    mysql_server=mysql::Server(host=vm1, remove_anon_users=true)

    # deploy drupal in that virtual host
    name=web::Alias(hostname="localhost")
    db=mysql::Database(server=mysql_server, name="drupal_test", user="drupal_test", password="Str0ng-P433w0rd")
    drupal::Application(name=name, container=web_server, database=db, admin_user="admin",
                        admin_password="test", admin_email="admin@example.com",
                        site_name="localhost")


* Lines 1-7 import all the required packages.
* Line 10 defines on which machine we want to deploy Drupal.

    * The *name* attribute is the hostname of the machine, which is later used to determine what configuration needs to be deployed on which machine.
    * The *os* attribute defines which operating system this server runs. This is used to select the right tools (yum or dnf or apt).
    * The *ip* attribute is the IP address of this host. At this moment we define this attribute manually, later in this tutorial we let Inmanta discover this automatically.

* Line 13 deploys an Apache server on our host.
* Line 14 deploys a Mysql server on our host and removes its anonymous users.
* Line 17 defines the name (hostname) of the web application.
* Line 18 defines a database for our Drupal website.
* Lines 19-21 define the actual Drupal application.

Deploy the configuration model
-------------------------------

To deploy the project, we must first register it with the management server by creating a project and an environment. A project is a collection of related environments. (e.g. development, testing, production, qa,...)
An environment is associated with a branch in a git repository. This allows the server to recompile the model when the environment changes.

Connect to the terminal of the server-container:

.. code-block:: sh

    docker exec -it "inmanta_quickstart_server" bash

Then, create the inmanta project and environment:

.. code-block:: sh

    cd /home/inmanta/quickstart-project
    inmanta-cli project create -n test
    inmanta-cli environment create -n quickstart-env -p test -r https://github.com/inmanta/quickstart.git -b master --save

.. note::

    The ``--save`` option tells ``inmanta-cli`` to store the environment config in the ``.inmanta`` file. The compiler uses this file to find the server and to export to the right environment.

Install all module dependencies into the project:

.. code-block:: sh

    inmanta project install

Finally compile the project and deploy it:

.. code-block:: sh

    inmanta -vvv  export -d

When the model is sent to the server, it will start deploying the configuration.
To track progress, you can go to the `dashboard <http://127.0.0.1:8888>`_, select the `test` project and then the
`quickstart-env` environment. When the deployment fails for some reason, consult the
:ref:`troubleshooting page<troubleshooting>` to investigate the root cause of the issue.

.. note::

    The ``-vvv`` option sets the output of the compiler to very verbose.
    The ``-d`` option instructs the server to immediately start the deploy.

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
==========================

Inmanta can deploy from the server using only the dashboard. All changes have to go through the repository in this case.

#. Clone the quickstart project on github (or to another repository location).
#. Go to the `dashboard <http://127.0.0.1:8888>`_.
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
