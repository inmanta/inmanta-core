.. _upgrading_the_orchestrator:


Upgrading the orchestrator
--------------------------

Upgrading the orchestrator can be done either in-place or by setting up a new orchestrator next to the old one
and migrating the state from the old to the new instance. The sections below describe the upgrade procedure
for each of both situations. These procedures can be used for major and non-major version upgrades.

.. note::

    Make sure to read the new version's changelog for any version specific upgrade notes, before
    proceeding with any of the upgrade procedures mentioned below.

Upgrading the orchestrator in-place
###################################

This section describes how to upgrade an orchestrator in-place.

.. note::
    **Pre-requisite**

    - Before upgrading the orchestrator to a new major version, make sure the old orchestrator is at the latest version available within its major.
    - Upgrades should be done one major version at a time. Upgrading from major
      version :code:`X` to major version :code:`X+2`, should be done by upgrading from :code:`X` to :code:`X+1` and then from :code:`X+1` to :code:`X+2`.
    - Make sure the PostgreSQL version of the database meets the requirements of the new major version of the orchestrator
      and make sure to update it if required. The required version can be found in the compatibility page of the Inmanta documentation
      for the new major version of the orchestrator.


1. Halt all environments (by pressing the ``STOP`` button in the web-console for each environment).
2. Create a backup of the database:

   .. tab-set::

       .. tab-item:: RPM-based installation

           .. code-block:: bash

               pg_dump -U <db_user> -W -h <host> <db_name> > <db_dump_file>

       .. tab-item:: Container-based installation

           .. code-block:: bash

               # Write the dump into the filesystem of the container
               podman exec -it inmanta-db pg_dump -U <db_user> -W -h localhost -f /tmp/inmanta.sql <db_name>
               # Copy the dump to the filesystem of the host
               podman cp inmanta-db:/tmp/inmanta.sql .


3. Update the artifact repository to the repository for the new major release:

   .. tab-set::

       .. tab-item:: RPM-based installation

           If you are doing an upgrade to a new major version, replace the content of the ``/etc/yum.repos.d/inmanta.repo`` file
           with the content for the new ISO version. This information can be obtained from the
           :ref:`installation documentation page<install-server>` for the new ISO version.

       .. tab-item:: Container-based installation

           Replace the image tag in ``/home/inmanta/.config/containers/systemd/inmanta-server.image`` with
           the one for the new ISO version. This information can be obtained from the
           :ref:`installation documentation page<install-server-with-podman>` for the new ISO version.

4. Upgrade the Inmanta server by running the following command(s). It might take some time before the
   orchestrator goes up, as some database migrations will be done.

   .. tab-set::

       .. tab-item:: RPM-based installation

           .. code-block:: bash

               sudo dnf update inmanta-service-orchestrator-server

       .. tab-item:: Container-based installation

           .. code-block:: bash

               systemctl --user daemon-reload
               systemctl --user restart inmanta-server-image.service
               systemctl --user restart inmanta-server.service

5. When accessing the web console, all the environments will be visible, and still halted.
6. One environment at a time:

   a. In the **Desired State** page of the environment, click ``Update project & recompile``, accessible via the
   dropdown of the ``Recompile`` button. (``/console/desiredstate?env=<your-env-id>``).

   b. Resume the environment by pressing the green ``Resume`` button in the bottom left corner of the console.

   .. warning::

       Make sure the compilation has finished and was successful.


Upgrading by migrating from one orchestrator to another orchestrator
#######################################################################

This document describes how to upgrade to a new version of the orchestrator by setting
up a new orchestrator next to the existing orchestrator and migrating all the state from
the existing to the new orchestrator. This procedure should be followed when an in-place
upgrade of the orchestrator is not possible e.g. when the operating system needs to be
upgraded alongside the orchestrator.

Terminology
+++++++++++

The procedure below describes how to migrate from one running orchestrator
denoted as the 'old orchestrator' to another one denoted as the 'new orchestrator'.

Procedure
+++++++++


.. note::
    **Pre-requisite**

    - Before upgrading the orchestrator to a new major version, make sure the old orchestrator is at the latest version available within its major.
    - Upgrades should be done one major version at a time. Upgrading from major
      version :code:`X` to major version :code:`X+2`, should be done by upgrading from :code:`X` to :code:`X+1` and then from :code:`X+1` to :code:`X+2`.


