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

  $ sudo dnf copr enable bartvanbrabant/inmanta
  $ sudo dnf install python3-inmanta
  $ sudo dnf install python3-inmanta-server
  $ sudo dnf install python3-inmanta-agent

The first package contains all the code and the commands. The server and the agent packages install
config files and systemd unit files.

More information on is availabe at: https://copr.fedorainfracloud.org/coprs/bartvanbrabant/inmanta/

CentOS
------
CentOS does not have python3. For CentOS 7 we use the python34 software
collection of Redhat.

First install the `rh-python34 software collection <https://www.softwarecollections.org/en/scls/rhscl/rh-python34/>`_

.. code-block:: sh

  $ sudo yum install centos-release-scl
  $ sudo yum install rh-python34

Enable the inmanta-scl copr repo:

.. code-block:: sh

  $ cd /etc/yum.repos.d
  $ sudo wget https://copr.fedorainfracloud.org/coprs/bartvanbrabant/inmanta-scl/repo/epel-7/bartvanbrabant-inmanta-scl-epel-7.repo

Install inmanta tool, server or agent or all:

.. code-block:: sh
  
  $ sudo dnf install rh-python34-python-inmanta
  $ sudo dnf install rh-python34-python-inmanta-server
  $ sudo dnf install rh-python34-python-inmanta-agent

The first package contains all the code and the commands. The server and the agent packages install
config files and systemd unit files.


