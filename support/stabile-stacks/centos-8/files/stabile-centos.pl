#!/usr/bin/perl

use JSON;
use Text::ParseWords;
use Data::Dumper;

my $registered;
my $internalip;
my $i;

my $action = shift if $ARGV[0];

my $webminhome = '/usr/libexec/webmin';
my $apache = 'httpd';
my $ip;
my $gw;
$ip = $1 if (`ifconfig eth0` =~ /inet (\d+\.\d+\.\d+)\.(\d+)/);
if ($ip) {
    $gw = "$ip.1";
    $internalip = "$1.$2";
}

if ($action eq 'mountpools') {
    print `curl --silent http://localhost:10000/stabile/index.cgi?action=mountpools`;
    exit 0;
} elsif  ($action eq 'initapps') {
    print `curl --silent http://localhost:10000/stabile/index.cgi?action=initapps`;
    exit 0;
} elsif  ($action eq 'activateapps') {
    print `curl --silent http://localhost:10000/stabile/index.cgi?action=activateapps`;
    exit 0;
} elsif ($action eq 'liststorage') {
    my $cmd = q/LANG=en df -h | tr -s ' ' ',' | jq -nR '[( input | split(",") ) as $keys | ( inputs | split(",") ) as $vals | [ [$keys, $vals] | transpose[] | {key:.[0],value:.[1]} ] | from_entries ]'/;
    my $json = `$cmd`;
    my $jobj = from_json($json);
    my %filesystems;
    foreach my $fs (@{$jobj}) {
        if ($fs->{Filesystem} =~ /\/dev\/(\w+)/) {
            $fs->{Name} = $1;
            $filesystems{$1} = $fs;
        }
    }

    $cmd = q|lsblk --json|;
    my $json2 = `$cmd`;
    my $jobj2 = from_json($json2);
    foreach my $fs (@{$jobj2->{blockdevices}}) {
        if ($fs->{children}) {
            foreach my $fs2 (@{$fs->{children}}) {
                if ($filesystems{$fs2->{name}}) {
                    delete $filesystems{$fs2->{name}}->{on};
                    $filesystems{$fs2->{name}}->{Blocksize} = $fs2->{size};
                }
            }
        }
    }
    my @fslist;
    foreach my $k (keys %filesystems) {
        push @fslist, $filesystems{$k};
    }
    print to_json(\@fslist, {pretty=>1});
    exit 0;


} elsif  ($action eq 'resizestorage') {
    my $rsize = $ARGV[0];
    my $dev = $ARGV[1] || 'vdb';
    if ($rsize>0) {
        print "resizing $dev $rsize...\n";
        print "Unmount partition\n";
        my $res = `umount /mnt/data`;
        sleep 1;
        print "Detaching image\n";
        $res = `curl -k --silent https://$gw/stabile/servers?action=detach`;
        print $res;
        my $imguuid;
        $imguuid = $1 if ($res =~ /(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})/);
        if ($imguuid) {
            print "Resizing image to $rsize\n";
            $res = `curl -k --silent "https://$gw/stabile/images/$imguuid?action=sync_save\&virtualsize=$rsize"`;
            print $res;
            sleep 2;
            print "Re-attaching image $imguuid\n";
            $res = `curl -k --silent "https://$gw/stabile/servers?action=attach\&image=$imguuid"`;
            print $res;
            sleep 1;
            my $blks = `lsblk -l`;
            print "Found blockdevices:\n$blks\n";
            $dev = '';
            my $dev0 = 'vdb';
            if ($blks =~ /vdb1/) {$dev = 'vdb1';}
            if ($blks =~ /vdc1/ && !($blks =~ /vdb1/)) {$dev = 'vdc1'; $dev0 = 'vdc';} # Device got attached to vdc instead of vdb - it happens...
            if ($dev) {
                print "Growing partition 1 on $dev\n";
                print `umount /mnt/data`;
                $res = `growpart /dev/$dev0 1`;
                print "Checking /dev/$dev\n";
                $res .= `e2fsck -fy /dev/$dev`;
                $res .= `resize2fs /dev/$dev`;
                print $res;
                print "Remounting partition $dev on /mnt/data\n";
                $res = `mount /dev/$dev /mnt/data`;
                print $res;
                print "Done.\n";
            } else {
                print "Unable to grow partition - not found. Please correct manually.\n";
            }
        }
    } else {
        print "Usage: stabile-helper resizestorage <size> [device]\n";
    }
    exit 0;
}

