#!/usr/bin/perl

use JSON;
use Digest::SHA qw(sha1_base64 sha1_hex);
use Digest::MD5 qw(md5 md5_hex md5_base64);

my $dnsdomain =  $appinfo{dnsdomain};
my $dnssubdomain = $appinfo{'dnssubdomain'};
my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":"$externalip";
my $esc_dnsdomain = $dnsdomain;
$esc_dnsdomain =~ s/\./\\./g;

sub aliases {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    my $meref = show_me();
    my $email = $meref->{email};
    $email = $meref->{username}  if (!$email || $email eq '--' || !($email =~ /\w+\@\w+/));
    my $aliases = `cat /root/.getssl/$dom/getssl.cfg | grep SANS=`;
    if ($aliases =~ /SANS="(.+)"/) {
        $aliases = $1;
        $aliases = join(' ', split(/, ?/, $aliases));
    } else {
        $aliases = '';
    }
    my $sans = '';

    if ($action eq 'form' || $action eq $action .'form') {
        my $form;

        #my $letsencrypt = (-e "/root/.getssl/$dom/getssl.cfg")?" checked":'';
        my $letsencrypt = (`grep 'snakeoil.pem' /etc/apache2/sites-available/*-ssl.conf`)?'':" checked";
        my $redirect = (`grep RewriteRule /etc/apache2/sites-available/000-default.conf`)?"checked":"";
        my $renewbtn = ($letsencrypt)?qq|<button onclick="\$('#letsencryptcheck').val('2'); salert('Hang on - this could take a minute or two...'); spinner(this); \$(this.form).submit();" class="btn btn-info btn-sm">renew</button>|:'';
        my $links = qq|<a href="https://$dom" target="_blank">$dom</a>|;
        foreach my $alias (split(/ /, $aliases)) {
            $links .= qq| / <a href="https://$alias" target="blank">$alias</a>|
        }

        $form .= <<END
        <form class="passwordform" id="aliasesredirectform" action="index.cgi?action=letsencrypt\&tab=aliases" method="post" accept-charset="utf-8" autocomplete="off">
            <div>
                Here you can manage aliases for this server and set up SSL certificates.
            </div>
            <div>
                <input id="aliasesredirect" type="checkbox" $redirect name="aliasesredirect" value="aliasesredirect" onchange="if (this.checked) {\$('#redirectcheck').val('2');} spinner(this); \$(this.form).submit();">
                <small>Redirect http &#8594; https for this site</small>
            </div>
            <input type="hidden" id="redirectcheck" name="redirectcheck" value="1">
        </form>
        <form class="passwordform" action="index.cgi?action=letsencrypt\&tab=aliases" method="post" accept-charset="utf-8" autocomplete="off">
            <div><small>Aliases for this website:</small></div>
            <div class="row">
                <div class="col-sm-10">
                    <input class="aliases" id="aliases" type="text" name="aliases" value="$aliases" autocomplete="off" />
                </div>
                <div class="col-sm-2">
                    <button type="submit" class="btn btn-default" onclick="spinner(this); submit();" rel="tooltip" data-placement="top" title="Aliases that are not FQDNs will be created in the $dnsdomain domain as [alias].$dnsdomain">Set!</button>
                </div>
            </div>
            <div><small>Aliases that contain a period are assumed to be FQDN's, and should point to $dom or $externalip. Aliases that do not contain a dot are created in the DNS zone $dnsdomain.</small></div>
            <div style="display:inline-block; margin-top:16px;">
                <input id="letsencrypt" type="checkbox" $letsencrypt name="letsencrypt" value="letsencrypt" onchange="if (this.checked) {\$('#letsencryptcheck').val('2'); salert('Hang on - this could take a minute or two...');} else {\$('#letsencryptcheck').val('3');} spinner(this); \$(this.form).submit();">
                <small>Get Let's Encrypt certificate and enable TLS this site $renewbtn</small>
                <div class="small">
                    Will try to obtain certificates for: $links
                </div>
            </div>
            <input type="hidden" id="letsencryptcheck" name="letsencryptcheck" value="1">
        </form>
END
        ;

        if ($action eq 'form') {
            return <<END
    <div class="tab-pane container" id="aliases">
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

END
;
        return $js;

    } elsif ($action eq 'letsencrypt') {
        my $message;
        my $confs = "/etc/apache2/sites-available/*-ssl.conf";
        my @domains = ();
        my %newdoms = ();
        my %aliasesdoms = map { lc $_ => $_ } split(/ /, $aliases);
        if (defined $in{aliases}) {
            @domains = split(/ /, $in{aliases});
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
                        my $mes = `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$newdom\&value=$externalip"` if ($newdom =~ /\.$dnsdomain/);
                        $mes =~ s/Status=//g;
                        $message .= $mes;
                    }
                }
                $newdoms{$newdom} = 1;
                $acl .= qq|\n'/var/www/html/.well-known/acme-challenge'|;
            }
            # Run through old aliases and remove deleted domains from DNS
            foreach my $alias (keys %aliasesdoms) {
                unless ($newdoms{$alias}) {
                    if ($alias =~ /\.$dnsdomain$/) {
                        my $cmd = qq|curl -k --max-time 5 "https://$gw/stabile/networks?action=dnsdelete\&name=$alias"|;
                        my $mes = `$cmd`;
                        $mes =~ s/Status=//g;
                        $message .= $mes;
                        sleep 1;
                    }
                }
            }
            $sans = join ",", keys %newdoms;
            $message .= "Updating aliases. ";
            # `mv /root/.getssl.bak /root/.getssl` if (-e "/root/.getssl.bak");
            `mkdir -p /root/.getssl/$dom` unless (-e "/root/.getssl");
            my $getsslcfg = <<END
CA="https://acme-v02.api.letsencrypt.org"
PRIVATE_KEY_ALG="rsa"
ACL=('/var/www/html/.well-known/acme-challenge'$acl)
SANS="$sans"
DOMAIN_CERT_LOCATION="/etc/ssl/certs/stabile.crt"
DOMAIN_KEY_LOCATION="/etc/ssl/certs/stabile.key"
CA_CERT_LOCATION="/etc/ssl/certs/stabile.chain"
RELOAD_CMD="systemctl reload apache2"
END
            ;
            `echo '$getsslcfg' > "/root/.getssl/$dom/getssl.cfg"`;
        }
        if (defined $in{letsencryptcheck}) {
            if ($in{letsencryptcheck} eq '2') {
                # Run getssl
                if ($externalip) {
                    my $res = `ping -c1 -w2 1.1.1.1`;
                    if ($res =~ /100\% packet loss/) {
                        $message .= "No Internet connectivity - not running letsencrypt";
                    } elsif ($externalip =~ /^192\.168\./){
                        $message .= "External IP is RFC 1819 - not running GetSSL";
                    } elsif ($dnsdomain) {
                        `perl -pi -e 's/.*$esc_dnsdomain\n//s' /etc/hosts`;
                        my $hsans = $sans;
                        $hsans =~ s/,/ /g;
                        `echo "$internalip $hsans $dom" >> /etc/hosts`; # necessary to allow getssl do its own checks
                        $message .= "Running getssl...";
                        my $sslres = `getssl -f  -U $dom | tee /tmp/getssl.out \&2>1`;
                        unless ($sslres =~ /error/i || $sslres =~ /failed/i) {
                            if (-e "/etc/ssl/certs/stabile.crt") {
                                $message .= "<div class=\"message\">";
                                $message .= `perl -pi -e 's/SSLCertificateFile.+/SSLCertificateFile \\/etc\\/ssl\\/certs\\/stabile.crt/g' $confs`;
                                $message .= `perl -pi -e 's/SSLCertificateKeyFile.+/SSLCertificateKeyFile \\/etc\\/ssl\\/certs\\/stabile.key/g' $confs`;
                                $message .= `perl -pi -e 's/#SSLCertificateChainFile.+/SSLCertificateChainFile \\/etc\\/ssl\\/certs\\/stabile.chain/g' $confs`;
                                $message .= "</div>";
                                `systemctl reload apache2`;
                                $message .= "<div class=\"message\">Let's encrypt centificates were installed for $dom $sans</div>";
                            } else {
                                $message .= "<div class=\"message\">Unable to obtain Let's encrypt centificates - certificates are not in place</div>";
                            }
                        } else {
                            $message .= "<div class=\"message\">Let's encrypt centificates were NOT obtained - getssl returned an error: $sslres</div>";
                        }
                    } else {
                        $message .= "<div class=\"message\">Let's encrypt centificates were NOT installed because no DNS domain available</div>";
                    }
                }
            } elsif ($in{letsencryptcheck} eq '3') {
            #    `mv /root/.getssl /root/.getssl.bak` if (-e "/root/.getssl");
                `perl -pi -e 's/.*$esc_dnsdomain\n//s' /etc/hosts`;
                $message .= "<div class=\"message\">";
                $message .= `perl -pi -e 's/SSLCertificateFile.+/SSLCertificateFile \\/etc\\/ssl\\/certs\\/ssl-cert-snakeoil.pem/g' $confs 2>\&1`;
                $message .= `perl -pi -e 's/SSLCertificateKeyFile.+/SSLCertificateKeyFile \\/etc\\/ssl\\/private\\/ssl-cert-snakeoil.key/g' $confs 2>\&1`;
                $message .= `perl -pi -e 's/SSLCertificateChainFile.+/#SSLCertificateChainFile \\/etc\\/ssl\\/certs\\/ssl-cert-snakeoil.chain/g' $confs 2>\&1`;
                $message .= "</div>";
                `systemctl reload apache2`;
                $message .= "<div class=\"message\">Let's encrypt centificates were removed!!!</div>";
            }
        }
        if (defined $in{redirectcheck}) {
            my $redirecting = `grep RewriteRule /etc/apache2/sites-available/000-default.conf`;
            my $redirect = defined $in{redirect} || $in{redirectcheck} eq '2';
            if ($redirect && !$redirecting) {
                `a2enmod rewrite`;
                my $msg = `perl -pi -e 's/<\\/VirtualHost>/RewriteEngine On\nRewriteRule (.*) https:\\/\\/\%{HTTP_HOST}\%{REQUEST_URI}\n<\\/VirtualHost>/s' /etc/apache2/sites-available/000-default.conf \&2>1`;
                `systemctl reload apache2`;
                $message .=  "<div class=\"message\">TLS redirection was enabled $msg</div>";
            } elsif ($redirecting) {
                my $msg = `perl -pi -e 's/RewriteEngine On\n//s' /etc/apache2/sites-available/000-default.conf \&2>1`;
                $msg .= `perl -pi -e 's/RewriteRule .*\n//s' /etc/apache2/sites-available/000-default.conf \&2>1`;
                `systemctl reload apache2`;
                $message .=  "<div class=\"message\">TLS redirection was removed! $msg</div>";
            }
        }
        return $message;
    }
}


1;
