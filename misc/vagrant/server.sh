#!/bin/bash

sudo dnf install -y mongodb-server mongodb mongo-tools unzip
sudo systemctl enable mongod
sudo systemctl start mongod

cd /tmp
rm -rf dump
unzip /inmanta/misc/vagrant/mongodb.zip
mongorestore -h 127.0.0.1 dump

sudo cat >/etc/systemd/system/impera-server.service <<EOF
[Unit]
Description=The server of the Impera platform
After=network.target

[Service]
Type=simple
ExecStart=/opt/impera/server.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo cat >/opt/impera/server.sh <<EOF
#!/bin/bash

export PYTHONPATH=/inmanta/src
/opt/impera/env/bin/python3 -m impera.app -c /opt/impera/server.cfg -vvv server
EOF

sudo chmod +x /opt/impera/server.sh

sudo cat >/opt/impera/server.cfg <<EOF
[config]
heartbeat-interval = 60
state-dir=/var/lib/impera

[database]
host=localhost
name=impera

[server_rest_transport]
port = 8888

[server]
fact-expire = 600
fact-renew = 200
auto-recompile-wait = 10
#agent_autostart = *
server_address=172.20.20.10
EOF

sudo mkdir -p /var/lib/impera

sudo systemctl daemon-reload
sudo systemctl start impera-server
sudo systemctl enable impera-server

#sudo dnf install -y npm
#mkdir -p /home/vagrant/node_modules
#chown vagrant:vagrant /home/vagrant/node_modules
#mkdir -p /inmanta-dashboard/node_modules
#sudo mount --bind /home/vagrant/node_modules /inmanta-dashboard/node_modules
#cd /inmanta-dashboard
#npm install

#sudo cat >/etc/systemd/system/impera-dashboard.service <<EOF
#[Unit]
#Description=Impera dashboard
#After=network.target

#[Service]
#Type=simple
#User=vagrant
#Group=vagrant
#ExecStart=/opt/impera/dashboard.sh
#Restart=on-failure

#[Install]
#WantedBy=multi-user.target
#EOF

#sudo cat >/opt/impera/dashboard.sh <<EOF
##!/bin/bash

#cd /inmanta-dashboard
#npm start
#EOF

#sudo chmod +x /opt/impera/dashboard.sh

#sudo systemctl daemon-reload
#sudo systemctl start impera-dashboard
#sudo systemctl enable impera-dashboard

