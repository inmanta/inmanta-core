    .. vim: spell

Quickstart
***************

Inmanta is intended to manage complex infrastructures, often in the cloud or other virtualized environments.
In this guide we start simple and manage a 3-node CLOS network with a spine and two leaf switches. First we install `containerlab <https://containerlab.dev/>`_ and then configure `SR Linux <https://learn.srlinux.dev/>`_ containers using **Inmanta open source orchestrator** and ``gNMI``.


1. First, we use `Containerlab` to spin-up Inmanta server and its PostgreSQL database, then three `SR Linux` containers, connected in a CLOS like topology
2. After that, we configure IP addresses and OSPF on them using **Inmanta**.

.. note::

    This guide is meant to quickly set up an Inmanta LAB environment to experiment with.
    It is not recommended to run this setup in production, as it might lead to instabilities in the long term.


Prerequisites
----------------------------

**Python version 3.9**, ``Docker``, ``Containerlab`` and ``Inmanta`` need to be installed on your machine and our ``SR Linux`` repository has to be cloned in order to proceed. Please make sure to follow the links below to that end.

1. `Install Docker <https://docs.docker.com/install/>`_.
2. `Install Containerlab <https://containerlab.dev/install/>`_.
3. Prepare a development environment by creating a `python virtual environment` and installing Inmanta:

   .. code-block:: sh

       mkdir -p ~/.virtualenvs
       python3 -m venv ~/.virtualenvs/srlinux
       source ~/.virtualenvs/srlinux/bin/activate
       pip install inmanta

4. Clone the `SR Linux examples <https://github.com/inmanta/examples/tree/master/Networking/SR%20Linux>`_ repository:

   .. code-block:: sh

       git clone https://github.com/inmanta/examples.git


5. Change directory to `SR Linux` examples:

   .. code-block:: sh

      cd examples/Networking/SR\ Linux/


This folder contains a **project.yml**, which looks like this:

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
        - type: package
            url: https://packages.inmanta.com/public/quickstart/python/simple/
        install_mode: release
        requires:


- The ``modulepath`` setting defines that modules will be stored in ``libs`` directory.
- The ``repo`` setting points to one or more Git repositories containing Inmanta modules.
- The ``requires`` setting is used to pin versions of modules, otherwise the latest version is used.

1. Install the required modules inside the `SR Linux` folder:

   .. code-block:: sh

       inmanta project install

   .. note::

        should you face any errors at this stage, please contact us.


In the next sections we will showcase how to set up and configure ``SR Linux`` devices.


.. _lab:

Setting up the LAB
_________________________

Go to the `SR Linux` folder and then `containerlab` to spin-up the containers:

.. code-block:: sh

    cd examples/Networking/SR\ Linux/containerlab
    sudo clab deploy -t topology.yml

`Containerlab` will spin-up:

1. an `Inmanta` server
2. a `PostgreSQL` Database server
3. Three `SR Linux` network operating systems.


Depending on your system's horsepower, give them a few seconds/minutes to fully boot-up.


Connecting to the containers
______________________________

At this stage, you should be able to view the **Web Console** by navigating to:

http://172.30.0.3:8888/console

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

Create an Inmanta project and an environment
_____________________________________________

A project is a collection of related environments. (e.g. development, testing, production, qa,...). We need to have an environment to manage our infrastructure. An environment is a collection of resources, such as servers, switches, routers, etc.

There are **two ways** to create a project and an environment:

1. Using Inmanta CLI (**recommended**):
    .. code-block:: sh

        # Create a project called test
        inmanta-cli --host 172.30.0.3 project create -n test
        # Create an environment called SR_Linux
        inmanta-cli --host 172.30.0.3 environment create -p test -n SR_Linux --save


The first option, ``inmanta-cli``, will automatically create a ``.inmanta`` file that contains the required information about the server and environment ID. The compiler uses this file to find the server and to export to the right environment.


2. Using the Web Console: Connect to the Inmanta container http://172.30.0.3:8888/console, click on the `Create new environment` button, provide a name for the project and the environment then click `submit`.


If you have chosen the second option, the Web Console, you need to copy the environment ID for later use, either:

 - from the URL, e.g. ec05d6d9-25a4-4141-a92f-38e24a12b721 from the http://172.30.0.3:8888/console/desiredstate?env=ec05d6d9-25a4-4141-a92f-38e24a12b721.
 - or by clicking on the gear icon on the top right of the Web Console, then click on Environment, scroll down all the way to the bottom of the page and copy the environment ID.


