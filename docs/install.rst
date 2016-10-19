Install Inmanta
****************

Inmanta requires python3 on your system. If you install it from source, python3 and pip need to be
installed. If you install from package, your package manager should install python3 if not yet
available on your system.

From source
------------
Stable releases are published in pypi, so the latest version can be installed with pip. However, the
latest releases use an unreleased version of motorengine:

- If you download the source. Install inmanta with `pip install --process-dependency-links .`
- If you install it with pip install inmanta, first install the correct motorengine with the
  following command: `pip install https://packages.inmanta.com/misc/motorengine-0.9.1dev0.tar.gz`

Fedora
------
A COPR repository contains rpm builds of the latest inmanta and dependencies that have not been
included yet in Fedora. More information on how to use this COPR repository is availabe at:

https://copr.fedorainfracloud.org/coprs/bartvanbrabant/inmanta/

Install inmanta tool, server or agent or all:

.. code-block:: sh

  $ sudo dnf install python3-inmanta
  $ sudo dnf install python3-inmanta-server
  $ sudo dnf install python3-inmanta-agent

The first package contains all the code and the commands. The server and the agent packages install
config files and systemd unit files.

CentOS
------
CentOS does not have python3. For CentOS 7 we have a COPR repo that uses the python34 software
collection of Redhat.

First install the rh-python34 software collection (https://www.softwarecollections.org/en/scls/rhscl/rh-python34/)

.. code-block:: sh

  $ sudo yum install centos-release-scl
  $ sudo yum install rh-python34

Enable the inmanta-scl copr repo:

.. code-block:: sh

  $ cd /etc/yum.repos.d
  $ wget https://copr.fedorainfracloud.org/coprs/bartvanbrabant/inmanta-scl/repo/epel-7/bartvanbrabant-inmanta-scl-epel-7.repo

Install inmanta tool, server or agent or all:

.. code-block:: sh
  
  $ sudo dnf install rh-python34-python-inmanta
  $ sudo dnf install rh-python34-python-inmanta-server
  $ sudo dnf install rh-python34-python-inmanta-agent

The first package contains all the code and the commands. The server and the agent packages install
config files and systemd unit files.


