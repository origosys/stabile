#!/usr/bin/perl

use JSON;

my $dev = 'eth0';
$dev = 'ens3';
my $ipstart = $1 if (`ifconfig $dev` =~ /inet (\d+\.\d+\.\d+)\.\d+/);
my $gw = "$ipstart.1" if ($ipstart);

my $intip = get_internalip();
my $mip;
my $mserver = show_management_server();
my $dashboardns = "kubernetes-dashboard";
if ($mserver) {
    $mip = $mserver->{internalip};
}
my $extip = get_externalip();

if ($intip && $mip) {
    if ($intip eq $mip) {
        if (-e "/usr/share/webmin/stabile/tabs/kubernetes/joincmd.sh") {
            ;
        } else {
            my $kinit = `kubeadm init --pod-network-cidr=10.244.0.0/16 --apiserver-cert-extra-sans=$extip | tee /root/initout.log 2>\&1`;
            if ($kinit =~ /(kubeadm join .+--discovery-token-ca-cert-hash sha256:.+)/s) {
                my $joincmd = $1;
                $joincmd =~ s/\n//;
                $joincmd =~ s/\\//;
                $joincmd =~ s/\s+/ /g;

                # Install CNI
#                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://docs.projectcalico.org/v3.3/getting-started/kubernetes/installation/hosted/rbac-kdd.yaml >> /root/initout.log`;
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml >> /root/initout.log`;

#                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/k8s-manifests/kube-flannel-rbac.yml >> /root/initout.log 2>\&1`;
#                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml >> /root/initout.log 2>\&1`;

            # Allow admin node to run pods
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl taint nodes --all node-role.kubernetes.io/master- >> /root/initout.log 2>\&1`;

            # Add the nfs storageclasses
            # Please note that for now we use the image docker.io/timmiles/nfs-subdir-external-provisioner:latest instead of the standard image
            # quay.io/external_storage/nfs-client-provisioner:latest which for now is broken with Kubernetes 1.20.2
            # See: https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner/issues/25#issuecomment-742616668
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f /usr/share/webmin/stabile/tabs/kubernetes/manifests/nfs-roles.yaml >> /root/initout.log 2>\&1`;
                my $json = `stabile-helper mountpools`;
                my $spools = from_json($json);
            #    my $pool0path = $spools->{'0'}->{'path'};
            #    $pool0path =~ s/\//\\\//g;
                my @pools=keys(%{$spools});
                $json = `curl -ks https://$gw/stabile/users/me`;
                my $me = from_json($json);
                my $username = $me->[0]->{'username'};
                $username =~ s/\@/\\\@/;
                for (my $i=0; $i< scalar @pools; $i++) {
                    my $pool = $pools[$i];
                    my $poolpath = $spools->{$pool}->{'path'};
                    $poolpath =~ s/\//\\\//g;
                    `perl -pi -e 's/pool\\d+/pool$pool/' /usr/share/webmin/stabile/tabs/kubernetes/manifests/nfs-storage.yaml`;
                    `perl -pi -e 's/: (.+) #nfspath/: $poolpath\\/$username\\/fuel #nfspath/' /usr/share/webmin/stabile/tabs/kubernetes/manifests/nfs-storage.yaml`;
                    `perl -pi -e 's/gatewayip/$gw/' /usr/share/webmin/stabile/tabs/kubernetes/manifests/nfs-storage.yaml`;
                    `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f /usr/share/webmin/stabile/tabs/kubernetes/manifests/nfs-storage.yaml >> /root/initout.log 2>\&1`;
                }

            # Add the local storageclass
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f /usr/share/webmin/stabile/tabs/kubernetes/manifests/local-storage.yaml >> /root/initout.log 2>\&1`;

            # Set local-storage as default storageclass
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl patch storageclass local-storage -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}' >> /root/initout.log 2>\&1`;

            # Install nginx ingress controller
            #    `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.1.1/deploy/static/provider/cloud/deploy.yaml >> /root/initout.log 2>\&1`;

            # Install Dashboard
            #    `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/master/aio/deploy/alternative.yaml >> /root/initout.log`;
            #    `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v1.10.1/src/deploy/alternative/kubernetes-dashboard.yaml >> /root/initout.log`;
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml >> /root/initout.log`;

            # Create dashboard admin-useradmin-user
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f /usr/share/webmin/stabile/tabs/kubernetes/manifests/dashboard-user.yaml >> /root/initout.log 2>\&1`;

            # Get the dashboard ip address and set it in proxy
                my $dashline = `KUBECONFIG=/etc/kubernetes/admin.conf kubectl get Service -n $dashboardns | grep kubernetes-dashboard`;
                my $daship = $1 if ($dashline =~ /ClusterIP \s+ (\d+\.\d+\.\d+\.\d+)/) ;
                if ($daship) {
                    `perl -pi -e 's/dashboardip/$daship/' /etc/apache2/sites-available/kubernetes-ssl.conf`;
                }
            # Get the token
                #my $adminuser = `KUBECONFIG=/etc/kubernetes/admin.conf kubectl -n kubernetes-dashboard get sa/admin-user -o jsonpath="{.secrets[0].name}"`;
                my $token;
                #$token = `KUBECONFIG=/etc/kubernetes/admin.conf kubectl -n kubernetes-dashboard get secret $adminuser -o go-template="{{.data.token | base64decode}}"` if ($adminuser);
                #`echo "Got admin-user: $adminuser and token: $token" >> /root/initout.log`;
                # New method for Kubernetes 1.24: https://itnext.io/big-change-in-k8s-1-24-about-serviceaccounts-and-their-secrets-4b909a4af4e0
                $token = `KUBECONFIG=/etc/kubernetes/admin.conf kubectl -n $dashboardns create token admin-user --duration=999999h`;
                chomp $token;
                `echo "Got admin-user token: $token" >> /root/initout.log`;
                if ($token =~ /^ey/) {
                    `echo "$token" > /root/admin-user.token`;
                    `perl -pi -e 's/export KUBE_TOKEN=.*/export KUBE_TOKEN=$token/' /etc/apache2/envvars`;
                    `systemctl restart apache2`;
                } else {
                    sleep 15;
                    #$adminuser = `KUBECONFIG=/etc/kubernetes/admin.conf kubectl -n kubernetes-dashboard get sa/admin-user -o jsonpath="{.secrets[0].name}"`;
                    #$token = `KUBECONFIG=/etc/kubernetes/admin.conf kubectl -n kubernetes-dashboard get secret $adminuser -o go-template="{{.data.token | base64decode}}"` if ($adminuser);
                    $token = `KUBECONFIG=/etc/kubernetes/admin.conf kubectl -n $dashboardns create token admin-user --duration=999999h`;
                    `echo "Tried again and got admin-user token: $token" >> /root/initout.log`;
                    if ($token =~ /^ey/) {
                        `echo "$token" > /root/admin-user.token`;
                        `perl -pi -e 's/export KUBE_TOKEN=.*/export KUBE_TOKEN=$token/' /etc/apache2/envvars`;
                        `systemctl restart apache2`;
                    }
                }

            # Set strictARP to true as per instructions here: https://metallb.universe.tf/installation/
            # And install metallb
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl get configmap -n kube-system -o yaml > configmap.yaml && sed -i "s/strictARP:.*\$/strictARP: true/" configmap.yaml && kubectl replace -f configmap.yaml`;
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl create secret generic memberlist --from-literal=secretkey="\$(openssl rand -base64 128)"`;
            #    `perl -pi -e 's/ipstart/$ipstart/g' /usr/share/webmin/stabile/tabs/kubernetes/manifests/metallb.yaml`;
                `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f /usr/share/webmin/stabile/tabs/kubernetes/manifests/metallb.yaml`;

            # Install portainer
            #    `KUBECONFIG=/etc/kubernetes/admin.conf kubectl apply -f https://raw.githubusercontent.com/portainer/portainer-k8s/master/portainer.yaml`;

            # Add the default helm repo
                `KUBECONFIG=/etc/kubernetes/admin.conf /usr/sbin/helm repo add stable https://charts.helm.sh/stable`;
                `KUBECONFIG=/etc/kubernetes/admin.conf /usr/sbin/helm repo add bitnami https://charts.bitnami.com/bitnami`;

            # Make joincmd available to nodes
                `echo "$joincmd" > /usr/share/webmin/stabile/tabs/kubernetes/joincmd.sh`;
                `chmod 755 /usr/share/webmin/stabile/tabs/kubernetes/joincmd.sh`;

            # Make kubectl work for stabile user
                `mkdir /home/stabile/.kube`;
                `chown -R 1001:1001 /home/stabile/.kube`;
                `chown 1001:1001 /etc/kubernetes/admin.conf`;
#                `chmod 600 /etc/kubernetes/admin.conf`;
#                `chmod -R og+r /etc/kubernetes/`;
                `cp -i /etc/kubernetes/admin.conf /home/stabile/.kube/config`;
                `chown -R stabile:stabile /home/stabile/.kube`;

            # Make kubeconfig available for download
                `cp -i /etc/kubernetes/admin.conf /usr/share/webmin/stabile/kubeconfig`;
                `perl -pi -e 's/server: https.*/server: https:\\\/\\\/$extip:6443/' /usr/share/webmin/stabile/kubeconfig`;

                `echo "Done..." >> /root/initout.log`;
            } else {
                `echo "$kinit" > /root/initerr`
            }
        }
        # Limit access to apiserver (port 6443) and  bird (port 179)
        my $localnet = "$ipstart.0/24";
        print `iptables -D INPUT -p tcp --dport 6443 -s 127.0.0.1 -j ACCEPT 2>/dev/null`;
        print `iptables -D INPUT -p tcp --dport 6443 -s $localnet -j ACCEPT 2>/dev/null`;
        print `iptables -D INPUT -p tcp --dport 6443 -j DROP 2>/dev/null`;
        print `iptables -A INPUT -p tcp --dport 6443 -s 127.0.0.1 -j ACCEPT 2>/dev/null`;
        print `iptables -A INPUT -p tcp --dport 6443 -s $localnet -j ACCEPT 2>/dev/null`;
        print `iptables -A INPUT -p tcp --dport 6443 -j DROP 2>/dev/null`;

        print `iptables -D INPUT -p tcp --dport 179 -s 127.0.0.1 -j ACCEPT 2>/dev/null`;
        print `iptables -D INPUT -p tcp --dport 179 -s $localnet -j ACCEPT 2>/dev/null`;
        print `iptables -D INPUT -p tcp --dport 179 -j DROP 2>/dev/null`;
        print `iptables -A INPUT -p tcp --dport 179 -s 127.0.0.1 -j ACCEPT 2>/dev/null`;
        print `iptables -A INPUT -p tcp --dport 179 -s $localnet -j ACCEPT 2>/dev/null`;
        print `iptables -A INPUT -p tcp --dport 179 -j DROP 2>/dev/null`;

    } else {
        if (-e "/root/joincmd.sh") {
            ;
        } else {
            for (my $i=0; $i<20; $i++) {
                `echo "Getting joincmd from $mip" >> /root/initout.log`;
                my $head = `curl -I http://$mip:10000/stabile/tabs/kubernetes/joincmd.sh`;
                if ($head =~ /HTTP\/1\.0 200 Document/) {
                    my $joincmd = `curl http://$mip:10000/stabile/tabs/kubernetes/joincmd.sh`;
                    chomp $joincmd;
                    chomp $joincmd;
                    `echo '$joincmd' > /root/joincmd.sh`;
                    `chmod 755 /root/joincmd.sh`;
                    `/root/joincmd.sh >> /root/initout.log 2>\&1`;
                    last;
                }
                sleep 10;
            }
        }
    }
} else {
    `echo "Not ready $intip, $mip" > /root/initprob`;
}

