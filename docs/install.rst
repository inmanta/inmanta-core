Install Inmanta
****************

Inmanta requires python3 on your system. If you install it from source, python3 and pip need to be
installed. If you install from package, your package manager installs python3 if not yet available
on your system.


With pip
---------
Inmanta can be installed with pip.

.. code-block:: sh

    pip install inmanta


From source
------------


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
  baseurl=https://pkg.inmanta.com/inmanta-oss-stable/f$releasever/
  gpgcheck=1
  gpgkey=https://pkg.inmanta.com/inmanta-oss-stable/inmanta-oss-stable-public-key
  repo_gpgcheck=1
  enabled=1
  enabled_metadata=1
  EOF
  sudo dnf install -y python3-inmanta python3-inmanta-server python3-inmanta-agent mongodb-server

For CentOS use yum and install epel-release:

.. code-block:: sh

  cat > /etc/yum.repos.d/inmanta_oss_dev.repo <<EOF
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

To start mongodb and the server:

.. code-block:: sh

  sudo systemctl enable mongod
  sudo systemctl start mongod
  sudo systemctl enable inmanta-server
  sudo systemctl start inmanta-server

On machine that run the compiler or agent may require to install python packages with pip. Some
libraries, such as OpenStack clients have dependencies that require gcc and python3-devel to be
availabe as well.

More information on is availabe at: https://copr.fedorainfracloud.org/coprs/bartvanbrabant/inmanta/
