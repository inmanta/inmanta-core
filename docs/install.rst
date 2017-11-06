Install Inmanta
****************
This page explain how to install the Inmanta orchestrator software and setup an orchestration server.

Install software
################
Inmanta requires python3 on your system. If you install it from source, python3 and pip need to be
installed. If you install from package, your package manager installs python3 if not yet available
on your system.

Systems that run the compiler or agent may require to install python packages with pip. These packages are requirments
of configuration modules. Some python packages, such as OpenStack clients have dependencies that require gcc and 
python3-devel to be availabe as well. The pre-packaged rpms contain the correct dependencies. When Inmanta is installed from 
source or pypi they need to be installed manually.

With pip
---------
Inmanta can be installed with pip.

.. code-block:: sh

    pip install inmanta


From source
------------

Either checkout of the code or use the releases page: https://github.com/inmanta/inmanta/releases

.. code-block:: sh

    git clone https://github.com/inmanta/inmanta.git
    cd inmanta
    pip install .


Fedora and CentOS 7
-------------------
For Fedora use dnf:

.. code-block:: sh

  cat > /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
  [inmanta-oss-stable]
  name=Inmanta OSS stable
  baseurl=https://pkg.inmanta.com/inmanta-oss-stable/f\$releasever/
  gpgcheck=1
  gpgkey=https://pkg.inmanta.com/inmanta-oss-stable/inmanta-oss-stable-public-key
  repo_gpgcheck=1
  enabled=1
  enabled_metadata=1
  EOF
  sudo dnf install -y python3-inmanta python3-inmanta-server python3-inmanta-agent mongodb-server

For CentOS use yum and install epel-release:

.. code-block:: sh

  cat > /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
  [inmanta-oss-stable]
  name=Inmanta OSS stable
  baseurl=https://pkg.inmanta.com/inmanta-oss-stable/el7/
  gpgcheck=1
  gpgkey=https://pkg.inmanta.com/inmanta-oss-stable/inmanta-oss-stable-public-key
  repo_gpgcheck=1
  enabled=1
  enabled_metadata=1
  EOF

  sudo yum install -y epel-release
  sudo yum install -y python3-inmanta python3-inmanta-server python3-inmanta-agent mongodb-server

The first package (python3-inmanta) contains all the code and the commands. The server and the agent
packages install config files and systemd unit files. The dashboard is installed with the server
package.

Configure server
################
This guide goes through the steps to setup an Inmanta service orchestrator server. This guide assumes a RHEL 7 or CentOS 7 
server. The rpm packages install the server configuration file in /etc/inmanta/server.cfg

Optional step 1: Setup SSL and authentication
---------------------------------------------

Follow the instructions in :ref:`auth-setup` to configure both SSL and authentication. It is not mandatory but still highly 
recommended.


Step 2: Setup mongodb
---------------------

Make sure mongodb is started and reachable by the Inmanta server. By default Inmanta tries to connect to the local server
and uses the database inmanta. See the :inmanta.config:group:`database` section in the configfile for other options.


Step 3: Set the server address
------------------------------

When virtual machines are started by this server that install the inmanta agent, the correct 
:inmanta.config:option:`server.server-address` needs to be 
configured. This address is used to create the correct boot script for the virtual machine.

Set this value to the hostname or IP address that others systems use to connect to the server. 

.. note:: If you deploy configuration models that modify resolver configuration it is recommended to use the IP address instead
  of the hostname.


Step 4: Configure ssh of the inmanta user
-----------------------------------------

The inmanta user that runs the server needs a working ssh client. This client is required to checkout git repositories over 
ssh and if the remote agent is used.

 1. Provide the inmanta user with one or more private keys:

    a. Generate a new key with ssh-keygen as the inmanta user: ``sudo -u inmanta ssh-keygen -N ""``
    b. Install an exiting key in /var/lib/inmanta/.ssh/id_rsa Make sure the permissions and ownership are set correctly.

 2. Configure ssh to accept all host keys or white list the hosts that are allowed or use signed host keys 
    (depends on your security requirements). This guide configures ssh client for the inmanta user to accept all host keys.
    Create /var/lib/inmanta/.ssh/config and create the following content:

    .. code-block:: text

      Host *
          StrictHostKeyChecking no
          UserKnownHostsFile=/dev/null

  3. Add the public key to any git repositories and save if to include in configuration models that require remote agents.
  4. Test if you can login into a machine that has the public key and make sure ssh does not show you any prompts to store 
     the host key.


Step 5: Start the server
------------------------

Start the server and make sure it is started at boot.

.. code-block:: sh

  sudo systemctl enable inmanta-server
  sudo systemctl start inmanta-server
