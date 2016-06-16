Installing Inmanta
=================

For Ubuntu 14.04 (trusty) and Fedora 21, follow the instructions below. For other distributions,
install from `source <https://github.com/inmanta>`_. The
`readme <https://github.com/inmanta>`_ contains installation instructions to
install Inmanta from source.


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


SSH Root access
---------------

In this tutorial we use agentless deployments, with vm1 as the management machine.
This means that it will manage itself and vm2 over SSH, thus requiring SSH root access to vm1 and vm2.
Therefore your public SSH key needs to be installed in the ``authorized_keys`` file of the root user on both machines.

If your public key is already installed in the current user, you can copy it to the root user with the following commands:

.. code-block:: sh

    sudo cp -a .ssh /root/
    sudo chown -R root:root /root/.ssh


In this guide we assume that you can login into vm2 using the same SSH keypair as you used to
login into vm1.  Therefore, use agent forwarding (the -A option) when you login into the vm1,
*before you continue with this guide*.

Check from the user on vm1 if you can login into vm1 and vm2 as root and accept the host key.

.. code-block:: sh

    ssh root@IP_OF_VM1
    ssh root@IP_OF_VM2

SELinux
-------

In a default Fedora, SELinux and possibly the firewall are configured and activated. This may cause
problems because managing these services is not covered here. We recommend that
you either set SELinux to permissive mode and disable the firewall with:

.. code-block:: sh

   sudo setenforce 0
   sudo sed -i "s/SELINUX=enforcing/SELINUX=permissive/g" /etc/sysconfig/selinux
   sudo systemctl stop firewalld

Or consult the Fedora documentation and change the firewall settings and set the correct SELinux
booleans.


