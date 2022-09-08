#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

# Install microk8s
# snap install microk8s --classic

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
cp /usr/share/webmin/stabile/tabs/kubernetes/manifests/*-test.yaml /home/stabile/
chown 1001:1001 /home/stabile/*

# Remove unneeded tabs
# rm -r /usr/share/webmin/stabile/tabs/servers
# rm -r /usr/share/webmin/stabile/tabs/commands

# Change logo
perl -pi -e 's/images\/ubuntu-logo.png/tabs\/kubernetes\/kubernetes-icon.svg/' /usr/share/webmin/stabile/index.cgi

systemctl enable docker
systemctl enable stabile-kubernetes
apt-mark hold kubeadm kubelet kubectl

# Set up SSL access to Kubernetes Dashboard on port 10002
#cp /etc/apache2/sites-available/default-ssl.conf /etc/apache2/sites-available/kubernetes-ssl.conf
#perl -pi -e 's/<VirtualHost _default_:443>/<VirtualHost _default_:10002>/;' /etc/apache2/sites-available/kubernetes-ssl.conf

#perl -pi -e 's/(\s+<\/VirtualHost>)/        ProxyPass \/ http:\/\/dashboardip:80\/\n        ProxyPassReverse \/ http:\/\/dashboardip:80\/\n        Header set Authorization "Bearer \${KUBE_TOKEN}"\n$1/;' /etc/apache2/sites-available/kubernetes-ssl.conf
#perl -pi -e 's/(DocumentRoot \/var\/www\/html)/$1\n        <Location \/>\n            deny from all\n            allow from 127.0.0.1\n        <\/Location>/;' /etc/apache2/sites-available/kubernetes-ssl.conf

perl -pi -e 's/Listen 443/Listen 443\n    Listen 10002/;' /etc/apache2/ports.conf
echo "export KUBE_TOKEN= " >> /etc/apache2/envvars

cp /tmp/files/logout.js /var/www/html/
cp /tmp/files/kubernetes-ssl.conf /etc/apache2/sites-available
touch /etc/apache2/kubepasswords
#htpasswd -bc /etc/apache2/kubepasswords admin-user change-me

a2ensite kubernetes-ssl
a2enmod headers
a2enmod request
a2enmod substitute
a2enmod filter

# Change cgroups driver for Docker
perl -pi -e 's/ExecStart=(.*)/ExecStart=$1 --exec-opt native.cgroupdriver=systemd/' /lib/systemd/system/docker.service

echo "net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1" > /etc/sysctl.d/k8s.conf

sysctl --system

echo "overlay
br_netfilter" >> /etc/modules-load.d/modules.conf

echo "#!/bin/bash
export KUBECONFIG=/etc/kubernetes/admin.conf" > /etc/profile.d/kubernetes.sh
echo "env_KUBECONFIG=/etc/kubernetes/admin.conf" >> /etc/webmin/miniserv.conf
echo 'Defaults	env_keep += "KUBECONFIG"' > /etc/sudoers.d/kubeconfig
chmod 440 /etc/sudoers.d/kubeconfig
