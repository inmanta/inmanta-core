#!/bin/bash

sudo cat >/etc/systemd/system/inmanta-agent.service <<EOF
[Unit]
Description=The server of the Inmanta platform
After=network.target

[Service]
Type=simple
ExecStart=/opt/inmanta/agent.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo cat >/opt/inmanta/agent.sh <<EOF
#!/bin/bash

export PYTHONPATH=/inmanta/src
/opt/inmanta/env/bin/python3 -m inmanta.app -c /opt/inmanta/agent.cfg -vvv agent
EOF

sudo chmod +x /opt/inmanta/agent.sh

cat > /opt/inmanta/agent.cfg <<EOF
[config]
heartbeat-interval = 60
fact-expire = 60
state-dir=/var/lib/inmanta

node-name=vm1.dev.inmanta.com
environment=1cc5c6ad-7b90-4547-b45f-2ccee1dac50b
agent-names=\$node-name

[agent_rest_transport]
port = 8888 
host = 172.20.20.10
EOF

sudo mkdir -p /var/lib/inmanta

sudo systemctl daemon-reload
sudo systemctl start inmanta-agent
sudo systemctl enable inmanta-agent
