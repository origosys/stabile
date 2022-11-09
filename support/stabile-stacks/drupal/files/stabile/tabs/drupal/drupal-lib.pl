#!/usr/bin/perl

use JSON;

my $dnsdomain_json = `curl -k https://$gw/stabile/networks?action=getdnsdomain`;
my $dom_obj = from_json ($dnsdomain_json);
my $dnsdomain =  $dom_obj->{'domain'};
my $dnssubdomain = $dom_obj->{'subdomain'};
$dnsdomain = '' unless ($dnsdomain =~  /\S+\.\S+$/ || $dnsdomain =~  /\S+\.\S+\.\S+$/);
my $esc_dnsdomain = $dnsdomain;
$esc_dnsdomain =~ s/\./\\./g;

sub drupal {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
        # Generate and return the HTML form for this tab
        my $form;
        opendir(DIR,"/var/www/drupal/sites") or die "Cannot open /var/www/drupal/sites\n";
        my @drupalfiles = readdir(DIR);
        closedir(DIR);
        my %aliases;
        foreach my $dir (@drupalfiles) {
            if (-l "/var/www/drupal/sites/$dir") {
                my $link = readlink("/var/www/drupal/sites/$dir");
                $aliases{$link} .= "$dir " if (-d "/var/www/drupal/sites/$link" && -e "/var/www/drupal/sites/$link/settings.php");
            }
        }
        foreach my $dir (@drupalfiles) {
            next if (-l "/var/www/drupal/sites/$dir");
            next unless (-d "/var/www/drupal/sites/$dir" && -e "/var/www/drupal/sites/$dir/settings.php");
            my $drupalname = $dir;
            $drupalname = $1 if ($drupalname =~ /(.+)\.$dnsdomain/);
            $drupalname =~ tr/\./_/;
            $form .= getDrupalTab($dir, $drupalname, $aliases{$dir});
        }
        $form .=  getDrupalTab('new', 'new');
        $form .=  getDrupalTab('drupalsecurity', 'drupalsecurity');

        # Redirect to upgrade page if still upgrading
        if (-e "/tmp/restoring") {
            $form .=  qq|<script>loc=document.location.href; setTimeout(function(){document.location=loc;}, 1500); </script>|;
        }

        return $form;

    } elsif ($action eq 'js') {
        # Generate and return javascript the UI for this tab needs
        my $dom = ($dnsdomain)?"$externalip.$dnssubdomain.$dnsdomain":$externalip;
        my $js = <<END
        \$('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
            var site = e.target.id;
            var href = e.target.href;
            var regexp = /#(.+)-site/;
            var match = regexp.exec(href);
            if (href.indexOf('#new')!=-1) { // set standard grey border in case it has failed validation previously
                \$('#drupaldomain_new').css('border','1px solid #CCCCCC'); \$('#drupaldomain_new').focus();
            }
            if (!match || match[1] == 'default' || match[1] == 'new') {
                \$("#currentwp").attr("href", "http://$dom/");
                \$("#currentwp").text("to default Drupal website");
                \$("#currentwpadmin").attr("href", "https://$dom/home/drupal-admin/");
                \$("#currentwpadmin").text("to default Drupal console");
            } else {
                var siteaddr = site;
                if (site.indexOf(".")==-1) siteaddr = site + ".$dnsdomain"
                \$("#currentwp").attr("href", "http://" + siteaddr + "/");
                \$("#currentwp").text("to " + site);
                \$("#currentwpadmin").attr("href", "https://" + siteaddr + "/home/drupal-admin/");
                \$("#currentwpadmin").text("to " + site + " administration");
            }
            if (match) {
                setTimeout(
                    function() {
                        if (\$("#drupalaliases_h_" + match[1]).val() == '')
                            \$("#drupalaliases_" + match[1]).val("");
                        \$("#drupalpassword_" + match[1]).val("--");
                        \$("#drupalpassword_" + match[1]).val("");
                    }, 100
                )
            }
        })

        \$(".drupaldomain").keypress(function(event){
            var inputValue = event.which;
            //if digits or not a space then don't let keypress work.
            if(
                (inputValue > 47 && inputValue < 58) //numbers
                || (inputValue > 64 && inputValue < 90) //letters
                || (inputValue > 96 && inputValue < 122)
                || inputValue==46 //period
                || inputValue==45 //dash
                || inputValue==95 //underscore
                || inputValue==8 //backspace
                || inputValue==127 //del
                || inputValue==9 //tab
                || inputValue==0 //tab?
            ) {
                ; // allow keypress
            } else
            {
                event.preventDefault();
            }
        });

        \$(".drupalalias").keypress(function(event){
            var inputValue = event.which;
            //if digits or not a space then don't let keypress work.
            if(
                (inputValue > 47 && inputValue < 58) //numbers
                || (inputValue > 64 && inputValue < 90) //letters
                || (inputValue > 96 && inputValue < 122)
                || inputValue==46 //period
                || inputValue==45 //dash
                || inputValue==95 //underscore
                || inputValue==8 //backspace
                || inputValue==127 //del
                || inputValue==32 //space
                || inputValue==9 //tab
                || inputValue==0 //tab?
            ) {
                ; // allow keypress
            } else
            {
                event.preventDefault();
            }
        });

        function confirmDRUPALAction(action, drupalname) {
            if (action == 'drupalremove') {
                \$('#action_' + drupalname).val(action);
                \$('#confirmdialog').prop('actionform', '#drupalform_' + drupalname);
                \$('#confirmdialog').modal({'backdrop': false, 'show': true});
                \$('#confirmed').click(function(){spinner(".drupalremove");});
                return false;
            }
        };

