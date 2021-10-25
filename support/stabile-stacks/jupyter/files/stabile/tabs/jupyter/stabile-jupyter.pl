#!/usr/bin/perl

use JSON;

my $dev = 'ens3';
$ip = $1 if (`ifconfig $dev` =~ /inet (\d+\.\d+\.\d+)\.\d+/);
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

unless (-e '/etc/jupyter.seeded') {
    print `perl -pi -e 's/ubuntu-xenial/jupyter/g' /etc/hosts`;
    `touch /etc/jupyter.seeded`;
}
#my $sslconf = "/etc/apache2/sites-available/000-default-le-ssl.conf";
#print `perl -pi -e 's/.*\\\/VirtualHost.*/\\\tProxyPass \\\/ http:\\\/\\\/127.0.0.1:8888\\\/ \\\n\\\tProxyPassReverse \\\/ http:\\\/\\\/127.0.0.1:8888\\\/\\\n<\\\/VirtualHost>/' $sslconf` unless ( !(-e $sslconf) || `grep ProxyPass $sslconf`);

print `perl -pi -e "s/.*c\\.NotebookApp\\.port =.*/c.NotebookApp.port = 8889/" /home/stabile/.jupyter/jupyter_notebook_config.py`;
print `perl -pi -e "s/.*c\\.NotebookApp\\.ip =.*/c.NotebookApp.ip = '$internalip'/" /home/stabile/.jupyter/jupyter_notebook_config.py`;
print `perl -pi -e 's/#c.NotebookApp.ssl_options.*/import ssl\nc.NotebookApp.ssl_options={\n"ssl_version": ssl.PROTOCOL_TLSv1_2\n}/' /home/stabile/.jupyter/jupyter_notebook_config.py`;

my $certfile = "/home/stabile/.jupyter/ssl-cert-snakeoil.pem";
my $keyfile = "/home/stabile/.jupyter/ssl-cert-snakeoil.key";

if (-e "/etc/ssl/private/stabile.crt") {
    print `cp -L /etc/ssl/private/stabile.* /home/stabile/.jupyter/`;
    print `cat /etc/ssl/private/stabile.chain >> /home/stabile/.jupyter/stabile.crt`;
    $certfile = "/home/stabile/.jupyter/stabile.crt";
    $keyfile = "/home/stabile/.jupyter/stabile.key";
} else {
    print `cp /etc/ssl/certs/ssl-cert-snakeoil.pem /home/stabile/.jupyter`;
    print `cp /etc/ssl/private/ssl-cert-snakeoil.key /home/stabile/.jupyter`;
}
`chown stabile:stabile /home/stabile/.jupyter/*`;

print `su stabile -c "/home/stabile/anaconda/bin/jupyter notebook --config=/home/stabile/.jupyter/jupyter_notebook_config.py --notebook-dir=/home/stabile/notebooks --certfile=$certfile --keyfile=$keyfile"`;


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
