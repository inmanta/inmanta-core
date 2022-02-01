In order to run a manually started agent, the ``inmanta-oss-agent`` package is required on the
machine that will run the agent.

.. code-block:: sh

    sudo tee /etc/yum.repos.d/inmanta_oss_stable.repo <<EOF
    [inmanta-oss-stable]
    name=Inmanta OSS stable
    baseurl=https://pkg.inmanta.com/inmanta-oss-stable/el8/
    gpgcheck=1
    gpgkey=https://pkg.inmanta.com/inmanta-oss-stable/inmanta-oss-stable-public-key
    repo_gpgcheck=1
    enabled=1
    enabled_metadata=1
    EOF

    sudo dnf install -y inmanta-oss-agent