1. **[New Orchestrator]**: Make sure the desired version of the orchestrator is installed, by following the
   installation instructions (see :ref:`RPM installation<install-server>` or :ref:`container-based installation<install-server-with-podman>`) and set up a project to validate that the orchestrator is configured correctly (config, credentials, access to packages, etc.).
2. **[Old Orchestrator]** Halt all environments (by pressing the ``STOP`` button in the web-console for each environment).
3. **[Old Orchestrator]** Stop and disable the server:

   .. tab-set::

       .. tab-item:: RPM-based installation

           .. code-block:: bash

               sudo systemctl disable --now inmanta-server.service

       .. tab-item:: Container-based installation

           Make sure that the following section is not part of the
           ``/home/inmanta/.config/containers/systemd/inmanta-server.container`` file to prevent it from starting at boot.

           .. code-block:: systemd

               [Install]
               WantedBy=default.target

           Activate the new config and stop the server.

           .. code-block:: bash

               systemctl --user daemon-reload
               systemctl --user stop inmanta-server.service


4. **[Old Orchestrator]** Make a dump of the server database using ``pg_dump``.

   .. tab-set::

       .. tab-item:: RPM-based installation

          .. code-block:: bash

              pg_dump -U <db_user> -W -h <host> -f <db_dump_file> <db_name>

       .. tab-item:: Container-based installation

           .. code-block:: bash

               # Write the dump into the filesystem of the container
               podman exec -it inmanta-db pg_dump -U <db_user> -W -h localhost -f /tmp/inmanta.sql <db_name>
               # Copy the dump to the filesystem of the host
               podman cp inmanta-db:/tmp/inmanta.sql .


5. **[New Orchestrator]** Make sure the server is stopped:

   .. tab-set::

       .. tab-item:: RPM-based installation

           .. code-block:: bash

               sudo systemctl stop inmanta-server.service

       .. tab-item:: Container-based installation

           .. code-block:: bash

               systemctl --user stop inmanta-server.service


6. **[New Orchestrator]** Drop the inmanta database and recreate it:


   .. tab-set::

       .. tab-item:: RPM-based installation

           .. code-block:: bash

               # drop the database
               psql -h <host> -U <db_user> -W -c "drop database <db_name>;" postgres

               # re-create it
               sudo -u postgres -i bash -c "createdb -O <db_user> <db_name>"

       .. tab-item:: Container-based installation

           .. code-block:: bash

               # drop the database
               podman exec -it inmanta-db psql -U <db_user> -W -h localhost -c "drop database <db_name>;" postgres

               # re-create it
               podman exec -it inmanta-db bash -c "createdb -U <db_user> -h localhost -W -O <db_user> <db_name>"


7. **[New Orchestrator]** Load the dump of the server database using ``psql``.


   .. tab-set::

       .. tab-item:: RPM-based installation

           .. code-block:: bash

               psql -U <db_user> -W -h <host> -f <db_dump_file> <db_name>

       .. tab-item:: Container-based installation

           .. code-block:: bash

               podman cp <db_dump_file> inmanta-db:/tmp
               podman exec -it inmanta-db psql -U <db_user> -W -h localhost -f /tmp/<db_dump_file> <db_name>


8. **[New Orchestrator]** Start the orchestrator service, it might take some time before the orchestrator goes up, as some database migration will be done:

   .. tab-set::

       .. tab-item:: RPM-based installation

           .. code-block:: bash

               sudo systemctl enable --now inmanta-server.service

       .. tab-item:: Container-based installation

           Make sure that the following section is part of the
           ``/home/inmanta/.config/containers/systemd/inmanta-server.container`` file to make the server start at boot.

           .. code-block:: systemd

               [Install]
               WantedBy=default.target

           Activate the new config and start the server.

           .. code-block:: bash

               systemctl --user daemon-reload
               systemctl --user start inmanta-server.service


9. **[New Orchestrator]** When accessing the web console, all the environments will be visible, and still halted.
10. **[New Orchestrator]** One environment at a time:

    a. In the **Desired State** page of the environment, click ``Update project & recompile``, accessible via the
    dropdown of the ``Recompile`` button. (``/console/desiredstate?env=<your-env-id>``).

    b. Resume the environment by pressing the green ``Resume`` button in the bottom left corner of the console.

    .. warning::

        Make sure the compilation has finished and was successful.

