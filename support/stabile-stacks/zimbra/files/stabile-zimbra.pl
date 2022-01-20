#!/usr/bin/perl

use JSON;

my $dev = 'ens3';
$ip = $1 if (`/sbin/ifconfig $dev` =~ /inet (\d+\.\d+\.\d+)\.\d+/);
$gw = "$ip.1" if ($ip);

my $action = shift if $ARGV[0];

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
my $zdoms;
$zdoms = `cat /etc/stabile/zimbradomains` if (-e "/etc/stabile/zimbradomains");
chomp $zdoms;

my $adoms = `sudo -u zimbra /opt/zimbra/bin/zmprov gad`;
while (!($adoms =~ /stabile\.int/)) { # Make sure Zimbra is alive before proceeding
    `echo "Waiting for Zimbra to start ($adoms)..." >> /tmp/zimbra.out`;
    sleep 20;
    $adoms = `sudo -u zimbra /opt/zimbra/bin/zmprov gad`;
}
unless ($zdoms && $zdoms =~ /$dom/) {
    print "Adding domain alias $dom\n";
    print `sudo -u zimbra /opt/zimbra/bin/zmprov createAliasDomain $dom stabile.int 2>\&1 | tee -a /tmp/zimbra.out`;
    print `sudo -u zimbra /opt/zimbra/bin/zmprov addAccountAlias admin\@stabile.int admin\@$dom 2>\&1 | tee -a /tmp/zimbra.out`;
    print `sudo -u zimbra /opt/zimbra/bin/zmprov mcf zimbraMtaSmtpdRejectUnlistedRecipient yes 2>\&1 | tee -a /tmp/zimbra.out`;
    print `sudo -u zimbra /opt/zimbra/bin/zmprov mcf zimbraMtaSmtpdRejectUnlistedSender yes 2>\&1 | tee -a /tmp/zimbra.out`;

    print `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$dom\&value=$dom\&type=MX" 2>\&1 | tee -a /tmp/zimbra.out`;

    # print `sudo -u zimbra /opt/zimbra/bin/zmlocalconfig -e postfix_smtpd_banner=`;
    # print `sudo -u zimbra /opt/zimbra/bin/zmlocalconfig -e zimbramtamyhostname=`;

    # print `sudo -u zimbra /opt/zimbra/bin/zmprov modifyConfig zimbraLogHostname zimbra.stabile.int`;
    # print `sudo -u zimbra /opt/zimbra/libexec/zmsetservername -n $dom`;
    # print `sudo -u zimbra /opt/zimbra/bin/zmprov -l rd stabile.io $dom`;
    # print `sudo -u zimbra /opt/zimbra/bin/zmprov modifyConfig zimbraDefaultDomainName $dom`;
    # print `sudo -u zimbra /opt/zimbra/bin/zmprov modifyConfig zimbraReverseProxyAvailableLookupTargets $dom`;
    # print `sudo -u zimbra /opt/zimbra/bin/zmprov modifyConfig zimbraReverseProxyUpstreamLoginServers $dom`;
    # print `sudo -u zimbra /opt/zimbra/bin/zmprov modifyConfig zimbraVersionCheckNotificationEmail admin\@$dom`;
    # print `sudo -u zimbra /opt/zimbra/bin/zmprov modifyConfig zimbraVersionCheckNotificationEmailFrom admin\@$dom`;
    # Update ressources referencing old domain
    # print `sudo -u zimbra /opt/zimbra/bin/zmlocalconfig -e av_notify_domain=$dom av_notify_user=admin\@$dom ldap_host=$dom ldap_master_url=ldap://$dom ldap_url=ldap://$dom:389 ldap_bind_url="ldap://$dom:389 ldap://127.0.0.1:389" smtp_destination=admin\@$dom smtp_source=admin\@$dom snmp_trap_host=$dom zimbra_server_hostname=$dom`;
    `echo "$dom" >> /etc/stabile/zimbradomains`;
}

