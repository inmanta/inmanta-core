Migrating from RPM's to containers
##################################

This page explains how an RPM-based installation of the Inmanta orchestrator can be migrated in-place to a container-based installation. The procedure below assumes you are running as the root user.

1. Shutdown the orchestrator that was installed from RPM.

   .. code-block::

      $ systemctl disable --now inmanta-server

2. Follow the procedure on :ref:`how to install Inmanta using Podman and Systemd (root setup)<install-server-with-podman>`. Ignore the part about adding the database container. We will make the new container-based installation connect to the same database that was used by the RPM-based installation. Also don't start the orchestrator yet. We will first apply some configuration changes in the next steps.
3. Copy the ``/etc/sysconfig/inmanta-server`` file to ``/var/lib/inmanta/.config/inmanta.env`` and add the following line to the ``[Container]`` section of ``~/.config/containers/systemd/inmanta-orchestrator-server.container`` file. This will make sure that the Inmanta orchestrator in the container has access to the environent variables defined in this file.

   .. code-block::

      EnvironmentFile=/var/lib/inmanta/.config/inmanta.env

4. Add a podman volume for the configuration files that are currently present in ``/etc/inmanta``.

   * Create a new podman volume with the name ``inmanta-server-config``:

     .. code-block::

        $ sudo -i -u inmanta -- podman volume create inmanta-server-config

   * Add the config files from ``/etc/inmanta`` into the volume ``inmanta-server-config``:

     * Enter the user namespace and mount the ``inmanta-server-config`` volume. The mount command returns the path where the volume is mounted.

       .. code-block::

          $ sudo -i -u inmanta -- podman unshare
          $ podman volume mount inmanta-server-config

     * Copy the files in ``/etc/inmanta`` into the volume by executing the following command. Replace ``<mount-dir>`` with
       the directory returned by the mount command:

       .. code-block::

          $ cp -r /etc/inmanta/* <mount-dir>

     * If the database server is running directly on the machine hosting the podman container, update the ``database.host`` config option in the ``database.cfg`` file to ``host.containers.internal``:

       .. code-block::

          $ vim <mount-dir>/inmanta.d/database.cfg

     * Unmount the ``inmanta-server-config`` volume again and leave the user namespace:

       .. code-block::

          $ podman volume unmount inmanta-server-config
          $ exit

5. (Optional) If configuration was added to the ``/var/lib/inmanta/.ssh`` directory, migrate it to the ``inmanta-server-data`` volume:

   * Create a new podman volume with the name ``inmanta-server-data``:

     .. code-block::

        $ sudo -i -u inmanta -- podman volume create inmanta-server-data

   * Enter the user namespace and mount the ``inmanta-server-data`` volume. The mount command returns the path where the volume is mounted.

     .. code-block::

        $ sudo -i -u inmanta -- podman unshare
        $ podman volume mount inmanta-server-data

   * Copy the files in ``/var/lib/inmanta/.ssh`` into the volume by executing the following command. Replace ``<mount-dir>`` with
     the directory returned by the mount command:

     .. code-block::

        $ cp -r /var/lib/inmanta/.ssh <mount-dir>

   * Unmount the ``inmanta-server-data`` volume again and leave the user namespace:

     .. code-block::

        $ podman volume unmount inmanta-server-data
        $ exit

6. Remove the volumes for the license and entitlement files, defined in the ``[Container]`` section of ``~/.config/containers/systemd/inmanta-orchestrator-server.container`` file and replace them with the following line that mounts the ``inmanta-server-config`` volume at ``/etc/inmanta`` in the container:

   .. code-block::

      Volume=inmanta-server-config:/etc/inmanta

7. (Optional) If the database server is running directly on the machine hosting the podman container:

   * Add the following line to the ``[Container]`` section of ``~/.config/containers/systemd/inmanta-orchestrator-server.container`` file. This makes sure that the host machine can be reference using the name ``host.containers.internal``.

     .. code-block::

        PodmanArgs=--add-host=host.containers.internal:host-gateway

   * Update the ``listen_addresses`` setting in the ``/var/lib/pgsql/data/postgresql.conf`` file to make the database server listen on the public interface of the host.
   * Add the following line to the ``/var/lib/pgsql/data/pg_hba.conf`` file to allow clients to login to the database from the public interface of the host. Replace ``<public-ip>`` with the public IP address of the host.

     .. code-block::

        host    all             all             <public-ip>/32               md5

8. Remove the ``INMANTA_DATABASE_*`` environment variables from ``~/.config/containers/systemd/inmanta-orchestrator-server.container`` file. These are not required because the inmanta server will read the database configuration from the configuration files in ``/etc/inmanta``.
9. Re-generate the systemd unit files and start the Inmanta server:

   .. code-block::

      $ sudo -i -u inmanta -- systemctl --user daemon-reload
      $ sudo -i -u inmanta -- systemctl --user start inmanta-orchestrator-server.service

10. The above-mentioned procedure didn't migrate the state directory of the Inmanta server. Hence, trigger a recompile in every environment to make sure that the state dir is populated correctly. This can be done by clicking the ``recompile`` button on the ``Compile Reports`` tab of the web-console.
11. Remove the RPM-based installation:

    .. code-block::

       $ dnf -y remove inmanta-service-orchestrator
       $ rm /etc/yum.repos.d/inmanta.repo

.. warning::

   The above-mentioned setup doesn't perform log rotation to let you the choice of dealing with the logs according to your own preferences.
 
