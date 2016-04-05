#!/bin/bash

sudo cat >/etc/systemd/system/impera-agent.service <<EOF
[Unit]
Description=The server of the Impera platform
After=network.target

[Service]
Type=simple
ExecStart=/opt/impera/agent.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo cat >/opt/impera/agent.sh <<EOF
#!/bin/bash

export PYTHONPATH=/inmanta/src
/opt/impera/env/bin/python3 -m impera.app -c /opt/impera/agent.cfg -vvv agent
EOF

sudo chmod +x /opt/impera/agent.sh

cat > /opt/impera/agent.cfg <<EOF
[config]
heartbeat-interval = 60
fact-expire = 60
state-dir=/var/lib/impera

environment=1cc5c6ad-7b90-4547-b45f-2ccee1dac50b
agent-names=\$node-name

[agent_rest_transport]
port = 8888 
host = 172.20.20.10
EOF

sudo mkdir -p /var/lib/impera

sudo systemctl daemon-reload
sudo systemctl start impera-agent
sudo systemctl enable impera-agent