Configuring SR Linux
_______________________________

There are a bunch of examples present inside the `SR Linux` folder of the `examples` repository that you have cloned in the previous step, setting up the lab_.

In this guide, we will showcase two examples on a small **CLOS** `topology <https://github.com/inmanta/examples/tree/master/Networking/SR%20Linux#sr-linux-topology>`_ to get you started:

1. `interface <https://github.com/inmanta/examples/blob/master/Networking/SR%20Linux/interfaces.cf>`_ configuration.
2. `OSPF <https://github.com/inmanta/examples/blob/master/Networking/SR%20Linux/ospf.cf>`_ configuration.

It could be useful to know that Inmanta uses the ``gNMI`` protocol to interface with ``SR Linux`` devices.

.. note::

    In order to make sure that everything is working correctly, run ``inmanta compile``. This will ensure that the modules are in place and the configuration is valid. If you face any errors at this stage, please contact us.


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
* Lines 34-40 instantiate the ``Ipv4`` object, link to the parent ``Subinterface`` object, set the IP address and prefix.


The rest of the configuration model follows the same method for ``leaf2`` and ``spine`` devices, with the only difference being the ``spine`` having two interfaces, subinterfaces and IP addresses.

Now, we can deploy the model by referring to `Deploy the configuration model`_ section.



SR Linux OSPF configuration
__________________________________

The `ospf.cf <https://github.com/inmanta/examples/blob/master/Networking/SR%20Linux/ospf.cf>`_ file contains the required configuration model to first set IP addresses on point-to-point interfaces between the ``spine``, ``leaf1`` and ``leaf2`` devices according to the `aforementioned topology <https://github.com/inmanta/examples/tree/master/Networking/SR%20Linux#sr-linux-topology>`_ and then configure ``OSPF`` between them.

This model build on top of the ``interfaces`` model that was discussed in `SR Linux interface configuration`_. It first `imports` the required packages, then configures ``interfaces`` on all the devices and after that, adds the required configuration model for ``OSPF``.


Let's have a look at the partial configuration model:


.. code-block:: inmanta
    :linenos:

    import srlinux
    import srlinux::interface as srinterface
    import srlinux::interface::subinterface as srsubinterface
    import srlinux::interface::subinterface::ipv4 as sripv4
    import srlinux::network_instance as srnetinstance
    import srlinux::network_instance::protocols as srprotocols
    import srlinux::network_instance::protocols::ospf as srospf
    import srlinux::network_instance::protocols::ospf::instance as srospfinstance
    import srlinux::network_instance::protocols::ospf::instance::area as srospfarea
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

    # |interface configuration| #

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

    # |network instance| #

    leaf1_net_instance = srlinux::NetworkInstance(
        device = leaf1,
        name = "default",
    )

    leaf1_net_instance_int1 = srnetinstance::Interface(
        parent_network_instance = leaf1_net_instance,
        name = "ethernet-1/1.0"
    )

    # |OSPF| #

    leaf1_protocols = srnetinstance::Protocols(
        parent_network_instance = leaf1_net_instance,
        ospf = leaf1_ospf
    )

    leaf1_ospf_instance = srospf::Instance(
            parent_ospf = leaf1_ospf,
            name = "1",
            router_id = "10.20.30.210",
            admin_state = "enable",
            version = "ospf-v2"
    )

    leaf1_ospf = srprotocols::Ospf(
        parent_protocols = leaf1_protocols,
        instance = leaf1_ospf_instance
    )

    leaf1_ospf_area = srospfinstance::Area(
        parent_instance = leaf1_ospf_instance,
        area_id = "0.0.0.0",
    )

    leaf1_ospf_int1 = srospfarea::Interface(
        parent_area = leaf1_ospf_area,
        interface_name = "ethernet-1/1.0",
    )


