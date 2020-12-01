#!/usr/bin/perl

my $ip = `dmidecode | grep "SKU Number"`;
my $net;
if ($ip =~ /SKU Number: (\d+\.\d+\.\d+)\.(\d+)/) {
	$ip = "$1.$2";
	$net = "$1";
	print "Configuring IP address with $ip\n";
	`mkdir /etc/stabile` unless (-e '/etc/stabile');
	`echo "$ip" > /tmp/internalip` if ($net =~ /^10\./);
} else {
	die "No ip address found\n";
}
unless (`grep '$ip' /etc/sysconfig/network-scripts/ifcfg-eth0`) {
    print "Writing network script for eth0\n";
    my $interfaces = <<END
IPV4_FAILURE_FATAL=no
NETMASK=255.255.255.0
NETWORK=$net.0
IPADDR=$ip
BROADCAST=$net.255
DEVICE=eth0
ONBOOT=yes
IPV6_AUTOCONF=yes
IPV6_PRIVACY=no
IPV6_FAILURE_FATAL=no
IPV6_ADDR_GEN_MODE=stable-privacy
BOOTPROTO=none
TYPE=Ethernet
IPV6INIT=yes
PROXY_METHOD=none
BROWSER_ONLY=no
MTU=""
NAME=""
DEFROUTE=yes
GATEWAY=$net.1
MACADDR=""
IPV6_DEFROUTE=yes
AUTOCONNECT_PRIORITY=1
END
;
    `cp /etc/sysconfig/network-scripts/ifcfg-eth0 /root/ifcfg-eth0.bak`;
    `echo "$interfaces" > /etc/sysconfig/network-scripts/ifcfg-eth0`;
} else {
    `perl -pi -e 's/IPADDR=.+/IPADDR=$ip/ unless (\$a); \$a=1;' /etc/sysconfig/network-scripts/ifcfg-eth0`;
    `perl -pi -e 's/NETMASK=.+/NETMASK=255.255.255.0/ unless (\$a); \$a=1;' /etc/sysconfig/network-scripts/ifcfg-eth0`;
    `perl -pi -e 's/NETWORK=.+/NETWORK=$net.0/ unless (\$a); \$a=1;' /etc/sysconfig/network-scripts/ifcfg-eth0`;
    `perl -pi -e 's/BROADCAST=.+/BROADCASE=$net.255/ unless (\$a); \$a=1;' /etc/sysconfig/network-scripts/ifcfg-eth0`;
    `perl -pi -e 's/GATEWAY=.+/GATEWAY=$net.1/ unless (\$a); \$a=1;' /etc/sysconfig/network-scripts/ifcfg-eth0`;
}
#my $if = `ifconfig`;
#if (!($if =~ /$ip/)) {
#    print `systemctl restart NetworkManager`;
#}