#!/usr/bin/perl

use JSON;
use Time::HiRes qw( time );


my $dev = 'eth0';
$dev = 'ens3';
my $ipstart = $1 if (`ifconfig $dev` =~ /inet (\d+\.\d+\.\d+)\.\d+/);
my $gw = "$ipstart.1" if ($ipstart);

my $intip = get_internalip();
my $mip;
my $mserver = show_management_server();
if ($mserver) {
    $mip = $mserver->{internalip};
}

if ($intip && $mip) {
    if (-e "/root/initout.log" && `grep Done /root/initout.log`) {
        print "MongoDB has already been initialized on this server\n";
    } else {
        # Add search domain to resolver
        my $dom_json = `curl -k https:/$gw//stabile/networks?action=getdnsdomain`;
        my $dom_obj = from_json($dom_json);
        my $searchdom = $mip . '.' . $dom_obj->{subdomain} . '.' . $dom_obj->{domain};
        `echo "search $searchdom" >> /etc/resolv.conf` unless (`grep "$searchdom" /etc/resolv.conf`);

        if ($intip eq $mip) { # We are on the main server - use as query router
            unless (`grep forking /etc/systemd/system/stabile-mongodb.service`) {
                # Add host to DNS with internal IP
                `hostnamectl set-hostname mongo-router`;
                `curl -k "https://$gw/stabile/networks?action=dnsdelete&name=mongo-router.$searchdom&type=A" > /root/initout.log`;
                `curl -k "https://$gw/stabile/networks?action=dnscreate&name=mongo-router.$searchdom&value=$intip&type=A" > /root/initout.log`;
                `perl -pi -e 's/ubuntu-focal-base/mongo-router/;' /etc/hosts`;

                # Create cluster certificate and copy to nodes
                `chmod -R g+rw /etc/ssl/private`;
                `chown :ssl-cert /etc/ssl/private/stabile.key`;
                `usermod -a -G ssl-cert mongodb`;
                `openssl rand -base64 756 > /etc/mongod.key`;
                `cp /etc/mongod.key /usr/share/webmin/stabile/tabs/mongodb/mongod.key`;
#                `stabile-helper runcommand "curl http://mongo-router:10000/stabile/tabs/mongodb/mongod.key > /etc/mongod.key"`;
                `chown mongodb:mongodb /etc/mongod.key`;
                `chmod 400 /etc/mongod.key`;

                # Generate initial password for stabile user
                `openssl rand -base64 12 > /etc/mongod.pass`;
                `cp /etc/mongod.pass /usr/share/webmin/stabile/tabs/mongodb/mongod.pass`;
                `chmod 660 /etc/mongod.pass`;
                `chown :ssl-cert /etc/mongod.pass`;

                # Disable mongod
                `systemctl stop mongod | tee /root/initout.log 2>\&1`;
                `systemctl disable mongod | tee /root/initout.log 2>\&1`;
                `perl -pi -e 's/Type=.*/Type=forking\nUser=mongodb\nRestart=always\nRestartSec=1/;' /etc/systemd/system/stabile-mongodb.service`;
                `systemctl daemon-reload | tee /root/initout.log 2>\&1`;
                `systemctl restart stabile-mongodb.service | tee /root/initout.log 2>\&1`;
                `exit 0`;
            }
            # Make ssl cert available
            `cp -a /etc/ssl/private/stabile.crt /tmp/mongodb.crt`;
            `cat /etc/ssl/private/stabile.key >> /tmp/mongodb.crt`;
            # Connect to config server
            print `mongos --keyFile /etc/mongod.key --bind_ip_all --fork --syslog --configdb config/mongo-config:27017 --tlsMode allowTLS --tlsCertificateKeyFile /tmp/mongodb.crt --tlsCAFile /etc/ssl/private/stabile.chain --tlsAllowConnectionsWithoutCertificates  | tee /tmp/mongoout.log 2>\&1`;
            # Add stabile user
            my $pwd = `cat /etc/mongod.pass`;
            chomp $pwd;
            `echo "db.getSiblingDB('admin').createUser({user:'stabile',pwd:'$pwd', roles:[{role:'userAdminAnyDatabase',db:'admin'},{role:'clusterAdmin',db:'admin'},{role:'root',db:'admin'}]})" | mongo`;
        } else {
            my $system_json = `curl -k https://$gw/stabile/systems/me`;
            my $systems_obj = from_json($system_json);
            my @children = @{$systems_obj->[0]->{children}};
            @children = sort {$b->{'internalip'} lt $a->{'internalip'}} @children;
            if ($intip eq $children[1]->{'internalip'}) { # We are on the second server in stack, use as config server
                # Add host to DNS with internal IP
                `hostnamectl set-hostname mongo-config`;
                `curl -k "https://$gw/stabile/networks?action=dnsdelete&name=mongo-config.$searchdom&type=A" > /root/initout.log`;
                `curl -k "https://$gw/stabile/networks?action=dnscreate&name=mongo-config.$searchdom&value=$intip&type=A" > /root/initout.log`;
                `perl -pi -e 's/ubuntu-focal-base/mongo-config/;' /etc/hosts`;
                # Create DB dir and edit mongod.conf
                `mkdir /mnt/data/mongodb`;
                `chown mongodb:mongodb /mnt/data/mongodb`;
                `perl -pi -e 's/dbPath:.*/dbPath: \\/mnt\\/data\\/mongodb/;' /etc/mongod.conf`;
                `perl -pi -e 's/#replication:/replication:\n  replSetName: "config"/;' /etc/mongod.conf`;
                `perl -pi -e 's/#sharding:/sharding:\n  clusterRole: configsvr/;' /etc/mongod.conf`;
                `perl -pi -e 's/#security:/security:\n  keyFile: \\/etc\\/mongod.key/;' /etc/mongod.conf`;
                # Initiate Mongo
                while (!(-s "/etc/mongod.key")) {
                    print "+"; sleep 1;
                    my $key = `curl http://mongo-router:10000/stabile/tabs/mongodb/mongod.key`;
                    chomp $key;
                    `echo "$key" > /etc/mongod.key` unless ($key =~ /not found/ || !$key);
                }
                `chown mongodb:mongodb /etc/mongod.key`;
                `chmod 400 /etc/mongod.key`;
                `systemctl restart mongod | tee /root/initout.log 2>\&1`;
                while (`echo "" | mongo` =~ /failed/) {print "."; sleep 1;}
                my $res = `echo "rs.initiate()" | mongo | tee /root/initout.log 2>\&1`;
                print "$res\n";
                if ($res =~ /"ok" : 1/s) {
                    `echo "Done..." >> /root/initout.log`;
                } else {
                    `echo "$res" > /root/initerr`
                }
            } else { # We are on the third or higher server in stack, use as shard server
                my $snum;
                my $i = -1;
                foreach my $child (@children) {
                    if ($child->{'internalip'} eq $intip) {
                        $snum = $i;
                        last;
                    }
                    $i++;
                }
                my $hostname = "mongo-shard$i";
                # Add host to DNS with internal IP
                `hostnamectl set-hostname $hostname`;
                `curl -k "https://$gw/stabile/networks?action=dnsdelete&name=$hostname.$searchdom&type=A" > /root/initout.log`;
                `curl -k "https://$gw/stabile/networks?action=dnscreate&name=$hostname.$searchdom&value=$intip&type=A" > /root/initout.log`;
                `perl -pi -e 's/ubuntu-focal-base/$hostname/;' /etc/hosts`;
                # Create DB dir and edit mongod.conf
                `mkdir /mnt/data/mongodb`;
                `chown mongodb:mongodb /mnt/data/mongodb`;
                `perl -pi -e 's/dbPath:.*/dbPath: \\/mnt\\/data\\/mongodb/;' /etc/mongod.conf`;
                `perl -pi -e 's/#replication:/replication:\n  replSetName: "shard$i"/;' /etc/mongod.conf`;
                `perl -pi -e 's/#sharding:/sharding:\n  clusterRole: shardsvr/;' /etc/mongod.conf`;
                `perl -pi -e 's/#security:/security:\n  keyFile: \\/etc\\/mongod.key/;' /etc/mongod.conf`;
                # Initiate Mongo
                while (!(-s "/etc/mongod.key")) {
                    print "+"; sleep 1;
                    my $key = `curl http://mongo-router:10000/stabile/tabs/mongodb/mongod.key`;
                    chomp $key;
                    `echo "$key" > /etc/mongod.key` unless ($key =~ /not found/ || !$key);
                }
                `chown mongodb:mongodb /etc/mongod.key`;
                `chmod 400 /etc/mongod.key`;
                `systemctl restart mongod | tee /root/initout.log 2>\&1`;
                while (`echo "" | mongo` =~ /failed/) {print "."; sleep 1;}
                my $res = `echo "rs.initiate()" | mongo | tee /root/initout.log 2>\&1`;
                print "$res\n";
                # Get password from router
                while (!(-s "/etc/mongod.pass")) {
                    print "+"; sleep 1;
                    my $key = `curl http://mongo-router:10000/stabile/tabs/mongodb/mongod.pass`;
                    chomp $key;
                    `echo "$key" > /etc/mongod.pass` unless ($key =~ /not found/ || !$key);
                }
                `chmod 600 /etc/mongod.pass`;
                my $pwd = `cat /etc/mongod.pass`;
                chomp $pwd;
                $res = '';
                while (!($res =~ /"ok" : 1/s)) {
                    # Add this shard server to router
                    $res = `echo 'sh.addShard("shard$i/mongo-shard$i:27017")' | mongo --host mongo-router -u stabile -p $pwd | tee /root/initout.log 2>\&1`;
                    sleep 1;
                    print "$res\n";
                }
                `echo "Done..." >> /root/initout.log`;
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
