Install the software
####################

.. tabs::

    .. tab:: CentOS 7

        For CentOS 7 use yum:

        .. code-block:: sh

          sudo tee /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
          [inmanta-oss-stable]
          name=inmanta-oss-stable
          baseurl=https://packages.inmanta.com/public/oss-stable/rpm/el/\$releasever/\$basearch
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
          baseurl=https://packages.inmanta.com/public/oss-stable/rpm/el/\$releasever/\$basearch
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


    .. tab:: Debian, Ubuntu and derivatives.

        First make sure Python >= 3.6 and git are installed. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with pip install in the newly created virtual env.

        Please note, the path to the virtual env is arbitrary. Your desired path can override below example.

        .. code-block:: sh

            # Install GCC, python3 >= 3.6 and pip
            sudo apt-get update
            sudo apt-get install build-essential
            sudo apt-get install python3-pip

            # Install wheel and inmanta in a python venv
            sudo apt-get install python3-venv
            sudo python3 -m venv /opt/inmanta
            sudo /opt/inmanta/bin/pip install wheel
            sudo /opt/inmanta/bin/pip install inmanta
            sudo /opt/inmanta/bin/inmanta --help

            # Install PostgreSQL
            sudo apt-get install postgresql postgresql-client


        Download the configuration file named ``inmanta.cfg`` (this name is arbitrary) in your virtual env:

        .. code-block:: sh

            sudo apt-get install wget
            sudo wget -O /opt/inmanta/inmanta.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/inmanta.cfg"


        If you want to use the dashboard you need to install it as well:

        Get the pre-built package from `our github page <https://github.com/inmanta/inmanta-dashboard/packages/>`_ click on the latest release and then on the right hand side, under ``Assets``, you will see the compressed package. Download and extract it to your desired directory (preferably, on the same virtual env which was created earlier, in this case, /opt/inmanta). Next, open the ``inmanta.cfg`` file and at the bottom of the file, under ``[dashboard]`` section, change the ``path`` value to the ``dist`` directory of where you extracted the pre-built package. For instance:

        .. code-block:: ini

            path=/opt/inmanta/package/dist


        Then the dashboard can be started using below command (please note, below command has to be run after completing the  :ref:`configure-server`) part:

        .. code-block:: bash

            inmanta -vv -c /opt/inmanta/inmanta.cfg server


    .. tab:: Other

        First make sure Python >= 3.6 and git are installed. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with ``pip install`` in the newly created virtual env.

        Please note, the path to the virtual env is arbitrary. Your desired path can override below example.

        .. code-block:: sh

            # Install python3 >= 3.6 and git
            # If git is not already installed, by running git in your terminal, the installation guide will be shown
            sudo python3 -m venv /opt/inmanta
            sudo /opt/inmanta/bin/pip install inmanta
            sudo /opt/inmanta/bin/inmanta --help


        Install PostgreSQL using this `guide <https://www.postgresql.org/docs/13/tutorial-install.html>`_


        Download the configuration file named ``inmanta.cfg`` (this name is arbitrary) in your virtual env:

        .. code-block:: sh

            sudo wget -O /opt/inmanta/inmanta.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/inmanta.cfg"


        If you want to use the dashboard you need to install it as well:

        Get the pre-built package from `our github page <https://github.com/inmanta/inmanta-dashboard/packages/>`_ click on the latest release and then on the right hand side, under ``Assets``, you will see the compressed package, download and extract it to your desired directory (preferably, on the same virtual env which was created earlier, in this case, /opt/inmanta). Next, open the ``inmanta.cfg`` file and at the bottom of the file, under ``[dashboard]`` section, change the ``path`` value to the ``dist`` directory of where you extracted the pre-built package. For instance:

        .. code-block:: ini

            path=/opt/inmanta/package/dist


        Then the dashboard can be started using below command:

        .. code-block:: bash

            inmanta -vv -c /opt/inmanta/inmanta.cfg server


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

.. _configure-server:

Configure server
################
This guide goes through the steps to set up an Inmanta service orchestrator server. This guide assumes a RHEL (7 or 8) or CentOS
(7 or 8) server is used. The rpm packages install the server configuration file in `/etc/inmanta/inmanta.cfg`.

Optional step 1: Setup SSL and authentication
---------------------------------------------

Follow the instructions in :ref:`auth-setup` to configure both SSL and authentication.
While not mandatory, it is highly recommended you do so.