if ($action eq "updatecerts") {
    if (-e "/root/.getssl/$dom/$dom.crt") {
    # `> /root/.getssl/$dom/root.crt`;
    #    `curl https://letsencrypt.org/certs/isrg-root-ocsp-x1.pem >> /root/.getssl/$dom/root.crt`;
    #    `curl https://letsencrypt.org/certs/isrg-root-x1-cross-signed.pem >> /root/.getssl/$dom/root.crt`;
        # DST Root CA X3
    #    print `curl https://censys.io/certificates/e255f7a2d4cfd3aa33c503b92d6994d49b9d003f2e949fafeb1d0817f83187a5/pem/raw >> /root/.getssl/$dom/x3-root.crt`;
    #    print `sudo -u zimbra /opt/zimbra/bin/zmcertmgr addcacert /root/.getssl/$dom/x3-root.crt`;
        # ISRG Root X1
    #    print `curl https://censys.io/certificates/6d99fb265eb1c5b3744765fcbc648f3cd8e1bffafdc4c2f99b9d47cf7ff1c24f/pem/raw >> /root/.getssl/$dom/x1-root.crt`;
    #    print `sudo -u zimbra /opt/zimbra/bin/zmcertmgr addcacert /root/.getssl/$dom/x1-root.crt`;
    #    `curl https://letsencrypt.org/certs/lets-encrypt-r3-cross-signed.pem >> /root/.getssl/$dom/root.crt`;
    #    `curl https://letsencrypt.org/certs/lets-encrypt-r3.pem >> /root/.getssl/$dom/root.crt`;
    #    `curl https://letsencrypt.org/certs/trustid-x3-root.pem.txt >> /root/.getssl/$dom/root.crt`;

    #    `cat /root/.getssl/$dom/fullchain.crt /root/.getssl/$dom/root.crt > /root/.getssl/$dom/combined.crt`;
        `cp /root/.getssl/$dom/fullchain.crt /tmp/fullchain.crt`;
        `chown zimbra:zimbra /tmp/fullchain.crt`;

        `cp /root/.getssl/$dom/$dom.key /opt/zimbra/ssl/zimbra/commercial/commercial.key`;
        `chown zimbra:zimbra /opt/zimbra/ssl/zimbra/commercial/commercial.key`;

        `cp /root/.getssl/$dom/$dom.crt /tmp/$dom.crt`;
        `chown zimbra:zimbra /tmp/$dom.crt`;
        print `cd /opt/zimbra/; sudo -u zimbra /opt/zimbra/bin/zmcertmgr deploycrt comm /tmp/$dom.crt /tmp/fullchain.crt 2>\&1 | tee -a /tmp/zimbra.out`;
        # Self-signed certs to localhost no longer work which prevents /opt/zimbra/libexec/zmstatuslog from connecting, so change ldap
        print `sudo -u zimbra /opt/zimbra/bin/zmlocalconfig -e ldap_host=$dom ldap_url=ldap://$dom:389 ldap_master_url=ldap://$dom:389 ldap_bind_url=ldap://$dom:389 2>\&1 | tee -a /tmp/zimbra.out`;
        print `rm /opt/zimbra/zmstat/pid/*`;

        #my $archname = 'x86_64-linux-gnu-thread-multi'; #/usr/bin/perl -V:archname
        # my $zcmdprefix = qq|cd /opt/zimbra/; sudo -u zimbra JYTHONPATH=/opt/zimbra/common/lib/jylibs SNMPCONFPATH=/opt/zimbra/conf PERLLIB=/opt/zimbra/common/lib/perl5/$archname:/opt/zimbra/common/lib/perl5 PERLLIB=/opt/zimbra/common/lib/perl5/$archname:/opt/zimbra/common/lib/perl5 JAVA_HOME=/opt/zimbra/common/lib/jvm/java PATH=/opt/zimbra/bin:\${JAVA_HOME}/bin:/opt/zimbra/common/bin:/opt/zimbra/common/sbin:/usr/sbin:\${PATH}|;
        #my $zcmdpostfix = " 2>\&1 | tee -a /tmp/zimbra.out &";

        `echo "Restarting Zimbra" >> /tmp/zimbra.out`;
        print `cd /opt/zimbra/; su - zimbra -c "/opt/zimbra/bin/zmcontrol restart 2>\&1" | tee -a /tmp/zimbra.out \&`;
#        print `$zcmdprefix /opt/zimbra/bin/zmopendkimctl start $zcmdpostfix`;
#        print `$zcmdprefix /opt/zimbra/bin/zmstatctl restart $zcmdpostfix`;
#        print `$zcmdprefix /opt/zimbra/bin/zmlogswatchctl restart $zcmdpostfix`;
#        print `$zcmdprefix /opt/zimbra/bin/zmswatchctl restart $zcmdpostfix`;
    } else {
        print "No cert found in /root/.getssl/$dom - please configure getssl manually or try running stabile-ubuntu.pl\n";
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
