# -*- mode: ruby -*-
# vi: set ft=ruby :

domain = "dev.inmanta.com"
box = "fedora/23-cloud-base"

nodes = [
    {:hostname => "server", :ip => "172.20.20.10", :fwd => {8888 => 8888}, :ram => 1024, :scripts => ["common.sh", "server.sh"]},
    {:hostname => "vm1", :ip => "172.20.20.11", :scripts => ["common.sh", "agent.sh"]},
]

# $ sudo dnf copr enable dustymabe/vagrant-sshfs
# $ sudo dnf install vagrant-sshfs

Vagrant.configure(2) do |config|
    nodes.each do |node|
        config.vm.define node[:hostname] do |node_config|
            node_config.vm.box = box
            node_config.vm.hostname = node[:hostname] + "." + domain
            node_config.vm.network :private_network, ip: node[:ip]

            if node[:fwd]
                node[:fwd].each do |src,dst|
                    node_config.vm.network :forwarded_port, guest: src, host: dst
                end
            end

            node_config.vm.synced_folder ".", "/vagrant", disabled: true
            node_config.vm.synced_folder ".", "/inmanta", type: "sshfs"

            node[:scripts].each do |script|
                node_config.vm.provision "shell", path: "misc/vagrant/" + script
            end
        end
    end
end
