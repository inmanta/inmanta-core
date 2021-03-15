Install the software
####################

.. tabs::

    .. tab:: CentOS 7

        For CentOS 7 use yum:

        .. code-block:: sh

          sudo tee /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
          [inmanta-oss-stable]
          name=inmanta-oss-stable
          baseurl=https://packages.inmanta.com/public/oss-stable/rpm/el/$releasever/$basearch
          repo_gpgcheck=1
          enabled=1
          gpgkey=https://packages.inmanta.com/public/oss-stable/gpg.A34DD0A274F07713.key
          gpgcheck=1
          sslverify=1
          sslcacert=/etc/pki/tls/certs/ca-bundle.crt
          metadata_expire=300
          pkg_gpgcheck=1
          autorefresh=1
          type=rpm-md
          EOF

          sudo yum install -y epel-release
          sudo yum install -y inmanta-oss inmanta-oss-server inmanta-oss-agent

        The first package (inmanta-oss) contains all the code and the commands. The server and the agent packages install config
        files and systemd unit files. The dashboard is installed with the server package.

    .. tab:: CentOS 8

        For CentOS 8 use dnf:

        .. code-block:: sh

          sudo tee /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
          [inmanta-oss-stable]
          name=inmanta-oss-stable
          baseurl=https://packages.inmanta.com/public/oss-stable/rpm/el/$releasever/$basearch
          repo_gpgcheck=1
          enabled=1
          gpgkey=https://packages.inmanta.com/public/oss-stable/gpg.A34DD0A274F07713.key
          gpgcheck=1
          sslverify=1
          sslcacert=/etc/pki/tls/certs/ca-bundle.crt
          metadata_expire=300
          pkg_gpgcheck=1
          autorefresh=1
          type=rpm-md
          EOF

          sudo dnf install -y epel-release
          sudo dnf install -y inmanta-oss inmanta-oss-server inmanta-oss-agent

        The first package (inmanta-oss) contains all the code and the commands. The server and the agent packages install config
        files and systemd unit files. The dashboard is installed with the server package.

    .. tab:: Other Linux and Mac

        First make sure Python >= 3.6 and git are installed. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with pip install in the newly created virtual env.

        .. code-block:: sh

            # Install python3 >= 3.6 and git
            sudo python3 -m venv /opt/inmanta
            sudo /opt/inmanta/bin/pip install inmanta
            sudo /opt/inmanta/bin/inmanta --help


        The misc folder in the source distribution contains systemd service files for both the server and the agent. Also
        install ``inmanta.cfg`` from the misc folder in ``/etc/inmanta/inmanta.cfg``

        If you want to use the dashboard you need to install it as well. Get the source from
        `our github page <https://github.com/inmanta/inmanta-dashboard/releases>`_ Next, build and install the dashboard. For
        this you need to have yarn and grunt:

        .. code-block:: sh

            tar xvfz inmanta-dashboard-20xx.x.x.tar.gz
            cd inmanta-dashboard-20xx.x.x
            yarn install
            grunt dist

        This creates a dist.tgz file in the current directory. Unpack this tarball in ``/opt/inmanta/dashboard`` and point
        the server in ``/etc/inmanta/inmanta.cfg`` to this location: set
        :inmanta.config:option:`dashboard.path` to ``/opt/inmanta/dashboard``


    .. tab:: Windows

        On Windows only the compile and export commands are supported. This is useful in the :ref:`push-to-server` deployment mode of
        inmanta. First make sure you have Python >= 3.6 and git. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with pip install in the newly created virtual env.

        .. code-block:: powershell

            # Install python3 >= 3.6 and git
            python3 -m venv C:\inmanta\env
            C:\inmanta\env\Script\pip install inmanta
            C:\inmanta\env\Script\inmanta --help


    .. tab:: Source

        Get the source either from our `release page on github <https://github.com/inmanta/inmanta-core/releases>`_ or clone/download a branch directly.

        .. code-block:: sh

            git clone https://github.com/inmanta/inmanta-core.git
            cd inmanta
            pip install -c requirements.txt .

.. warning::
    When you use Inmanta modules that depend on python libraries with native code, python headers and a working compiler are required as well.

Configure server
################
This guide goes through the steps to set up an Inmanta service orchestrator server. This guide assumes a RHEL (7 or 8) or CentOS
(7 or 8) server is used. The rpm packages install the server configuration file in `/etc/inmanta/inmanta.cfg`.

Optional step 1: Setup SSL and authentication
---------------------------------------------

Follow the instructions in :ref:`auth-setup` to configure both SSL and authentication.
While not mandatory, it is highly recommended you do so.
