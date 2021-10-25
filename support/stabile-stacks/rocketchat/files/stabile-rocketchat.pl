#!/usr/bin/perl

use JSON;

my $dev = 'ens3';
$ip = $1 if (`ifconfig $dev` =~ /inet (\d+\.\d+\.\d+)\.\d+/);
$gw = "$ip.1" if ($ip);

my $appinfo_ref = get_appinfo();
if (!$appinfo_ref) {
    sleep 20;
    $appinfo_ref = get_appinfo();
}
if (!$appinfo_ref) {
    die "Unable to initialize Stabile API";
}
my %appinfo = %$appinfo_ref;
my $externalip = get_externalip();
my $dnsdomain =  $appinfo{dnsdomain};
my $dnssubdomain = $appinfo{'dnssubdomain'};
my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":"$externalip";

unless (`grep initialized /etc/mongod.conf`) {
    my $res = '';
    my $inc = 0;
    while ($inc < 10) {
        $res =  `mongo --eval "printjson(rs.initiate())"`;
        if ($res =~ /failed/) {
            `echo "$res" >> /tmp/rocketchat.out`;
            sleep 15;
            $inc++;
        } else {
            my  $hostname = `hostname`;
            chomp $hostname;
            print "Setting Site_Url to: https://$dom\n";
            `echo 'db.rocketchat_settings.update({"_id" : "Site_Url"},{\$set:{value:"https://$dom"}})' | mongo rocketchat`;
            `echo "# rocketchat initialized" >> /etc/mongod.conf`;
            print `systemctl restart rocketchat | tee -a /tmp/rocketchat.out \&2>1`;
            last;
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

sub get_appid {
    my $appid;
    if (!(-e "/tmp/appid")) {
        $appid = $1 if (`curl -sk https://$gw/stabile/servers?action=getappid` =~ /appid: (.+)/);
        chomp $appid;
        `echo "$appid" > /tmp/appid` if ($appid);
    } else {
        $appid = `cat /tmp/appid` if (-e "/tmp/appid");
        chomp $appid;
    }
    return $appid;
}

sub get_appinfo {
    my $appinfo;
    $appinfo = `curl -sk https://$gw/stabile/servers?action=getappinfo`;
    if ($appinfo =~ /^\{/) {
        my $json_hash_ref = from_json($appinfo);
        return $json_hash_ref;
    } else {
        return '';
    }
}