if (-e '/etc/webmin/') {
    while (!$registered && $i<20) {
        $internalip = $internalip || get_internalip();
        my $res = `curl http://$internalip:10000/stabile/index.cgi?action=registerwebminserver`;
        $registered = ($res =~ /Registered at \S+/);
        chomp $registered;
        if ($registered) {
            `echo "$internalip: $res" >> /tmp/stabile-registered`;
        } else {
            `echo "$internalip: $res" >> /tmp/stabile-registered`;
            sleep 5;
        };
        $i++;
    }
} else {
    print "Webmin not installed, not registering server\n";
}

$externalip = `cat /tmp/externalip` if (-e '/tmp/externalip');
$externalip = `cat /etc/stabile/externalip` if (-e '/etc/stabile/externalip');
chomp $externalip;

my $appinfo = `curl -ks "https://$gw/stabile/servers?action=getappinfo"`;
my $info_ref = from_json($appinfo);
my $status = $info_ref->{status};
my $uuid = $info_ref->{uuid};
my $dnsdomain = $info_ref->{dnsdomain};
my $name = $info_ref->{name};
$name =~ s/ //g;

if ($status eq 'upgrading') {
    print "Upgrading this server...\n";
    `echo "restoring" > /tmp/restoring` unless ( -e "/tmp/restoring");

    # Mount storage pools and locate source dir
    my $json_text = `curl -ks "https://$gw/stabile/images?action=liststoragepools"`;
    my $spools_ref = from_json($json_text);
    my @spools = @$spools_ref;
    my $mounts = `cat /proc/mounts`;
    my @restoredirs;

    my $json_text = `curl -ks "https://$gw/stabile/users/me"`;
    if ($json_text =~ /^\[/) {
        my $json_hash_ref = from_json($json_text);
        my $me_ref = $json_hash_ref->[0];
        $user = $me_ref->{username};
    }

    if ($user) {
        foreach my $pool (@spools) {
            next if ($pool->{id} == -1);
            next unless ($pool->{mountable});
            my $sid = "pool" . $pool->{id};
            my $spath = $pool->{path};
            my $shostpath = $pool->{hostpath};
            unless ($mounts =~ /\/mnt\/fuel\/$sid/) {
            `mkdir -p /mnt/fuel/$sid` unless (-e "/mnt/fuel/$sid");
                my $mounted;
                if ($shostpath eq 'local') {
                    $mounted = `mount $gw:$spath/$user/fuel /mnt/fuel/$sid`;
                } else {
                    $mounted = `mount $shostpath/$user/fuel /mnt/fuel/$sid`;
                }
            }
            my $srcloc = "/mnt/fuel/$sid/upgradedata/$uuid";
            push @restoredirs, $srcloc if (-e $srcloc); # If upgrade data exists, restore from this dir
        }
        # Read in libs for tabs
        opendir(DIR,"$webminhome/stabile/tabs") or die "Cannot open tabs directory\n";
        my @dir = readdir(DIR);
        closedir(DIR);
        my @tabs;
        foreach my $tab (@dir) {
            next if ($tab =~ /\./);
            print "Sourcing $tab-lib.pl\n" if (-e "$webminhome/stabile/tabs/$tab/$tab-lib.pl");
            require "$webminhome/stabile/tabs/$tab/$tab-lib.pl";
        }

        # Ask each library to do the actual restore
        foreach my $tab (@dir) {
            next if ($tab =~ /\./);
            foreach my $srcloc (@restoredirs) {
                my $res = $tab->("restore", {sourcedir=>$srcloc}) if (defined &$tab && $srcloc);
                $res =~ s/\n/ /g;
                print "$tab, $srcloc: $res\n";
                `echo "$res" >> /tmp/restore.log`;
            }
        }
    } else {
        print "Unable to get user.\n";
    }

    unlink ("/tmp/restoring");
    # Done copying data back, change status from upgrading to running
    print `curl -ks "https://$gw/stabile/servers?action=setrunning"`;

} else {
    print "Server is $status. Looking for shellinabox...\n";
    if (-e '$webminhome/stabile/tabs/servers/shellinaboxd') {
#        unless (`pgrep shellinaboxd`) {
        print "Opening ports for shellinabox...\n";
        # Disallow shellinabox access from outside
        my $gw = $internalip;
        $gw = "$1.1" if ($gw =~ /(\d+\.\d+\.\d+)\.\d+/);
        print `iptables -D INPUT -p tcp --dport 4200 -s $gw -j ACCEPT`;
        print `iptables -D INPUT -p tcp --dport 4200 -j DROP`;
        print `iptables -A INPUT -p tcp --dport 4200 -s $gw -j ACCEPT`;
        print `iptables -A INPUT -p tcp --dport 4200 -j DROP`;

        my $title = $externalip || $internalip;
        if (-e '$webminhome/stabile/tabs/servers/ShellInABox.js') {
            print "Updating terminal title to $title\n";
            `perl -pi -e 's/^document.title = ".*";/document.title = "Term:$title";/' $webminhome/stabile/tabs/servers/ShellInABox.js`;
        }
    }
    get_internalip();
    # Add hostname to hosts
    my $hostname = $name;
    `hostname "$hostname"`;
    `echo "$hostname" > /etc/hostname`;
    unless (`grep $hostname /etc/hosts`) {
        `perl -pi -e 's/(127.+localhost.*)/\$1 $hostname/;' /etc/hosts`
    }
    # Run getssl
    if ($externalip) {
        my $res = `ping -c1 -w2 1.1.1.1`;
        if ($res =~ /100\% packet loss/) {
            print "No Internet connectivity - not running letsencrypt\n";
        } elsif ($externalip =~ /^192\.168\./){
            print "External IP is RFC 1819 - not running GetSSL\n";
        } elsif ($dnsdomain) {
            print "Running GetSSL\n";
            if (-e "/root/.getssl/$externalip.$dnsdomain") {
                print `getssl -a`;
            } else {
                print `mkdir -p /root/.getssl/$externalip.$dnsdomain`;
                my $getsslcfg = <<END
CA="https://acme-v02.api.letsencrypt.org"
PRIVATE_KEY_ALG="rsa"
ACL=("/var/www/.well-known/acme-challenge")
DOMAIN_CERT_LOCATION="/etc/ssl/certs/stabile.crt"
DOMAIN_KEY_LOCATION="/etc/ssl/certs/stabile.key"
CA_CERT_LOCATION="/etc/ssl/certs/stabile.chain"
RELOAD_CMD="systemctl reload $apache"
END
;
                print `echo '$getsslcfg' > /root/.getssl/$externalip.$dnsdomain/getssl.cfg'`;
                print `letsencrypt -d $externalip.$dnsdomain --email=cert\@$dnsdomain --agree-tos --no-redirect --noninteractive --apache`;
            }
            if (-e "/etc/ssl/certs/stabile.crt") {
                my $reloadapache;
                if (!(`grep stabile /etc/$apache/sites-available/webmin-ssl.conf`)) {
                    `perl -pi -e 's/SSLCertificateFile .+/SSLCertificateFile \/etc\/ssl\/certs\/stabile.crt/' /etc/$apache/sites-available/*ssl.conf`;
                    `perl -pi -e 's/SSLCertificateKeyFile .+/SSLCertificateFile \/etc\/ssl\/certs\/stabile.key/' /etc/$apache/sites-available/*ssl.conf`;
                    `perl -pi -e 's/#SSLCertificateChainFile .+/SSLCertificateFile \/etc\/ssl\/certs\/stabile.chain/' /etc/$apache/sites-available/*ssl.conf`;
                    $reloadapache = 1;
                }
                `systemctl reload $apache` if ($reloadapache);
            }
            `systemctl reload apache2` if ($reloadapache);
        }
    }
}

sub get_internalip {
    my $intip;
    if (!(-e "/tmp/internalip") && !(-e "/etc/stabile/internalip")) {
        $intip = $1 if (`curl -sk https://$gw/stabile/networks/this` =~ /"internalip" : "(.+)",/);
        chomp $intip;
        `echo "$intip" > /tmp/internalip` if ($intip);
        `mkdir /etc/stabile` unless (-e '/etc/stabile');
    } else {
        $intip = `cat /tmp/internalip` if (-e "/tmp/internalip");
        $intip = `cat /etc/stabile/internalip` if (-e "/etc/stabile/internalip");
        chomp $intip;
    }
    `echo "$intip" > /etc/stabile/internalip` if ($intip);
    `ssh-keygen -A` unless (-e "/etc/stabile/internalip"); # Generate ssh host keys
    return $intip;
}