* Lines 1-10 import the required modules/packages.
* Lines 16-24 instantiate the device; ``GnmiDevice`` object and set the required parameters.
* Lines 28-33 instantiate the ``Interface`` object by selecting the parent interface, ``ethernet-1/1`` and setting the MTU to 9000.
* Lines 35-39 instantiate the ``Subinterface`` object, link to the parent interface object, set an `index` and link to the child ``Ipv4`` object.
* Lines 41-47 instantiate the ``Ipv4`` object, link to the parent ``Subinterface`` object, set the IP address and prefix.
* Lines 51-54 instantiate ``NetworkInstance`` object, set the name to ``default``.
* Lines 56-59 instantiate a network instance ``Interface`` object, link to the ``default`` network instance object and use ``ethernet-1/1.0`` as the interface.
* Lines 63-66 instantiate the ``Protocols`` object, link to the ``default`` network instance object and link to the ``OSPF`` object which we will create shortly.
* Lines 68-74 instantiate an OSPF instance and OSPF ``Instance``, link to the ``OSPF instance``, provide a name, router ID, admin state and version.
* Lines 76-79 instantiate an ``OSPF`` object, link to the ``Protocols`` object and link to the ``OSPF instance``.
* Lines 81-84 instantiate an ``Area`` object, link to the ``OSPF instance`` and provide the area ID.
* Lines 86-89 instantiate an area ``Interface`` object, link to the ``OSPF area`` object and activates the OSPF on ``ethernet-1/1.0`` interface.


The rest of the configuration model follows the same method for ``leaf2`` and ``spine`` devices, with the only difference being the ``spine`` having two interfaces, subinterfaces and IP addresses and OSPF interface configuration.

Now, we can deploy the model by referring to `Deploy the configuration model`_ section.



Deploy the configuration model
____________________________________

To deploy the project, we must first register it with the management server by creating a project and an environment. We have covered this earlier at `Create an Inmanta project and an environment`_ section.

Export the ``interafces`` configuration model to the Inmanta server:

.. code-block:: sh

    inmanta -vvv export -f interfaces.cf
    # or
    inmanta -vvv export -f interfaces.cf -d


Export the ``OSPF`` configuration model to the Inmanta server:

.. code-block:: sh

    inmanta -vvv export -f ospf.cf
    # or
    inmanta -vvv export -f ospf.cf -d


.. note::

    The ``-vvv`` option sets the output of the compiler to very verbose.
    The ``-d`` option instructs the server to immediately start the deploy.


When the model is sent to the server, it will start deploying the configuration.
To track progress, you can go to the `dashboard <http://172.30.0.3:8888/dashboard>`_, select the `test` project and then the `SR_Linux` environment and click on ``Resources`` tab on the left pane to view the progress.

When the deployment is complete, you can verify the configuration using the commands provided in `Verifying the configuration`_ section.


If the deployment fails for some reason, consult the
:ref:`troubleshooting page<troubleshooting>` to investigate the root cause of the issue.



Verifying the configuration
_____________________________

After a successful deployment, you can connect to ``SR Linux`` devices and verify the configuration.

Pick all or any of the devices you like, connect to them as discussed in `Connecting to the containers`_ section and check the configuration:

.. code-block:: sh

   show interface ethernet-1/1.0
   show network-instance default protocols ospf neighbor
   show network-instance default route-table ipv4-unicast summary
   info flat network-instance default



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



Update the configuration model
------------------------------

The provided configuration models can be easily modified to reflect your desired configuration. Be it a change in IP addresses or adding new devices to the model. All you need to do is to create a new or modify the existing configuration model, say ``interfaces.cf`` to introduce your desired changes.

For instance, let's change the IP address of interface ``ethernet-1/1.0`` to `100.0.0.1/24` in the `interfaces.cf` configuration file:


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
            ip_prefix = "100.0.0.1/24"
        )
    )


Additionally, you can add more SR Linux devices to the `topology.yml` file and explore the possible combinations.


Modify or Create your own modules
___________________________________

Inmanta enables developers of a configuration model to make it modular and reusable. We have made some videos that can walk you through the entire process in a short time.

Please check our `YouTube <https://www.youtube.com/playlist?list=PL8UgC-AkgG7ZfqzTBpBYh_Uiou8SsjHaW>`_ playlist to get started.


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
    |    |__ file1.txt
    |
    |__ model
    |    |__ _init.cf
    |    |__ services.cf
    |
    |__ plugins
    |    |__ functions.py
    |
    |__ templates
         |__ conf_file.conf.tmpl


Custom modules should be placed in the ``libs`` directory of the project.


Next steps
___________________

:doc:`model_developers`
