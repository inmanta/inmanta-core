Install Inmanta
****************

Inmanta requires python3 on your system. If you install it from source, python3 and pip need to be
installed. If you install from package, your package manager should install python3 if not yet
available on your system.


With pip
---------
Inmanta can be installed with pip, however, we depend on a version of motorengine that is not in pypi yet. You must first install this version by hand.

.. code-block:: sh

    pip install https://packages.inmanta.com/misc/motorengine-0.9.1dev0.tar.gz
    pip install inmanta
    

From source
------------


.. code-block:: sh

    git clone https://github.com/inmanta/inmanta.git
    cd inmanta 
    pip install --process-dependency-links .


Fedora
------

.. code-block:: sh

  sudo dnf copr enable bartvanbrabant/inmanta
  sudo dnf install python3-inmanta
  sudo dnf install python3-inmanta-server
  sudo dnf install python3-inmanta-agent
  sudo dnf install mongodb-server

The first package contains all the code and the commands. The server and the agent packages install
config files and systemd unit files.

To start mongodb and the server:

.. code-block:: sh

  sudo systemctl start mongod
  sudo systemctl start inmanta-server

More information on is availabe at: https://copr.fedorainfracloud.org/coprs/bartvanbrabant/inmanta/

To install the dashboard:

.. code-block:: sh

  sudo -i
  cat > /etc/yum.repos.d/inmanta.repo <<EOF
  [inmanta-dash]
  baseurl=https://packages.inmanta.com/rpms/inmanta-dashboard/
  enabled=1
  gpgcheck=0
  EOF
  sudo dnf install inmanta-dashboard
  exit
  
And add the following section to the config file (`/etc/inmanta/server.cfg`)

.. code-block:: ini

  [dashboard]
  enabled=true
  path=/usr/share/inmanta/dashboard

CentOS
------
CentOS does not have python3. For CentOS 7 we use the python34 software
collection of Redhat.

First install the `rh-python34 software collection <https://www.softwarecollections.org/en/scls/rhscl/rh-python34/>`_

.. code-block:: sh

  sudo yum install centos-release-scl
  sudo yum install rh-python34

Enable the inmanta-scl copr repo:

.. code-block:: sh

  cd /etc/yum.repos.d
  sudo wget https://copr.fedorainfracloud.org/coprs/bartvanbrabant/inmanta-scl/repo/epel-7/bartvanbrabant-inmanta-scl-epel-7.repo

Install inmanta tool, server or agent or all:

.. code-block:: sh
  
  sudo yum install rh-python34-python-inmanta
  sudo yum install rh-python34-python-inmanta-server
  sudo yum install rh-python34-python-inmanta-agent
  sudo yum install mongodb-server

The first package contains all the code and the commands. The server and the agent packages install
config files and systemd unit files.

To install the dashboard:

.. code-block:: sh

  sudo -i
  cat > /etc/yum.repos.d/inmanta.repo <<EOF
  [inmanta-dash]
  baseurl=https://packages.inmanta.com/rpms/inmanta-dashboard/
  enabled=1
  gpgcheck=0
  EOF
  sudo dnf install inmanta-dashboard
  exit
  
And add the following section to the config file (`/etc/inmanta/server.cfg`)

.. code-block:: ini

  [dashboard]
  enabled=true
  path=/usr/share/inmanta/dashboard
