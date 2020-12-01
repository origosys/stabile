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
if (-z '/etc/network/interfaces') {
    print "Writing interfaces file\n";
    my $interfaces = <<END
auto lo
iface lo inet loopback

auto ens3
iface ens3 inet static
    address $ip
    netmask 255.255.255.0
    network $net.0
    broadcast $net.255
    gateway $net.1
    dns-nameservers $net.1
    dns-search origo.io
END
;
    `echo "$interfaces" >> /etc/network/interfaces`;
    print `systemctl restart networking`;
} else {
    `perl -pi -e 's/address .+/address $ip/ unless (\$a); \$a=1;' /etc/network/interfaces`;
    `perl -pi -e 's/netmask .+/netmask 255.255.255.0/ unless (\$a); \$a=1;' /etc/network/interfaces`;
    `perl -pi -e 's/network .+/network $net.0/ unless (\$a); \$a=1;' /etc/network/interfaces`;
    `perl -pi -e 's/broadcast .+/broadcast $net.255/ unless (\$a); \$a=1;' /etc/network/interfaces`;
    `perl -pi -e 's/gateway .+/gateway $net.1/ unless (\$a); \$a=1;' /etc/network/interfaces`;
    `perl -pi -e 's/dns-nameservers .+/dns-nameservers $net.1/ unless (\$a); \$a=1;' /etc/network/interfaces`;
}
my $if = `ifconfig`;
if ($if =~ /10\.1\.1\.2/) {
    print `systemctl restart networking`;
}
