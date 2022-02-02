Install the software
####################

.. tabs::

    .. tab:: RHEL 8

        For RHEL 8 based systems use dnf:

        .. code-block:: sh

          sudo tee /etc/yum.repos.d/inmanta-oss-stable.repo <<EOF
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

          sudo dnf install -y inmanta-oss inmanta-oss-server inmanta-oss-agent

        The first package (inmanta-oss) contains all the code and the commands. The server and the agent packages install config
        files and systemd unit files. The dashboard is installed with the server package.


    .. tab:: Debian, Ubuntu and derivatives.

        First make sure Python >= 3.9 and git are installed. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with pip install in the newly created virtual env.

        Please note, the path to the virtual env is arbitrary. Your desired path can override below example.

        .. code-block:: sh

            # Install GCC, python3 >= 3.9 and pip
            sudo apt-get update
            sudo apt-get install build-essential
            sudo apt-get install python3-pip

            # Install wheel and inmanta in a python venv
            sudo apt-get install python3-venv
            sudo python3 -m venv /opt/inmanta
            sudo /opt/inmanta/bin/pip install -U pip wheel
            sudo /opt/inmanta/bin/pip install inmanta
            sudo /opt/inmanta/bin/inmanta --help

            # Install PostgreSQL
            sudo apt-get install postgresql postgresql-client


        Download the configuration files named ``inmanta.cfg`` and ``extensions.cfg`` (these names are arbitrary) in your virtual env:

        .. code-block:: sh

            sudo mkdir /opt/inmanta/inmanta.d
            sudo apt-get install wget
            sudo wget -O /opt/inmanta/inmanta.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/inmanta.cfg"
            sudo wget -O /opt/inmanta/inmanta.d/extensions.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/extensions.cfg"


        If you want to use the web-console and/or the dashboard you need to install it as well:

        Get the pre-built package from our `web-console <https://github.com/inmanta/web-console/packages/>`_ and/or `dashboard <https://github.com/inmanta/inmanta-dashboard/packages/>`_ github page. Click on the the package name to go to the package's main page, then on the right hand side under ``Assets``, you will see the compressed package. Download and extract it to your desired directory (preferably, on the same virtual env which was created earlier, in this case, /opt/inmanta). Next, open the ``inmanta.cfg`` file and at the bottom of the file, under the ``[dashboard]`` and/or ``[web-console]`` section, change the ``path`` value to the ``dist`` directory of where you extracted the pre-built package. For instance:

        .. code-block:: ini

            path=/opt/inmanta/web-console/package/dist


        Then the web-console/dashboard can be started using below command (please note, below command has to be run after completing the  :ref:`configure-server`) part:

        .. code-block:: bash

            sudo /opt/inmanta/bin/inmanta -vv -c /opt/inmanta/inmanta.cfg --config-dir /opt/inmanta/inmanta.d server


    .. tab:: Other

        First make sure Python >= 3.9 and git are installed. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with ``pip install`` in the newly created virtual env.

        Please note, the path to the virtual env is arbitrary. Your desired path can override below example.

        .. code-block:: sh

            # Install python3 >= 3.9 and git
            # If git is not already installed, by running git in your terminal, the installation guide will be shown
            sudo python3 -m venv /opt/inmanta
            sudo /opt/inmanta/bin/pip install -U pip wheel
            sudo /opt/inmanta/bin/pip install inmanta
            sudo /opt/inmanta/bin/inmanta --help


        Install PostgreSQL using this `guide <https://www.postgresql.org/docs/13/tutorial-install.html>`_



        Download the configuration files named ``inmanta.cfg`` and ``extensions.cfg`` (these names are arbitrary) in your virtual env:

        .. code-block:: sh

            sudo mkdir /opt/inmanta/inmanta.d
            sudo wget -O /opt/inmanta/inmanta.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/inmanta.cfg"
            sudo wget -O /opt/inmanta/inmanta.d/extensions.cfg "https://raw.githubusercontent.com/inmanta/inmanta-core/master/misc/extensions.cfg"


        If you want to use the web-console and/or the dashboard you need to install it as well:

        Get the pre-built package from our `web-console <https://github.com/inmanta/web-console/packages/>`_ and/or `dashboard <https://github.com/inmanta/inmanta-dashboard/packages/>`_ github page. Click on the the package name to go to the package's main page, then on the right hand side under ``Assets``, you will see the compressed package. Download and extract it to your desired directory (preferably, on the same virtual env which was created earlier, in this case, /opt/inmanta). Next, open the ``inmanta.cfg`` file and at the bottom of the file, under the ``[dashboard]`` and/or ``[web-console]`` section, change the ``path`` value to the ``dist`` directory of where you extracted the pre-built package. For instance:

        .. code-block:: ini

            path=/opt/inmanta/web-console/package/dist


        Then the web-console/dashboard can be started using below command (please note, below command has to be run after completing the  :ref:`configure-server`) part:

        .. code-block:: bash

            /opt/inmanta/bin/inmanta -vv -c /opt/inmanta/inmanta.cfg --config-dir /opt/inmanta/inmanta.d server


    .. tab:: Windows

        On Windows only the compile and export commands are supported. This is useful in the :ref:`push-to-server` deployment mode of
        inmanta. First make sure you have Python >= 3.9 and git. Inmanta requires many dependencies so it is recommended to create a virtual env.
        Next install inmanta with pip install in the newly created virtual env.

        .. code-block:: powershell

            # Install python3 >= 3.9 and git
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
This guide goes through the steps to set up an Inmanta service orchestrator server. This guide assumes a RHEL 8 based
server is used. The rpm packages install the server configuration file in `/etc/inmanta/inmanta.cfg`.

Optional step 1: Setup SSL and authentication
---------------------------------------------

Follow the instructions in :ref:`auth-setup` to configure both SSL and authentication.
While not mandatory, it is highly recommended you do so.
