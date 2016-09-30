Install Inmanta
****************

For Ubuntu 14.04 (trusty) and Fedora 21, follow the instructions below. For other distributions,
install from `source <https://github.com/inmanta>`_. The
`readme <https://github.com/inmanta>`_ contains installation instructions to
install Inmanta from source.


Vagrant
-------

Docker
------

Centos
------

Fedora
------

The packages to install Inmanta are available in a yum/dnf repository. Following
instructions add the repository and install Inmanta on vm1:

.. code-block:: sh

    sudo curl -o /etc/yum.repos.d/inmanta.repo https://inmanta.io/repo/inmanta.repo
    sudo yum install -y python3-inmanta

On vm2 Inmanta is not required, as we will do an agentless install. However, `this requires python3 to be installed on all machines <https://github.com/inmanta>`_. To install Python 3 on vm2:

.. code-block:: sh

    sudo yum install -y python3

Ubuntu
------

The packages to install Inmanta on Ubuntu are available in a ppa. The following instructions add the
repository and install Inmanta:

.. code-block:: sh

    echo "deb https://inmanta.io/repo/trusty/ /" | sudo su -c "cat > /etc/apt/sources.list.d/inmanta.list"
    sudo apt-get update
    sudo apt-get install python3-inmanta

Apt might warn about unauthenticated packages, because the packages in our repository have not been
signed.


From source
------------