END
        ;
        return $js;


    } elsif ($action eq 'tab') {
        return getDRUPALdropdown();

        # This is called from index.cgi (the UI)
    } elsif ($action eq 'upgrade') {
        my $res;
        my $srcloc = "/var/www/drupal";
        my $dumploc = $in{targetdir};

        if (-d $dumploc) {
            # Dump database
            `mysqldump --databases \$(mysql -N information_schema -e "SELECT DISTINCT(TABLE_SCHEMA) FROM tables WHERE TABLE_SCHEMA LIKE 'drupal_%'") > $dumploc/drupal.sql`;
        }

        my $srcsize = `du -bs $srcloc`;
        $srcsize = $1 if ($srcsize =~ /(\d+)/);
        my $dumpsize = `du -bs $dumploc/drupal`;
        $dumpsize = $1 if ($dumpsize =~ /(\d+)/);
        if ($srcsize == $dumpsize) {
            $res = "OK: Drupal data and database dumped successfully to $dumploc";
        } else {
            $res = "There was a problem dumping Drupal data to $dumploc ($srcsize <> $dumpsize)!";
        }
        return $res;

        # This is called from stabile-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {
        my $srcloc = $in{sourcedir};
        my $res;
        my $dumploc  = "/var/www";
        if (-d $srcloc && -d $dumploc) {
            $res = "OK: ";
            if (-e "$srcloc/drupal.sql") {
                $res .= qq|restoring db, |;
                $res .= `/usr/bin/mysql < $srcloc/drupal.sql`;
            }
            chomp $res;
        }
        $res = "Not copying $srcloc/* -> $dumploc" unless ($res);
        return $res;

    } elsif ($action eq 'drupalremove' && $in{drupal}) {
        my $message;
        my $drupal = $in{drupal};
        my $dom = $drupal;
        my $drupalname = $drupal;
        $drupalname = $1 if ($drupalname =~ /(.+)\.$dnsdomain$/);
        $drupalname =~ tr/\./_/;
        $drupal = $1 if ($drupal =~ /(.+)\.$dnsdomain$/);
        $dom = "$dom.$dnsdomain" unless ($dom =~ /\./ || $dom eq 'default');
        my $db = "drupal_$drupalname";
        $message .= `mysqldump $db > /var/lib/drupal/$db.sql`;
        `echo "drop database $db;" | mysql`;

        opendir(DIR,"/var/www/drupal/sites") or die "Cannot open /var/www/drupal/sites\n";
        my @drupalfiles = readdir(DIR);
        closedir(DIR);
        # First remove aliases
        foreach my $file (@drupalfiles) {
            my $fname = $file;
            $fname = $1 if ($fname =~ /(.+)\.$dnsdomain$/);
            if (-l "/var/www/drupal/sites/$file") { # Check if it is a link
                my $link = readlink("/var/www/drupal/sites/$file");
                if ($link eq $dom) {
                    unlink ("/var/www/drupal/sites/$file");
                    # Remove DNS entry if not a FQDN
                    $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnsdelete\&name=$fname"` unless ($fname =~ /\./);
                }
            }
        }
        if ($dom eq 'default') { # default should always exist - recreate
            $message .= `cd /var/www/drupal; drush -y site-install standard --db-url='mysql://drupal\@localhost/drupal_default' --site-name=Drupal >> /root/drupal_install.out 2>&1`;
            $message .=  "<div class=\"message\">Default website was reset!</div>";
        } else {
            # Remove DNS entry if not a FQDN
            $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnsdelete\&name=$drupal"` unless ($drupal =~ /\./);
            $message .= `rm -r /var/www/drupal/sites/$dom`;
            $message .=  "<div class=\"message\">Website $dom was removed!</div>";
            opendir(DIR,"/var/www/drupal/sites") or die "Cannot open /var/www/drupal/sites\n";
            @drupalfiles = readdir(DIR);
            closedir(DIR);
        }
        $postscript .= qq|\$('#nav-tabs a[href="#default-site"]').tab('show');\n|;
        return $message;
    } elsif ($action eq 'drupalcreate' && $in{drupaldomain_new}) {
        my $message;
        my $drupal = $in{drupaldomain_new};
        my $drupalname = $drupal;
        $drupal = $1 if ($drupal =~ /(.+)\.$dnsdomain$/);
        $drupalname = $1 if ($drupalname =~ /(.+)\.$dnsdomain$/);
        $drupalname =~ tr/\./_/;
        my $dom = $drupal;
        $dom = "$dom.$dnsdomain" unless ($dom =~ /\./ || $dom eq 'default');
        my $db = "drupal_$drupalname";
        if (-e "/var/www/drupal/sites/$dom" || $drupal eq 'new' || $drupal eq 'default') {
            $message .=  "<div class=\"message\">Website $dom already exists!</div>";
        } elsif ($dom =~ /\.$dnsdomain$/  && !dns_check($drupal)) {
            $message .=  "<div class=\"message\">Domain $drupal.$dnsdomain is not available - please use a domain that's available, and make sure your engine is linked!</div>";
        } else {
            # Configure Drupal / Debian
            $message .= `mkdir -p /var/www/drupal/sites/$dom/files`;
            $message .= `cp -a /var/lib/drupal/files/css /var/www/drupal/sites/$dom/files`;
            $message .= `cp -a /var/lib/drupal/files/js /var/www/drupal/sites/$dom/files`;
            $message .= `cp -a /var/lib/drupal/files/php /var/www/drupal/sites/$dom/files`;
            $message .= `cd /var/www/drupal; drush -y site-install standard --db-url='mysql://drupal\@localhost/$db' --site-name=$dom --sites-subdir=$dom >> /root/drupal_install.out 2>&1`;
            $message .= `chown -R www-data:www-data /var/www/drupal/sites/$dom`;

            # Create DNS entry if not a FQDN
            $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$drupal\&value=$externalip"` unless ($drupal =~ /\./);

            # Create aliases
            if (defined $in{"drupalaliases_new"}) {
                my @drupalaliases = split(' ', $in{"drupalaliases_new"});
                foreach my $alias (@drupalaliases) {
                    my $dom1 = $alias;
                    $dom1 = "$alias.$dnsdomain" unless ($alias =~ /\./);
                    $alias = $1 if ($alias =~ /(.+)\.$dnsdomain/);
                    my $link = "/var/www/drupal/sites/$dom1";
                    unless (-e $link) {
                        $message .= `cd /var/www/drupal/sites; ln -s "$dom" "$link"`;
                        # Create DNS entry if not a FQDN
                        $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$alias\&value=$externalip"` unless ($alias =~ /\./);
                        $message .=  "<div class=\"message\">alias $link -> $dom was created!</div>";
                    }
                }
            }

            $message .=  "<div class=\"message\">Website $dom was created!</div>";
            $postscript .= qq|\$('#nav-tabs a[href="#$drupalname-site"]').tab('show');\n|;
        }
        return $message;
    } elsif ($action eq 'drupalaliases' && $in{drupal}) {
        my $message;
        my $drupal = $in{drupal};
        my $drupalname = $drupal;
        $drupal = $1 if ($drupal =~ /(.+)\.$dnsdomain$/);
        $drupalname = $1 if ($drupalname =~ /(.+)\.$dnsdomain$/);
        $drupalname =~ tr/\./_/;
        my $dom = $drupal;
        $dom = "$dom.$dnsdomain" unless ($dom =~ /\./ || $dom eq 'default');
        opendir(DIR,"/var/www/drupal/sites") or die "Cannot open /var/www/drupal/sites\n";
        my @drupalfiles = readdir(DIR);
        closedir(DIR);
        my %aliases;
        if (defined $in{"drupalaliases_$drupalname"}) {
            if (-d "/var/www/drupal/sites/$dom" && -e "/var/www/drupal/sites/$dom/settings.php") {
                my @drupalaliases = split(' ', $in{"drupalaliases_$drupalname"});
                foreach my $alias (@drupalaliases) {$aliases{$alias} = 1;}
                # First locate and unlink existing aliases that should be deleted
                foreach my $dir (@drupalfiles) {
                    next unless (-l "/var/www/drupal/sites/$dir");
                    my $fname = $dir;
                    $fname = $1 if ($dir =~ /(.+)\.$dnsdomain/);
                    my $link = readlink("/var/www/drupal/sites/$dir");
                    if ($link eq $dom) {
                        unless ($aliases{$fname} || $aliases{$dir}) { # This alias should be deleted
                            unlink ("/var/www/drupal/sites/$dir");
                            # Remove DNS entry if not a FQDN
                            $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnsdelete\&name=$fname"` unless ($fname =~ /\./);
                            $message .=  "<div class=\"message\">Alias $dir removed!</div>";
                        }
                        $aliases{$fname} = 0; # No need to recreate this alias
                    }
                }
                # Then create aliases
                foreach my $alias (@drupalaliases) {
                    my $newdom = $alias;
                    $newdom = "$alias.$dnsdomain" unless ($alias =~ /\./);
                    $alias = $1 if ($alias =~ /(.+)\.$dnsdomain$/);
                    my $link = "/var/www/drupal/sites/$newdom";
                    # Check availability of new domain names
                    if ($newdom =~ /\.$dnsdomain$/ && !(-e $link) && !dns_check($newdom)) {
                        $message .=  "<div class=\"message\">Domain $alias.$dnsdomain is not available!</div>";
                    } elsif (($aliases{$alias} || $aliases{$newdom}) && !(-e $link)) {
                        $message .= `cd /var/www/drupal/sites; ln -s "$dom" "$link"`;
                        # Create DNS entry if not a FQDN
                        $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$alias\&value=$externalip"` unless ($alias =~ /\./);
                        #                    $message .=  "<div class=\"message\">Alias $alias created!</div>";
                        # Re-read directory
                    } else {
                        #                    $message .=  "<div class=\"message\">Alias $alias not created!</div>";
                    }
                }
                opendir(DIR,"/var/www/drupal/sites") or die "Cannot open /var/www/drupal/sites\n";
                @drupalfiles = readdir(DIR);
                closedir(DIR);
                $message .=  "<div class=\"message\">Aliases updated for $drupal!</div>";
            } else {
                $message .=  "<div class=\"message\">Target $dom does not exist!</div>";
            }
        }
        #    $postscript .= qq|\$('#nav-tabs a[href="#$drupalname-site"]').tab('show');\n|;
        return $message;
    } elsif ($action eq 'drupalrestore' && $in{drupal}) {
        my $message;
        my $drupal = $in{drupal};
        my $drupalname = $drupal;
        $drupalname = $1 if ($drupalname =~ /(.+)\.$dnsdomain/);
        $drupalname =~ tr/\./_/;
        my $db = "drupal_$drupalname";
        if (-e "/var/lib/drupal/$db.sql") {
            #        `echo "drop database drupal; create database drupal;" | mysql`;
            $message .=  `mysql $db < /var/lib/drupal/$db.sql`;
            if (`echo status | mysql $db`) {
                $message .=  "<div class=\"message\">Drupal database restored.</div>";
            } else {
                $message .=  "<div class=\"message\">Drupal database $db not found!</div>";
            }
        }
        #    $postscript .= qq|\$('#nav-tabs a[href="#$drupalname-site"]').tab('show');\n|;
        return $message;
    } elsif ($action eq 'drupalbackup' && $in{drupal}) {
        my $message;
        my $drupal = $in{drupal};
        my $drupalname = $drupal;
        $drupalname = $1 if ($drupalname =~ /(.+)\.$dnsdomain/);
        $drupalname =~ tr/\./_/;
        my $db = "drupal_$drupalname";
        $message .=  `mysqldump $db > /var/lib/drupal/$db.sql`;
        $message .=  "<div class=\"message\">Drupal database was backed up to /var/lib/drupal/$db.sql!</div>" if (-e "/var/lib/drupal/$db.sql");
        #    $postscript .= qq|\$('#nav-tabs a[href="#$drupalname-site"]').tab('show');\n|;
        return $message;
    } elsif ($action eq 'drupalpassword' && $in{drupal}) {
        my $message;
        my $drupal = $in{drupal};
        my $drupalname = $drupal;
        $drupalname = $1 if ($drupalname =~ /(.+)\.$dnsdomain/);
        $drupalname =~ tr/\./_/;
        my $pwd = $in{drupalpassword};
        if ($pwd) {
            $message .= `bash -c 'cd /var/www/drupal; drush -l $drupal upwd --password="$pwd" admin' 2>&1`;
        }
        return $message;
    } elsif ($action eq 'drupallimit') {
        my $message;
        if (defined $in{drupallimit}) {
            my $limit = $in{drupallimit};
            my ($validlimit, $mess) = validate_limit($limit);
            $message .= $mess;
            if ($validlimit) {
                if (`grep '#stabile' /var/www/drupal/.htaccess`)
                {
                    $message .= `perl -pi -e 's/allow from (.*) \#stabile/allow from $validlimit #stabile/;' /var/www/drupal/.htaccess`;
                } else {
                    $validlimit =~ s/\\//g;
                    `echo "<files drupal-login.php>\norder deny,allow\ndeny from all\nallow from $validlimit #stabile\n</files>" >> /var/www/drupal/.htaccess`;
                }
                $message .=  "<div class=\"message\">Drupal admin access was changed!</div>";
            } else {
                $message .= `perl -i -p0e 's/<files drupal-login\.php>\n.*\n.*\n.*\n<\/files>//smg' /var/www/drupal/.htaccess`;
                $message .=  "<div class=\"message\">Drupal admin access is now open from anywhere!</div>";
                $drupallimit = '';
            }
            my $allow = `cat /var/www/drupal/.htaccess`;
            $drupallimit = $1 if ($allow =~ /allow from (.+) \#stabile/);
        }
        return $message;

    } elsif ($action eq 'drupalletsencrypt') {
        my $message;
        my $confs = "/etc/apache2/sites-available/*-ssl.conf";
        if (defined $in{drupalletsencryptcheck}) {
            my $encrypt = $in{drupalletsencryptcheck} eq '2';
            if ($encrypt) {
                # Run getssl
                if ($externalip) {
                    my $res = `ping -c1 -w2 1.1.1.1`;
                    if ($res =~ /100\% packet loss/) {
                        $message .= "No Internet connectivity - not running letsencrypt";
                    } elsif ($externalip =~ /^192\.168\./){
                        $message .= "External IP is RFC 1819 - not running GetSSL";
                    } elsif ($dnsdomain) {
                        opendir(DIR,"/var/www/drupal/sites") or die "Cannot open /var/www/drupal/sites\n";
                        my @drupalfiles = readdir(DIR);
                        closedir(DIR);
                        my @domains;
                        my $acl;
                        foreach my $file (@drupalfiles) {
                            if (-l "/var/www/drupal/sites/$file") { # Check if it is a link
                                my $link = readlink("/var/www/drupal/sites/$file");
                                next unless (-e "/var/www/drupal/sites/$link/settings.php");
                            } else {
                                next unless ($file ne 'default' && -e "/var/www/drupal/sites/$file/settings.php");
                            }
                            push @domains, $file;
                            $acl .= qq|\n'/var/www/html/.well-known/acme-challenge'|;
                        }
                        my $sans = join ",", @domains;
                        $message .= "Running getssl...";
                        `mv /root/.getssl.bak /root/.getssl` if (-e "/root/.getssl.bak");
                        `mkdir -p /root/.getssl/$externalip.$dnssubdomain.$dnsdomain` unless (-e "/root/.getssl");
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
                        `echo '$getsslcfg' > "/root/.getssl/$externalip.$dnssubdomain.$dnsdomain/getssl.cfg"`;
                        `perl -pi -e 's/.*$esc_dnsdomain\n//s' /etc/hosts`;
                        my $hsans = $sans;
                        $hsans =~ s/,/ /g;
                        `echo "$internalip $externalip.$dnssubdomain.$dnsdomain $hsans" >> /etc/hosts`; # necessary to allow getssl do its own checks
                        my $sslres = `getssl -f  -U $externalip.$dnssubdomain.$dnsdomain | tee /tmp/getssl.out \&2>1`;
                        unless ($sslres =~ /error/i) {
                            if (-e "/etc/ssl/certs/stabile.crt") {
                                $message .= "<div class=\"message\">";
                                $message .= `perl -pi -e 's/SSLCertificateFile.+/SSLCertificateFile \\/etc\\/ssl\\/certs\\/stabile.crt/g' $confs`;
                                $message .= `perl -pi -e 's/SSLCertificateKeyFile.+/SSLCertificateKeyFile \\/etc\\/ssl\\/certs\\/stabile.key/g' $confs`;
                                $message .= `perl -pi -e 's/#SSLCertificateChainFile.+/SSLCertificateChainFile \\/etc\\/ssl\\/certs\\/stabile.chain/g' $confs`;
                                $message .= "</div>";
                                `systemctl reload apache2`;
                                $message .= "<div class=\"message\">Let's encrypt centificates were installed for $externalip.$dnssubdomain.$dnsdomain $sans $sslres</div>";
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
            } else {
                `mv /root/.getssl /root/.getssl.bak` if (-e "/root/.getssl");
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
        if (defined $in{drupalredirectcheck}) {
            my $redirecting = `grep RewriteRule /etc/apache2/sites-available/000-default.conf`;
            my $redirect = defined $in{drupalredirect} || $in{drupalredirectcheck} eq '2';
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

## Returns HTML for drop-down for selecting Drupal sites
sub getDRUPALdropdown {
    my $dropdown;
    my $websitedrops;
    opendir(DIR,"/var/www/drupal/sites") or die "Cannot open /var/www/drupal/sites\n";
    my @drupalfiles = readdir(DIR);
    closedir(DIR);

    foreach my $dir (@drupalfiles) {
        next if (-l "/var/www/drupal/sites/$dir"); # This is an alias - skip
        next if ($dir eq 'default');
        next unless (-d "/var/www/drupal/sites/$dir" && -e "/var/www/drupal/sites/$dir/settings.php");
        my $drupalname = $dir;
        $drupalname = $1 if ($drupalname =~ /(.+)\.$dnsdomain/);
        $drupalname =~ tr/\./_/;
        $websitedrops .= <<END
<li><a href="#$drupalname-site" tabindex="-1" data-toggle="tab" id="$dir">$dir</a></li>
END
        ;
    }

    $dropdown = <<END
        <li class="dropdown">
            <a href="#" id="myTabDrop1" class="dropdown-toggle" data-toggle="dropdown">drupal <b class="caret"></b></a>
            <span class="dropdown-arrow"></span>
            <ul class="dropdown-menu" role="menu" aria-labelledby="myTabDrop1">
                <li><a href="#default-site" tabindex="-1" data-toggle="tab">Default website</a></li>
                $websitedrops
                <li><a href="#new-site" tabindex="-1" data-toggle="tab">Add new website...</a></li>
                <li><a href="#drupal-security" tabindex="-1" data-toggle="tab">Drupal security</a></li>
            </ul>
        </li>
END
    ;
    return $dropdown;

}

## Returns HTML for a single Drupal configuration tab
sub getDrupalTab {
    my $drupal = shift;
    my $drupalname = shift;
    my $drupalaliases = shift;
    $drupalaliases = join(' ', split(' ', $drupalaliases));
    my $drupalalinks = '';
    foreach my $link (split(' ', $drupalaliases)) {
        $drupalalinks .= qq|<a href="http://$link" target="_blank">$link</a> |;
    }
    $drupalalinks = " ($drupalalinks)" if ($drupalalinks);
    my $dom = $drupal;
    $dom = "$dom.$dnsdomain" unless ($dom =~ /\./ || $dom eq 'default');
    $dom = "$externalip.$dnssubdomain.$dnsdomain" if ($dom eq 'default');
    my $drupaluser = 'admin';
    if ($drupal eq 'drupalsecurity') {
        my $allow = `cat /var/www/drupal/.htaccess`;
        my $drupallimit;
        $drupallimit = $1 if ($allow =~ /allow from (.+) \#stabile/);
        my $drupalletsencrypt = (-e "/root/.getssl/$externalip.$dnssubdomain.$dnsdomain/getssl.cfg")?" checked":'';
        my $drupalredirect = (`grep RewriteRule /etc/apache2/sites-available/000-default.conf`)?"checked":"";
        my $renewbtn = ($drupalletsencrypt)?qq|<button onclick="\$('#drupalletsencryptcheck').val('2'); salert('Hang on - this could take a minute or two...'); spinner(this); \$(this.form).submit();" class="btn btn-info btn-sm" type="button">renew</button>|:'';

        my $curipdrupal;
        $curipdrupal = qq|<span style="float: left; font-size: 13px;">leave empty to allow login from anywhere, your current IP is <a href="#" onclick="\$('#drupallimit').val('$ENV{HTTP_X_FORWARDED_FOR} ' + \$('#drupallimit').val());">$ENV{HTTP_X_FORWARDED_FOR}</a></span>| if ($ENV{HTTP_X_FORWARDED_FOR});

        my $drupalsecurityform = <<END
<div class="tab-pane" id="drupal-security">
    <form class="passwordform" noaction="index.cgi?action=drupallimit\&tab=drupal\&show=drupal-security" method="post" accept-charset="utf-8" style="margin-bottom:36px;" autocomplete="off">
        <div>
            <small>Limit drupal login for all sites to:</small>
            <div class="row">
                <div class="col-sm-10">
                    <input id="drupallimit" type="text" name="drupallimit" value="$drupallimit" placeholder="IP address or network, e.g. '192.168.0.0/24 127.0.0.1'">
                    $curipdrupal
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default" type="button" onclick="spinner(this);">Set!</button>
                </div>
            </div>
        </div>
    </form>
    <form class="passwordform" action="index.cgi?action=drupalletsencrypt\&tab=drupal\&show=drupal-security" method="post" accept-charset="utf-8" autocomplete="off">
        <div style="display:inline-block;">
            <input id="drupalletsencrypt" type="checkbox" $drupalletsencrypt name="drupalletsencrypt" value="drupalletsencrypt" onchange="if (this.checked) {\$('#drupalletsencryptcheck').val('2'); salert('Hang on - this could take a minute or two...');} spinner(this); \$(this.form).submit();">
            <small>Get Let's Encrypt certificate and enable TLS for all sites $renewbtn</small>
        </div>
        <input type="hidden" id="drupalletsencryptcheck" name="drupalletsencryptcheck" value="1">
    </form>
    <form class="passwordform" id="drupalredirectform" action="index.cgi?action=drupalletsencrypt\&tab=drupal\&show=drupal-security" method="post" accept-charset="utf-8" autocomplete="off">
        <div>
            <input id="drupalredirect" type="checkbox" $drupalredirect name="drupalredirect" value="drupalredirect" onchange="if (this.checked) {\$('#drupalredirectcheck').val('2');} spinner(this); \$(this.form).submit();">
            <small>Redirect -> https for all sites</small>
        </div>
        <input type="hidden" id="drupalredirectcheck" name="drupalredirectcheck" value="1">
    </form>
</div>
END
        ;
        return $drupalsecurityform;
    }

    my $resetbutton = qq|<button class="btn btn-danger drupalremove" rel="tooltip" type="button" data-placement="top" title="This will remove your website and wipe your database - be absolutely sure this is what you want to do!" id="drupalremove_button_$drupalname" onclick="confirmDRUPALAction('drupalremove', '$drupalname');" type="button">Remove website</button>|;

    my $backup_tooltip = "Click to back up your Drupal database";

    my $manageform = <<END
    <div class="tab-pane" id="$drupalname-site">
    <form class="passwordform drupalform" id="drupalform_$drupalname" action="index.cgi?tab=drupal\&show=$drupalname-site" method="post" accept-charset="utf-8" autocomplete="off">
        <div>
            <small>The website's <a href="http://$dom" target="_blank">domain name</a>:</small>
            <input class="drupaldomain" id="drupaldomain_$drupalname" type="text" name="drupaldomain_$drupalname" value="$drupal" disabled autocomplete="off">
        </div>
        <small>Aliases for the website$drupalalinks:</small>
        <div class="row">
            <div class="col-sm-10">
                <input class="drupalalias" id="drupalaliases_$drupalname" type="text" name="drupalaliases_$drupalname" value="$drupalaliases" autocomplete="off" />
                <input type="hidden" id="drupalaliases_h_$drupalname" name="drupalaliases_h_$drupalname" value="$drupalaliases" autocomplete="off" />
            </div>
            <div class="col-sm-2">
                <button type="button" class="btn btn-default" onclick="spinner(this); \$('#action_$drupalname').val('drupalaliases'); submit();" rel="tooltip" data-placement="top" title="Aliases that are not FQDNs will be created in the $dnsdomain domain as [alias].$dnsdomain">Set!</button>
            </div>
        </div>
        <small>Set password for Drupal user '$drupaluser':</small>
        <div class="row">
            <div class="col-sm-10">
                <input id="drupalpassword_$drupalname" type="password" name="drupalpassword" autocomplete="off" value="" class="password">
            </div>
            <div class="col-sm-2">
                <button type="button" class="btn btn-default" onclick="spinner(this); \$('#action_$drupalname').val('drupalpassword'); submit();">Set!</button>
            </div>
        </div>
        <div class="row">
            <div class="col-sm-12">
                <small><a href="http://$dom/drupal/user/login" target="_blank">Click here to</a> access the Drupal management UI for $drupal</small>
            </div>
        </div>
    <div style="height:10px;"></div>
END
    ;

    my $backupbutton = qq|<button class="btn btn-primary" type="button" rel="tooltip" data-placement="top" title="$backup_tooltip" onclick="\$('#action_$drupalname').val('drupalbackup'); \$('#drupalform_$drupalname').submit(); spinner(this);">Backup database</button>|;

    if ($drupal eq 'new') {
        $backup_tooltip = "You must save before you can back up";
        $resetbutton = qq|<button class="btn btn-info" type="button" rel="tooltip" data-placement="top" title="Click to create your new website!" onclick="if (\$('#drupaldomain_new').val()) {spinner(this); \$('#action_$drupalname').val('drupalcreate'); \$('#drupalform_$drupalname').submit();} else {\$('#drupaldomain_new').css('border','1px solid #f39c12'); \$('#drupaldomain_new').focus(); return false;}">Create website</button>|;

        $manageform = <<END
    <div class="tab-pane" id="$drupal-site">
    <form class="passwordform drupalform" id="drupalform_$drupalname" action="index.cgi?tab=drupal" method="post" accept-charset="utf-8" autocomplete="off">
        <div>
            <small>The website's domain name:</small>
            <input class="drupaldomain required" id="drupaldomain_$drupalname" type="text" name="drupaldomain_$drupalname" value="" autocomplete="off">
        </div>
        <div>
            <small>Aliases for the website:</small>
            <input class="drupaldomain" id="drupalaliases_$drupalname" type="text" name="drupalaliases_$drupalname" value="$drupalaliases" autocomplete="off">
        </div>
        <small>Set password for Drupal user 'admin':</small>
        <div class="row">
            <div class="col-sm-10">
                <input id="drupalpassword_$drupalname" type="password" name="drupalpassword" autocomplete="off" value="" disabled class="disabled" placeholder="Password can be set after creating website">
            </div>
            <div class="col-sm-2">
                <button class="btn btn-default disabled" type="button" disabled>Set!</button>
            </div>
        </div>
    <div style="height:10px;"></div>
END
        ;
        $backupbutton = qq|<button class="btn btn-primary disabled" rel="tooltip" data-placement="top" title="$backup_tooltip" onclick="spinner(this); return false;">Backup database</button>|;
    }

    my $restorebutton = qq|<button class="btn btn-primary disabled" disabled type="button" rel="tooltip" data-placement="top" title="You must back up before you can restore" onclick=return false;">Restore database</button>|;
    my $ftime;

    if (-e "/var/lib/drupal/drupal_$drupalname.sql") {
        $ftime = make_date( (stat("/var/lib/drupal/drupal_$drupalname.sql"))[9] ) . ' ' . `date +%Z`;
        $restorebutton = qq|<button class="btn btn-primary" type="button" rel="tooltip" data-placement="top" title="Restore database from backup made $ftime" onclick="spinner(this); \$('#action_$drupalname').val('drupalrestore'); \$('#drupalform_$drupalname').submit();">Restore database</button>|;
    }

    my $backupform .= <<END
    <div class="mbl">
        $backupbutton
        $restorebutton
        $resetbutton
        <input type="hidden" name="action" id="action_$drupalname">
        <input type="hidden" name="drupal" id="drupal_$drupalname" value="$drupal">
    </div>
    </form>
    </div>
END
    ;
     return $manageform . "\n" . $backupform;
}

1;
