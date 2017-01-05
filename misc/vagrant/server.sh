#!/bin/bash

sudo dnf install -y mongodb-server mongodb mongo-tools unzip
sudo systemctl enable mongod
sudo systemctl start mongod

cd /tmp
rm -rf dump
unzip /inmanta/misc/vagrant/mongodb.zip
mongorestore -h 127.0.0.1 dump

sudo cat >/etc/systemd/system/inmanta-server.service <<EOF
[Unit]
Description=The server of the Inmanta platform
After=network.target

[Service]
Type=simple
ExecStart=/opt/inmanta/server.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo cat >/opt/inmanta/server.sh <<EOF
#!/bin/bash

export PYTHONPATH=/inmanta/src
/opt/inmanta/env/bin/python3 -m inmanta.app -c /opt/inmanta/server.cfg -vvv server
EOF

sudo chmod +x /opt/inmanta/server.sh

sudo cat >/opt/inmanta/server.cfg <<EOF
[config]
heartbeat-interval = 60
state-dir=/var/lib/inmanta

[database]
host=localhost
name=inmanta

[server_rest_transport]
port = 8888

[server]
fact-expire = 600
fact-renew = 200
auto-recompile-wait = 10
#agent_autostart = *
server_address=172.20.20.10

[dashboard]
enabled=true
path=/usr/share/inmanta/dashboard
EOF

sudo mkdir -p /var/lib/inmanta

sudo systemctl daemon-reload
sudo systemctl start inmanta-server
sudo systemctl enable inmanta-server