sub show_management_server {
    # Try twice
    my $json_text = `curl -ks "https://$gw/stabile/systems/this"`;
    if ($json_text =~ /^\[/) {
        $json_array_ref = from_json($json_text);
        return $json_array_ref->[0];
    } else {
        sleep 5;
        $json_text = `curl -ks "https://$gw/stabile/systems/this"`;
        if ($json_text =~ /^\[/) {
            $json_array_ref = from_json($json_text);
            return $json_array_ref->[0];
        }
    }
}

sub get_internalip {
    my $internalip;
    if (!(-e "/tmp/internalip") && !(-e "/etc/stabile/internalip")) {
        $internalip = $1 if (`curl -sk https://$gw/stabile/networks/this` =~ /"internalip" : "(.+)",/);
        chomp $internalip;
        `echo "$internalip" > /tmp/internalip` if ($internalip);
        `mkdir /etc/stabile` unless (-e '/etc/stabile');
        `echo "$internalip" > /etc/stabile/internalip` if ($internalip);
    } else {
        $internalip = `cat /tmp/internalip` if (-e "/tmp/internalip");
        $internalip = `cat /etc/stabile/internalip` if (-e "/etc/stabile/internalip");
        chomp $internalip;
    }
    return $internalip;
}

sub get_externalip {
    my $externalip;
    if (!(-e "/tmp/externalip")) {
        $externalip = $1 if (`curl -sk https://$gw/stabile/networks/this` =~ /"externalip" : "(.+)",/);
        chomp $externalip;
        if ($externalip eq '--') {
            # Assume we have ens4 up with an external IP address
            $externalip = `ifconfig ens4 | grep -o 'inet addr:\\\S*' | sed -n -e 's/^inet addr://p'`;
            chomp $externalip;
        }
        `echo "$externalip" > /tmp/externalip` if ($externalip);
    } else {
        $externalip = `cat /tmp/externalip` if (-e "/tmp/externalip");
        chomp $externalip;
    }
    return $externalip;
}

