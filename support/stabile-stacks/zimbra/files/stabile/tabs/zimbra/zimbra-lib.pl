#!/usr/bin/perl

use JSON;
use Digest::SHA qw(sha1_base64 sha1_hex);
use Digest::MD5 qw(md5 md5_hex md5_base64);
use URI::Escape::XS qw(uri_escape uri_unescape);

my $dnsdomain =  $appinfo{dnsdomain};
my $dnssubdomain = $appinfo{'dnssubdomain'};
my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":"$externalip";
my $esc_dnsdomain = $dnsdomain;
$esc_dnsdomain =~ s/\./\\./g;


my $aliases = `cat /root/.getssl/$dom/getssl.cfg | grep SANS=`;
if ($aliases =~ /SANS="(.+)"/) {
    $aliases = $1;
    $aliases = join(' ', split(/, ?/, $aliases));
} else {
    $aliases = '';
}
my $sans = '';

sub zimbra {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};
    my $meref = show_me();

    if ($action eq 'form' || $action eq 'zimbraform') {
        my $form;

        my $letsencrypt = (-e "/root/.getssl/$dom/getssl.cfg")?" checked":'';
        my $renewbtn = ($letsencrypt)?qq|<button type="button" onclick="\$('#mycheck').val('2'); salert('Hang on - this could take a minute or two...'); limitZimbraSpinner('zimbradomains'); return false;" class="btn btn-info btn-sm kubebutton">install certificates</button>|:'';
        my $links = qq|<a href="https://$dom" target="_blank">$dom</a>|;
#        my $maildoms = '';
        foreach my $alias (split(/ /, $aliases)) {
            $links .= qq| / <a href="https://$alias" target="blank">$alias</a>|;
#            $maildoms .= $2 if ($alias =~ /(?!\.)\.(.+)/);
        }

        my $running = `systemctl is-active stabile-zimbra`;
        chomp $running;
        $running = 1 unless ($running =~ /inactive/);
        my $setupdone = (glob("/opt/zimbra/log/zmsetup.*.log"))?1:0;
        unless ($running && $setupdone) {
            my $status = `tail -n 15 /tmp/zmsetup.*.log`;
            $form .= <<END
    <script>
        setTimeout(function() {
            \$.get("index.cgi?action=zimbraform&tab=zimbra", function(result) {
                \$("#zimbra").html(result);
            });
        }, 3000);
    </script>
    <div class="tab-pane container" id="zimbra">
        <table><tr><td>
            <div class="sk-wave">
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
            </div>
        </td><td>
            <h5 style="margin-left: 20px;">Preparing Zimbra - this may take a few minutes...</h5>
        </td><tr></table>
        <pre>$status
        </pre>
    </div>
END
        } else {
            # my $zdom = `sudo -u zimbra /opt/zimbra/bin/zmprov gacf | grep "zimbraDefaultDomainName: " | sed -n "/zimbraDefaultDomainName: /s/zimbraDefaultDomainName: //p"`; # This takes about 5 seconds...

            $form .= <<END
        <form class="passwordform" id="zimbrapassword_form" action="index.cgi?action=changezimbrapassword&tab=zimbra" method="post" onsubmit="limitZimbraSpinner('zimbrapassword'); \$('#zimbrapassword').val(''); return false;" accept-charset="utf-8" autocomplete="off">
            <div>
                Here you can manage some basic settings for your zimbra installation.
            </div>
            <small>Set the password for the zimbra user "admin" in the default domain:</small>
            <div class="row">
                <div class="col-sm-10">
                    <input type="password" id="zimbrapassword" name="zimbrapassword" autocomplete="off" value="" class="password kubebutton">
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default kubebutton" type="submit" id="zimbrapassword_button">Set!</button>
                </div>
            </div>
            <small style="margin-top:10px;">
                After setting the password you can <a target="_blank" href="https://$dom:7071">log in here</a> as user "admin" with your password to manage your Zimbra server, or log into the <a target="_blank" href="https://$dom">webmail interface</a>.
            </small>
        </form>

        <form class="passwordform" id="zimbradomains_form" action="index.cgi?action=zimbradomains&tab=zimbra" method="post" onsubmit="limitZimbraSpinner('zimbradomains'); return false;" accept-charset="utf-8" autocomplete="off">
            <input type="hidden" id="mycheck" name="mycheck" value="1" />
            <div><small>Server aliases:</small></div>
            <div class="row">
                <div class="col-sm-10">
                    <input class="zimbradomains" id="zimbradomains" type="text" name="zimbradomains" value="$aliases" autocomplete="off" />
                </div>
                <div class="col-sm-2">
                    <button type="submit" id="zimbradomains_button" class="btn btn-default" rel="tooltip" data-placement="top" title="If domain is not a FQDN, it will be created in the $dnsdomain domain as [alias].$dnsdomain">Set!</button>
                </div>
            </div>
            <div class="small" style="margin-top:10px;">
                    Your Zimbra server is reachable at $links. To receive mail, add aliases above. Try sending an email to <a href="mailto:admin\@$dom">admin\@$dom</a> to test connectivity<br>
            </div>
            <div class="small" style="margin-top:20px;">
                If an alias does not contain a dot, A-, MX-, SPF-, DKIM- and DMARC-records are added to the $dnsdomain zone.
                If an alias contains a dot it is assumed that you handle DNS configuration yourself.
                DNS entries can be <a href="http://$dom/dns/" target="_blank">found here</a>.<br>
                In both cases a domain alias is created in Zimbra pointing to $dom. If you want your new domain to be an independent email domain, you can safely delete this domain alias.<br>
            </div>
            <div style="display:inline-block; margin-top:16px;">
                <small>Obtain Let's Encrypt certificate and install it on this mail server $renewbtn</small>
                <div class="small">
                    Will try to obtain certificates for: $dom $aliases
                </div>
            </div>
        </form>
END
            ;
        }
        if ($action eq 'form') {
            return <<END
    <style>
        :root {
          --no-sk-size: 200px;
        }
    </style>
    <div class="tab-pane container" id="zimbra">
        $form
    </div>
END
            ;
        } else {
            return <<END
Content-type: text/htm

$form
END
        }

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
        \$("#currentwp").attr("href", "https://$dom/");
        \$("#currentwp").text("to zimbra");

    function limitZimbraSpinner(target) {
        if (!target) target = "zimbrapassword";
        \$("#" + target + "_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        var ser = \$('#' + target + '_form').serialize();
        \$(".kubebutton").prop("disabled", true );
        \$.post('index.cgi?action=' + target + '&tab=zimbra', ser, function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".kubebutton").prop("disabled", false );

            setTimeout(function() {
                \$.get("index.cgi?action=zimbraform&tab=zimbra", function(result) {
                    \$("#zimbra").html(result);
                });
            }, 200);

        }).fail(function() {
            salert( "An error occurred :(" );
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".kubebutton").prop("disabled", false );
        });
    }

    var linkElement = document.createElement("link");
    linkElement.rel = "stylesheet";
    linkElement.href = "tabs/zimbra/spinkit.css";
    document.head.appendChild(linkElement);

