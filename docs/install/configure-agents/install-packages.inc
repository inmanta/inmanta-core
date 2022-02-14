In order to run a manually started agent, the ``inmanta-oss-agent`` package is required on the
machine that will run the agent.

.. code-block:: sh

    sudo tee /etc/yum.repos.d/inmanta-oss-stable.repo <<EOF
    [inmanta-oss-stable]
    name=Inmanta OSS stable
    baseurl=https://packages.inmanta.com/public/oss-stable/rpm/el/\$releasever/\$basearch
    gpgcheck=1
    gpgkey=https://packages.inmanta.com/public/oss-stable/gpg.A34DD0A274F07713.key
    repo_gpgcheck=1
    enabled=1
    enabled_metadata=1
    EOF

    sudo dnf install -y inmanta-oss-agent
