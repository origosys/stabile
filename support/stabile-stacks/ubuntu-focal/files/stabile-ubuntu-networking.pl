#!/usr/bin/perl

my $ip = `dmidecode | grep "SKU Number"`;
my $net;
if ($ip =~ /SKU Number: (\d+\.\d+\.\d+)\.(\d+)/) {
	$ip = "$1.$2";
	$net = "$1";
	print "Configuring IP address with $ip\n";
	`mkdir /etc/stabile` unless (-e '/etc/stabile');
    # Generate new ssh keys on first run
    unless (-e "/etc/stabile/internalip") {
        `rm /etc/ssh/ssh_host_*`;
        `ssh-keygen -A`;
    }
    if ($net =~ /^10\./) {
        `echo "$ip" > /tmp/internalip`;
        `echo "$ip" > /etc/stabile/internalip`;
    }
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
    `perl -pi -e 's/address 10\..+/address $ip/' /etc/network/interfaces`;
    `perl -pi -e 's/network 10\..+/network $net.0/' /etc/network/interfaces`;
    `perl -pi -e 's/broadcast 10\..+/broadcast $net.255/' /etc/network/interfaces`;
    `perl -pi -e 's/gateway 10\..+/gateway $net.1/' /etc/network/interfaces`;
    `perl -pi -e 's/dns-nameservers 10\..+/dns-nameservers $net.1/' /etc/network/interfaces`;
    print `ifconfig ens3 0.0.0.0`; # This for some reason is necessary when a new address is assigned because of move
    print `systemctl restart networking`;
}
my $if = `ifconfig`;
if ($if =~ /10\.1\.1\.2/) {
    print `systemctl restart networking`;
}