END
;
        return $js;

# This is called from index.cgi (the UI)
    } elsif ($action eq 'upgrade') {
        my $res;
        return $res;

# This is called from stabile-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {
        my $res;
        return $res;

    } elsif ($action eq 'zimbrapassword' && defined $in{zimbrapassword}) {
        my $message;
        my $pwd = $in{zimbrapassword};
        if ($pwd) {
            $message = `sudo -u zimbra /opt/zimbra/bin/zmprov sp admin $pwd`;
            chomp $message;
            if ($message) {
                $message =~ s/\n/ /g;
                $message = "There was a problem setting the password: $message";
            } else {
                $message = "The Zimbra password was changed!";
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;

    } elsif ($action eq 'zimbradomains' && (defined $in{zimbradomains} || defined $in{mycheck})) {
        my $message;
        my @domains = ();
        my %newdoms = ();
        my %aliasesdoms = map { lc $_ => $_ } split(/ /, $aliases);
        if (defined $in{mycheck} && $in{mycheck} eq '2') {
            # Run getssl
            if ($externalip) {
                my $res = `ping -c1 -w2 1.1.1.1`;
                if ($res =~ /100\% packet loss/) {
                    $message .= "No Internet connectivity - not running letsencrypt";
                } elsif ($externalip =~ /^192\.168\./){
                    $message .= "External IP is RFC 1819 - not running GetSSL";
                } elsif ($dnsdomain) {
                    `perl -pi -e 's/.*$esc_dnsdomain\n//s' /etc/hosts`;
                    `echo "$internalip $aliases $dom" >> /etc/hosts`; # necessary to allow getssl do its own checks
                    $message .= "Running getssl...";
                    my $sslres = `getssl -f  -U $dom | tee /tmp/getssl.out \&2>1`;
                    unless ($sslres =~ /error/i || $sslres =~ /failed/i) {
                        if (-e "/etc/ssl/certs/stabile.crt") {
                            $message .= "Let's encrypt centificates were installed for $dom $sans";
                        } else {
                            $message .= "Unable to obtain Let's encrypt centificates - certificates are not in place";
                        }
                    } else {
                        $message .= "Let's encrypt centificates were NOT obtained - getssl returned an error: $sslres";
                    }
                } else {
                    $message .= "Let's encrypt centificates were NOT installed because no DNS domain available";
                }
                $message =~ s/\n/ /g;
                $message =~ s/"/'/g;
            }
        } elsif (defined $in{zimbradomains}) {
            @domains = split(/ /, $in{zimbradomains});
            my $acl;
            foreach my $alias (@domains) {
                my $newdom = $alias;
                $newdom = "$alias.$dnsdomain" unless ($alias =~ /\./);
                # Assume existing domains are OK
                if ($aliasesdoms{$newdom}) {
                    ;
                } else {
                    # Check availability of domain name
                    if ($newdom =~ /\.$dnsdomain$/ && !dns_check($newdom)) {
                        $message .=  "<div class=\"message\">Domain $newdom is not available!</div>";
                        next;
                    } else {
                        # Create DNS entry if not a FQDN or in our zone
                        if ($newdom =~ /\.$dnsdomain/) {
                            my $mes = `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$newdom\&value=$externalip\&type=A"`;
                            $mes =~ s/Status=//g;
                            $message .= $mes;
                            $mes = `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$newdom\&value=$dom\&type=MX"`;
                            $mes =~ s/Status=//g;
                            $message .= $mes;
                        }
                    }
                    # Configure Zimbra alias domain
                    $message .= `sudo -u zimbra /opt/zimbra/bin/zmprov createAliasDomain $newdom stabile.int`;
                #    $message .= `sudo -u zimbra /opt/zimbra/bin/zmprov modifyConfig zimbraDefaultDomainName $dom`;
                    # $message .= `sudo -u zimbra /opt/zimbra/bin/zmprov addAccountAlias admin\@stabile.int admin\@$newdom`;
                    # chomp $message;
                    my $dkimres = `sudo -u zimbra /opt/zimbra/libexec/zmdkimkeyutil -a -d $newdom 2>\&1`;
                    # my $dkim = `sudo -u zimbra /opt/zimbra/libexec/zmdkimkeyutil -q -d $newdom 2>\&1`;
                    if ($dkimres =~ /(\w+-\w+-\w+-\w+-\w+\._domainkey)(\tIN\tTXT\t)(\(.+)(  ; ----- DKIM key .+)/s) {
                        my $dkey = $1;
                        my $dkim = $3;
                        $dkim =~ s/\n\s*\n/\n/g;
                        chomp $dkim;
                        my $dkim_entry = "$1$2$dkim$4";
                    #    $dkim =~ s/"\s+"//g;
                    #    $dkim_entry =~ s/"\s+"//g;
                        `echo '$dkim_entry' > /var/www/html/dns/$dkey.$newdom.dkim`;
                        my $spf = qq|( "v=spf1 mx ip4:$externalip -all" )|;
                        my $spf_entry = qq|$newdom.	60	IN	TXT	$spf|;
                        `echo '$spf_entry' > /var/www/html/dns/$newdom.spf`;
                        my $dmarc = qq|( "v=DMARC1; p=reject; pct=100; adkim=r; aspf=r; sp=none" )|;
                        my $dmarc_entry = qq|_dmarc.$newdom.	IN	TXT	$dmarc|;
                        `echo '$dmarc_entry' > /var/www/html/dns/_dmarc.$newdom.dmarc`;
                        if ($newdom =~ /\.$dnsdomain$/) {
                            $dkim = uri_escape($dkim);
                            #$dkim =~ s/([^^A-Za-z0-9\-_.!~*'()])/ sprintf "%%%0x", ord $1 /eg;
                            # URI encode https://stackoverflow.com/questions/4510550/using-perl-how-do-i-decode-or-create-those-encodings-on-the-web
                            $spf =~ s/([^^A-Za-z0-9\-_.!~*'()])/ sprintf "%%%0x", ord $1 /eg;
                            $dmarc =~ s/([^^A-Za-z0-9\-_.!~*'()])/ sprintf "%%%0x", ord $1 /eg;

                            my $cmd = qq|curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$dkey.$newdom\&value=$dkim\&type=TXT"|;
                            $mes = `$cmd`;
                            $mes =~ s/Status=//g; $mes = $1 if ($mes =~ /(.+) -> .*/); $message .= $mes;
                            $cmd = qq|curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$newdom\&value=$spf\&type=TXT"|;
                            $mes = `$cmd`;
                            $mes =~ s/Status=//g; $mes = $1 if ($mes =~ /(.+) -> .*/); $message .= $mes;
                            $cmd = qq|curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=_dmarc.$newdom\&value=$dmarc\&type=TXT"|;
                            $mes = `$cmd`;
                            $mes =~ s/Status=//g; $mes = $1 if ($mes =~ /(.+) -> .*/); $message .= $mes;
                        }
                    } else {
                        $message .= "Did not get valid DKIM keys from Zimbra. ";
                    }
                }
                $newdoms{$newdom} = 1;
                $acl .= qq|\n'/var/www/html/.well-known/acme-challenge'|;
            }
            # Run through old aliases and remove deleted domains from DNS
            foreach my $alias (keys %aliasesdoms) {
                unless ($newdoms{$alias}) {
                    if ($alias =~ /\.$dnsdomain$/) {
                        my $cmd = qq|curl -k --max-time 30 "https://$gw/stabile/networks?action=dnsdelete\&name=$alias"|;
                        my $mes = `$cmd`;
                        $mes =~ s/Status=//g;
                        $message .= $mes;
#                        $message .= `sudo -u zimbra /opt/zimbra/bin/zmprov removeAccountAlias admin\@stabile.int admin\@$alias`;
#                        chomp $message;
                    }
                    $message .= `sudo -u zimbra /opt/zimbra/libexec/zmdkimkeyutil -r -d $alias`;
                    $message .= `rm /var/www/html/dns/*.$alias.dkim`;
                    $message .= `rm /var/www/html/dns/$alias.spf`;
                    $message .= `rm /var/www/html/dns/*.$alias.dmarc`;
                    $message .= `sudo -u zimbra /opt/zimbra/bin/zmprov deleteDomain $alias`;
                }
            }
            $sans = join ",", keys %newdoms;
            $message .= "Aliases updated! ";
            `mkdir -p /root/.getssl/$dom` unless (-e "/root/.getssl");
            my $getsslcfg = <<END
CA="https://acme-v02.api.letsencrypt.org"
PRIVATE_KEY_ALG="rsa"
ACL=('/var/www/html/.well-known/acme-challenge'$acl)
SANS="$sans"
DOMAIN_CERT_LOCATION="/etc/ssl/certs/stabile.crt"
DOMAIN_KEY_LOCATION="/etc/ssl/certs/stabile.key"
CA_CERT_LOCATION="/etc/ssl/certs/stabile.chain"
RELOAD_CMD="/usr/local/bin/stabile-zimbra.pl updatecerts"
END
            ;
            `echo '$getsslcfg' > "/root/.getssl/$dom/getssl.cfg"`;
            if ($message) {
                $message =~ s/\n/ /g;
                $message =~ s/"/'/g;
            } else {
                $message = "Unable to change the Zimbra domains!";
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;
    }
}

1;
