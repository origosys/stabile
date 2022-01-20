#!/usr/bin/perl

use JSON;

my $dev = 'ens3';
$ip = $1 if (`/sbin/ifconfig $dev` =~ /inet (\d+\.\d+\.\d+)\.\d+/);
$gw = "$ip.1" if ($ip);

my $appinfo_ref = get_appinfo();
if (!$appinfo_ref) {
    sleep 5;
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

my $miniopwd;
if (-e "/etc/stabile/miniopwd") {
    $miniopwd = `cat /etc/stabile/miniopwd`;
    chomp $miniopwd;
}
$miniopwd = `openssl rand -base64 12` unless ($miniopwd);
chomp $miniopwd;

my $intip = get_internalip();
if (`grep '127.0.0.1' /etc/apache2/conf-available/minio.conf`) {
    print `sed -i 's/127\.0\.0\.1/$intip/' /etc/apache2/conf-available/minio.conf`;
}

print "Starting Minio on $dom\n";
print `mc alias set minio/ http://$intip:9000 stabile "$miniopwd"`;
print `MINIO_ROOT_USER="stabile" MINIO_ROOT_PASSWORD="$miniopwd" MINIO_PROMETHEUS_URL="http://localhost:9090" MINIO_PROMETHEUS_AUTH_TYPE=public minio server /mnt/data --address "localhost:9000" --console-address "$dom:9001" | tee /tmp/minio.log`;

# Disable outside access to non-https
print `sudo iptables -D INPUT -p tcp --dport 9001 -s $intip -j ACCEPT 2>/dev/null`;
print `sudo iptables -D INPUT -p tcp --dport 9001 -j DROP 2>/dev/null`;
print `sudo iptables -A INPUT -p tcp --dport 9001 -s $intip -j ACCEPT`;
print `sudo iptables -A INPUT -p tcp --dport 9001 -j DROP`;

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
