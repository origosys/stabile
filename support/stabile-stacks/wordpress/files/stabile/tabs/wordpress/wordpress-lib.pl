#!/usr/bin/perl

use JSON;

my $dnsdomain_json = `curl -k https://$gw/stabile/networks?action=getdnsdomain`;
my $dom_obj = from_json ($dnsdomain_json);
my $dnsdomain =  $dom_obj->{'domain'};
my $dnssubdomain = $dom_obj->{'subdomain'};
$dnsdomain = '' unless ($dnsdomain =~  /\S+\.\S+$/ || $dnsdomain =~  /\S+\.\S+\.\S+$/);
my $esc_dnsdomain = $dnsdomain;
$esc_dnsdomain =~ s/\./\\./g;

sub wordpress {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
        # Generate and return the HTML form for this tab

        # First let's make sure install.php has been patched - WP may have been upgraded
        unless (`grep "HTTP_HOST" /usr/share/wordpress/wp-admin/install.php`) {
            `/usr/local/bin/stabile-wordpress.sh`;
            #            system(q|perl -pi -e 's/(\/\/ Sanity check\.)/$1\n\$showsite=( (strpos(\$_SERVER[HTTP_HOST], ".stabile.io")===FALSE)? \$_SERVER[HTTP_HOST] : substr(\$_SERVER[HTTP_HOST], 0, strpos(\$_SERVER[HTTP_HOST], ".stabile.io")) );\n/' /usr/share/wordpress/wp-admin/install.php|);
            #            system(q|perl -pi -e 's/(^<p class="step"><a href="\.\.\/wp-login\.php".+<\/a>)/<!-- $1 --><script>var pipeloc=location\.href\.substring(0,location.href.indexOf("\/home")); location=pipeloc \+ ":10000\/stabile\/?show=<?php echo \$showsite; ?>-site";<\/script>/;'  /usr/share/wordpress/wp-admin/install.php|);
            # Crazy amount of escaping required
            #            system(qq|perl -pi -e "s/(step=1)/\\\$1\&host=' \. \\\\\\\$_SERVER[HTTP_HOST] \.'/;" /usr/share/wordpress/wp-admin/install.php|);
            #            system(q|perl -pi -e 's/(step=2)/$1\&host=<?php echo \$_SERVER[HTTP_HOST]; ?>/;' /usr/share/wordpress/wp-admin/install.php|);
        } else {
            ;# "Already patched\n";
        }

        my $form;
        opendir(DIR,"/etc/wordpress") or die "Cannot open /etc/wordpress\n";
        my @wpfiles = readdir(DIR);
        closedir(DIR);
        my %aliases;
        foreach my $file (@wpfiles) {
            next unless ($file =~ /config-(.+)\.php/);
            if (-l "/etc/wordpress/$file") {
                my $link = readlink("/etc/wordpress/$file");
                $aliases{$link} .= "$1 ";
            }
        }

        foreach my $file (@wpfiles) {
            next if (-l "/etc/wordpress/$file");
            next unless ($file =~ /config-(.+)\.php$/);
            my $wp = $1;
            my $wpname = $wp;
            $wpname = $1 if ($wpname =~ /(.+)\.$dnsdomain/);
            $wpname =~ tr/\./_/;
            $form .= getWPtab($wp, $wpname, $aliases{$file});
        }
        $form .=  getWPtab('new', 'new');
        $form .=  getWPtab('wpsecurity', 'wpsecurity');

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
                \$('#wpdomain_new').css('border','1px solid #CCCCCC'); \$('#wpdomain_new').focus();
            }
            \$("#currentwpadmin").parent().show();
            if (!match || match[1] == 'default' || match[1] == 'new') {
                \$("#currentwp").attr("href", "http://$dom/");
                \$("#currentwp").text("to default WordPress website");
                \$("#currentwpadmin").attr("href", "https://$dom/home/wp-admin/");
                \$("#currentwpadmin").text("to default WordPress console");
            } else {
                var siteaddr = site;
                if (site.indexOf(".")==-1) siteaddr = site + ".$dnsdomain"
                \$("#currentwp").attr("href", "http://" + siteaddr + "/");
                \$("#currentwp").text("to " + site + " website");
                \$("#currentwpadmin").attr("href", "https://" + siteaddr + "/home/wp-admin/");
                \$("#currentwpadmin").text("to " + site + " administration");
            }
            if (match) {
                setTimeout(
                    function() {
                        if (\$("#wpaliases_h_" + match[1]).val() == '')
                            \$("#wpaliases_" + match[1]).val("");
                        \$("#wppassword_" + match[1]).val("--");
                        \$("#wppassword_" + match[1]).val("");
                    }, 100
                )
            }
        })

        \$(".wpdomain").keypress(function(event){
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

        \$(".wpalias").keypress(function(event){
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

        function confirmWPAction(action, wpname) {
            if (action == 'wpremove') {
                \$('#action_' + wpname).val(action);
                \$('#confirmdialog').prop('actionform', '#wpform_' + wpname);
                \$('#confirmdialog').modal({'backdrop': false, 'show': true});
                return false;
            }
        };

END
        ;
        return $js;


    } elsif ($action eq 'tab') {
        return getWPdropdown();

        # This is called from index.cgi (the UI)
    } elsif ($action eq 'upgrade') {
        my $res;
        my $srcloc = "/usr/share/wordpress";
        my $dumploc = $in{targetdir};

        if (-d $dumploc) {
            # Dump database
            `mysqldump --databases \$(mysql -N information_schema -e "SELECT DISTINCT(TABLE_SCHEMA) FROM tables WHERE TABLE_SCHEMA LIKE 'wordpress_%'") > $dumploc/wordpress.sql`;
            # Copy wp-content (remove target first, in order to be able to compare sizes)
            `rm -r $dumploc/wp-content`;
            `rm -r $dumploc/blogs.dir`;
            `cp -r $srcloc/wp-content $dumploc`;
            `cp -r $srcloc/blogs.dir $dumploc`;
            # Also copy /etc/wordpress
            `cp -r /etc/wordpress $dumploc`;
        }

        my $srcsize = `du -bs $srcloc`;
        $srcsize = $1 if ($srcsize =~ /(\d+)/);
        my $dumpsize = `du -bs $dumploc/wp-content`;
        $dumpsize = $1 if ($dumpsize =~ /(\d+)/);
        if ($srcsize == $dumpsize) {
            $res = "OK: WordPress data and database dumped successfully to $dumploc";
        } else {
            $res = "There was a problem dumping WordPress data to $dumploc ($srcsize <> $dumpsize)!";
        }
        return $res;

        # This is called from stabile-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {
        my $srcloc = $in{sourcedir};
        my $res;
        my $dumploc  = "/usr/share/wordpress/wp-content";
        if (-d $srcloc && -d $dumploc) {
            $res = "OK: ";
            my $srcdir = "wp-content/*";
            $res .= qq|copying $srcloc/$srcdir -> $dumploc, |;
            $res .= `cp --backup -a $srcloc/$srcdir "$dumploc"`;
            $res .= `chown -R www-data:www-data $dumploc`;

            $srcdir = "blogs.dir/*";
            $dumploc = "/usr/share/wordpress/blogs.dir";
            $res .= qq|copying $srcloc/$srcdir -> $dumploc, |;
            `mkdir $dumploc` unless (-e "$dumploc");
            $res .= `cp --backup -a $srcloc/$srcdir "$dumploc"`;
            # $res .= `chown -R www-data:www-data $dumploc`;

            $srcdir = "wordpress/*";
            $dumploc  = "/etc/wordpress/";
            $res .= qq|copying $srcloc/$srcdir -> $dumploc, |;
            $res .= `cp --backup -a $srcloc/$srcdir "$dumploc"`;

            if (-e "$srcloc/wordpress.sql") {
                $res .= qq|restoring db, |;
                $res .= `/usr/bin/mysql < $srcloc/wordpress.sql`;
            }
            # User id's may have changed
            `chown -R www-data:www-data /usr/share/wordpress`;

            # Set management link
            #            `curl -k -X PUT --data-urlencode "PUTDATA={\\"uuid\\":\\"this\\",\\"managementlink\\":\\"/stabile/pipe/http://{uuid}:10000/stabile/\\"}" https://10.0.0.1/stabile/images`;
            chomp $res;
        }
        $res = "Not copying $srcloc/* -> $dumploc" unless ($res);
        #`/etc/init.d/apache2 start`;
        #`umount /mnt/fuel/*`;
        return $res;

    } elsif ($action eq 'wpremove' && $in{wp}) {
        my $message;
        my $wp = $in{wp};
        my $dom = $wp;
        my $wpname = $wp;
        $wpname = $1 if ($wpname =~ /(.+)\.$dnsdomain$/);
        $wpname =~ tr/\./_/;
        $wp = $1 if ($wp =~ /(.+)\.$dnsdomain$/);
        $dom = "$dom.$dnsdomain" unless ($dom =~ /\./ || $dom eq 'default');
        my $db = "wordpress_$wpname";
        $message .= `mysqldump $db > /var/lib/wordpress/$db.sql`;
        `echo "drop database $db;" | mysql`;

        opendir(DIR,"/etc/wordpress") or die "Cannot open /etc/wordpress\n";
        my @wpfiles = readdir(DIR);
        closedir(DIR);
        # Now remove aliases
        my $target = "config-$dom.php";
        foreach my $file (@wpfiles) {
            next unless ($file =~ /config-(.+)\.php/);
            my $fname = $1;
            $fname = $1 if ($fname =~ /(.+)\.$dnsdomain$/);
            if (-l "/etc/wordpress/$file") { # Check if it is a link
                my $link = readlink("/etc/wordpress/$file");
                if ($link eq $target) {
                    unlink ("/etc/wordpress/$file");
                    # Remove DNS entry if not a FQDN
                    $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnsdelete\&name=$fname"` unless ($fname =~ /\./);
                }
            }
        }

        if ($dom eq 'default') { # default should always exist - recreate
            `echo "create database $db;" | mysql`;
            # Change the managementlink property of the image
            #    `curl -k -X PUT --data-urlencode 'PUTDATA={"uuid":"this","managementlink":"/stabile/pipe/http://{uuid}/home/wp-admin/install.php"}' https://$gw/stabile/images`;
            $message .=  "<div class=\"message\">Default website was reset!</div>";
            $message .=  qq|<script>loc=document.location.href; document.location=loc.substring(0,loc.indexOf(":10000")) + "/home/wp-admin/install.php?host=$dom"; </script>|;
        } else {
            unlink("/etc/wordpress/config-$dom.php");
            my $wpc2 = "/usr/share/wordpress/blogs.dir/$wpname";
            `rm -r "$wpc2"`;

            # Remove DNS entry if not a FQDN
            $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnsdelete\&name=$wp"` unless ($wp =~ /\./);

            $postscript .= qq|\$('#nav-tabs a[href="#default-site"]').tab('show');\n|;
            $message .=  "<div class=\"message\">Website $dom was removed!</div>";
            opendir(DIR,"/etc/wordpress") or die "Cannot open /etc/wordpress\n";
            @wpfiles = readdir(DIR);
            closedir(DIR);
        }
        return $message;
    } elsif ($action eq 'wpcreate' && $in{wpdomain_new}) {
        my $message;
        my $wp = $in{wpdomain_new};
        my $wpname = $wp;
        $wp = $1 if ($wp =~ /(.+)\.$dnsdomain$/);
        $wpname = $1 if ($wpname =~ /(.+)\.$dnsdomain$/);
        $wpname =~ tr/\./_/;
        my $dom = $wp;
        $dom = "$dom.$dnsdomain" unless ($dom =~ /\./ || $dom eq 'default');
        my $db = "wordpress_$wpname";
        if (-e "/etc/wordpress/config-$dom.php" || $wp eq 'new' || $wp eq 'default') {
            $message .=  "<div class=\"message\">Website $dom already exists!</div>";
            #       $postscript .= qq|\$('#nav-tabs a[href="#new-site"]').tab('show');\n|;
        } elsif ($dom =~ /\.$dnsdomain$/  && !dns_check($wp)) {
            $message .=  "<div class=\"message\">Domain $wp.$dnsdomain is not available - please use a domain that's available, and make sure your engine is linked!</div>";
        } else {
            # Configure WordPress / Debian
            my $target = "config-$dom.php";

            $message .= `cp /etc/wordpress/config-default.php /etc/wordpress/$target`;
            $message .= `perl -pi -e "s/php/php\\ndefine('UPLOADS', 'blogs.dir\\/$wpname\\/uploads');/;" /etc/wordpress/$target`;
            $message .= `perl -pi -e 's/wordpress_default/$db/;' /etc/wordpress/$target`;
            $message .= `perl -pi -e 's/wordpress\\\/wp-content/wordpress\\\/blogs.dir\\\/$wpname/;' /etc/wordpress/$target`;
        #    $message .= `perl -pi -e 's/home\\\/wp-content/home\\\/blogs.dir\\\/$wpname/;' /etc/wordpress/$target`;
            my $wpc2 = "/usr/share/wordpress/blogs.dir/$wpname";
            `mkdir -p $wpc2; chown www-data:www-data $wpc2`;
            my $wphome = '/usr/share/wordpress/wp-content';
            `cp -a $wphome/languages/ $wphome/plugins/ $wphome/themes/ /usr/share/wordpress/blogs.dir/$wpname`;
            # Create WordPress database
            `echo "create database $db;" | mysql`;
            # Create DNS entry if not a FQDN
            $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$wp\&value=$externalip"` unless ($wp =~ /\./);

            # Create aliases
            if (defined $in{"wpaliases_new"}) {
                my @wpaliases = split(' ', $in{"wpaliases_new"});
                foreach my $alias (@wpaliases) {
                    my $dom1 = $alias;
                    $dom1 = "$alias.$dnsdomain" unless ($alias =~ /\./);
                    $alias = $1 if ($alias =~ /(.+)\.$dnsdomain/);
                    my $link = "/etc/wordpress/config-$dom1.php";
                    unless (-e $link) {
                        $message .= `cd /etc/wordpress; ln -s "$target" "$link"`;
                        # Create DNS entry if not a FQDN
                        $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$alias\&value=$externalip"` unless ($alias =~ /\./);
                        $message .=  "<div class=\"message\">alias $target -> $link was created!</div>";
                    }
                }
            }

            $message .=  "<div class=\"message\">Website $dom was created!</div>";
            $postscript .= qq|\$('#nav-tabs a[href="#$wpname-site"]').tab('show');\n|;
            $message .=  qq|<script>loc=document.location.href; document.location=loc.substring(0,loc.indexOf(":10000")) + "/home/wp-admin/install.php?host=$dom"; </script>|;
        }
        return $message;
    } elsif ($action eq 'wpaliases' && $in{wp}) {
        my $message;
        my $wp = $in{wp};
        my $wpname = $wp;
        $wp = $1 if ($wp =~ /(.+)\.$dnsdomain$/);
        $wpname = $1 if ($wpname =~ /(.+)\.$dnsdomain$/);
        $wpname =~ tr/\./_/;
        my $dom = $wp;
        $dom = "$dom.$dnsdomain" unless ($dom =~ /\./ || $dom eq 'default');
        opendir(DIR,"/etc/wordpress") or die "Cannot open /etc/wordpress\n";
        my @wpfiles = readdir(DIR);
        closedir(DIR);
        my %aliases;
        if (defined $in{"wpaliases_$wpname"}) {
            my $target = "config-$dom.php";
            if (-e "/etc/wordpress/$target" && !(-l "/etc/wordpress/$target")) {
                my @wpaliases = split(' ', $in{"wpaliases_$wpname"});
                foreach my $alias (@wpaliases) {$aliases{$alias} = 1;}
                # First locate and unlink existing aliases that should be deleted
                foreach my $file (@wpfiles) {
                    next unless ($file =~ /config-(.+)\.php/);
                    my $dom = $1;
                    my $fname = $dom;
                    $fname = $1 if ($dom =~ /(.+)\.$dnsdomain/);
                    if (-l "/etc/wordpress/$file") {
                        my $link = readlink("/etc/wordpress/$file");
                        if ($link eq $target) {
                            unless ($aliases{$fname} || $aliases{$dom}) { # This alias should be deleted
                                unlink ("/etc/wordpress/$file");
                                # Remove DNS entry if not a FQDN
                                $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnsdelete\&name=$fname"` unless ($fname =~ /\./);
                                $message .=  "<div class=\"message\">Alias $file removed!</div>";
                            }
                            $aliases{$fname} = 0; # No need to recreate this alias
                        }
                    }
                }
                # Then create aliases
                foreach my $alias (@wpaliases) {
                    my $newdom = $alias;
                    $newdom = "$alias.$dnsdomain" unless ($alias =~ /\./);
                    $alias = $1 if ($alias =~ /(.+)\.$dnsdomain$/);
                    my $link = "/etc/wordpress/config-$newdom.php";
                    # Check availability of new domain names
                    if ($newdom =~ /\.$dnsdomain$/ && !(-e $link) && !dns_check($newdom)) {
                        $message .=  "<div class=\"message\">Domain $alias.$dnsdomain is not available!</div>";
                    } elsif (($aliases{$alias} || $aliases{$newdom}) && !(-e $link)) {
                        $message .= `cd /etc/wordpress; ln -s "config-$dom.php" "$link"`;
                        # Create DNS entry if not a FQDN
                        $message .= `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscreate\&name=$alias\&value=$externalip"` unless ($alias =~ /\./);
                        #                    $message .=  "<div class=\"message\">Alias $alias created!</div>";
                        # Re-read directory
                    } else {
                        #                    $message .=  "<div class=\"message\">Alias $alias not created!</div>";
                    }
                }
                opendir(DIR,"/etc/wordpress") or die "Cannot open /etc/wordpress\n";
                @wpfiles = readdir(DIR);
                closedir(DIR);
                $message .=  "<div class=\"message\">Aliases updated for $wp!</div>";
            } else {
                $message .=  "<div class=\"message\">Target $target does not exist!</div>";
            }
        }
        #    $postscript .= qq|\$('#nav-tabs a[href="#$wpname-site"]').tab('show');\n|;
        return $message;
    } elsif ($action eq 'wprestore' && $in{wp}) {
        my $message;
        my $wp = $in{wp};
        my $wpname = $wp;
        $wpname = $1 if ($wpname =~ /(.+)\.$dnsdomain/);
        $wpname =~ tr/\./_/;
        my $db = "wordpress_$wpname";
        if (-e "/var/lib/wordpress/$db.sql") {
            #        `echo "drop database wordpress; create database wordpress;" | mysql`;
            $message .=  `mysql $db < /var/lib/wordpress/$db.sql`;
            if (`echo status | mysql $db`) {
                $message .=  "<div class=\"message\">WordPress database restored.</div>";
            } else {
                $message .=  "<div class=\"message\">WordPress database $db not found!</div>";
            }
        }
        #    $postscript .= qq|\$('#nav-tabs a[href="#$wpname-site"]').tab('show');\n|;
        return $message;
    } elsif ($action eq 'wpbackup' && $in{wp}) {
        my $message;
        my $wp = $in{wp};
        my $wpname = $wp;
        $wpname = $1 if ($wpname =~ /(.+)\.$dnsdomain/);
        $wpname =~ tr/\./_/;
        my $db = "wordpress_$wpname";
        $message .=  `mysqldump $db > /var/lib/wordpress/$db.sql`;
        $message .=  "<div class=\"message\">WordPress database was backed up to /var/lib/wordpress/$db.sql!</div>" if (-e "/var/lib/wordpress/$db.sql");
        #    $postscript .= qq|\$('#nav-tabs a[href="#$wpname-site"]').tab('show');\n|;
        return $message;
    } elsif ($action eq 'wppassword' && $in{wp}) {
        my $message;
        my $wp = $in{wp};
        my $wpname = $wp;
        $wpname = $1 if ($wpname =~ /(.+)\.$dnsdomain/);
        $wpname =~ tr/\./_/;
        my $db = "wordpress_$wpname";
        my $pwd = $in{wppassword};
        if ($pwd) {
            $message .=  `echo "UPDATE wp_users SET user_pass = MD5('$pwd') WHERE ID = 1;" | mysql -s $db`;
            $message .=  "<div class=\"message\">The WordPress password was changed!</div>";
        }
        #    $postscript .= qq|\$('#nav-tabs a[href="#$wpname-site"]').tab('show');\n|;
        return $message;
    } elsif ($action eq 'wplimit') {
        my $message;
        if (defined $in{wplimit}) {
            my $limit = $in{wplimit};
            my ($validlimit, $mess) = validate_limit($limit);
            $message .= $mess;
            if ($validlimit) {
                if (`grep '#stabile' /usr/share/wordpress/.htaccess`)
                {
                    $message .= `perl -pi -e 's/allow from (.*) \#stabile/allow from $validlimit #stabile/;' /usr/share/wordpress/.htaccess`;
                } else {
                    $validlimit =~ s/\\//g;
                    `echo "<files wp-login.php>\norder deny,allow\ndeny from all\nallow from $validlimit #stabile\n</files>" >> /usr/share/wordpress/.htaccess`;
                }
                $message .=  "<div class=\"message\">WordPress admin access was changed!</div>";
            } else {
                $message .= `perl -i -p0e 's/<files wp-login\.php>\n.*\n.*\n.*\n<\/files>//smg' /usr/share/wordpress/.htaccess`;
                $message .=  "<div class=\"message\">WordPress admin access is now open from anywhere!</div>";
                $wplimit = '';
            }
            my $allow = `cat /usr/share/wordpress/.htaccess`;
            $wplimit = $1 if ($allow =~ /allow from (.+) \#stabile/);
        }
        return $message;

    } elsif ($action eq 'wpletsencrypt') {
        my $message;
        my $confs = "/etc/apache2/sites-available/*-ssl.conf";
        if (defined $in{wpletsencryptcheck}) {
            my $encrypt = $in{wpletsencryptcheck} eq '2';
            if ($encrypt) {
                # Run getssl
                if ($externalip) {
                    my $res = `ping -c1 -w2 1.1.1.1`;
                    if ($res =~ /100\% packet loss/) {
                        $message .= "No Internet connectivity - not running letsencrypt";
                    } elsif ($externalip =~ /^192\.168\./){
                        $message .= "External IP is RFC 1819 - not running GetSSL";
                    } elsif ($dnsdomain) {
                        opendir(DIR,"/etc/wordpress") or die "Cannot open /etc/wordpress\n";
                        my @wpfiles = readdir(DIR);
                        closedir(DIR);
                        my @domains;
                        my $acl;
                        foreach my $file (@wpfiles) {
                            next if ($file eq 'config-default.php');
                            if ($file =~ /config-(.+)\.php/) {
                                push @domains, $1;
                                $acl .= qq|\n'/var/www/html/.well-known/acme-challenge'|;
                            }
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
                                $message .= "<div class=\"message\">Let's encrypt centificates were installed for $externalip.$dnssubdomain.$dnsdomain $sans</div>";
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
        if (defined $in{wpredirectcheck}) {
            my $redirecting = `grep RewriteRule /etc/apache2/sites-available/000-default.conf`;
            my $redirect = defined $in{wpredirect} || $in{wpredirectcheck} eq '2';
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

## Returns HTML for drop-down for selecting WordPress sites
sub getWPdropdown {

# Redirect to WordPress install page if default site not configured
    my $dropdown;
    if (!(`echo "SHOW TABLES LIKE 'wp_posts'" | mysql wordpress_default`)) {
        # Allow WordPress to log into mysql
        `echo "ALTER USER 'root'\@'localhost' IDENTIFIED WITH mysql_native_password BY '';" | mysql`;
        $dropdown = <<END
        <li class="dropdown">
            <a href="#" id="myTabDrop1" class="dropdown-toggle" data-toggle="dropdown">wordpress <b class="caret"></b></a>
            <span class="dropdown-arrow"></span>
            <ul class="dropdown-menu" role="menu" aria-labelledby="myTabDrop1">
                <li><a href="#default-site" tabindex="-1" data-toggle="tab" onclick='loc=document.location.href; document.location=loc.substring(0,loc.indexOf(":10000")) + "/home/wp-admin/install.php?host=default";'>Configure default website</a></li>
            </ul>
        </li>
END
        ;
    } else {
        my $websitedrops;
        opendir(DIR,"/etc/wordpress") or die "Cannot open /etc/wordpress\n";
        my @wpfiles = readdir(DIR);
        closedir(DIR);

        foreach my $file (@wpfiles) {
            next if (-l "/etc/wordpress/$file"); # This is an alias - skip
            next unless ($file =~ /config-(.+)\.php/);
            my $wp = $1;
            next if $wp eq 'default';
            my $wpname = $wp;
            $wpname = $1 if ($wpname =~ /(.+)\.$dnsdomain/);
            $wpname =~ tr/\./_/;
            $websitedrops .= <<END
<li><a href="#$wpname-site" tabindex="-1" data-toggle="tab" id="$wp">$wp</a></li>
END
            ;
        }

        $dropdown = <<END
        <li class="dropdown">
            <a href="#" id="myTabDrop1" class="dropdown-toggle" data-toggle="dropdown">wordpress <b class="caret"></b></a>
            <span class="dropdown-arrow"></span>
            <ul class="dropdown-menu" role="menu" aria-labelledby="myTabDrop1">
                <li><a href="#default-site" tabindex="-1" data-toggle="tab">Default website</a></li>
                $websitedrops
                <li><a href="#new-site" tabindex="-1" data-toggle="tab">Add new website...</a></li>
                <li><a href="#wp-security" tabindex="-1" data-toggle="tab">WordPress security</a></li>
            </ul>
        </li>
END
        ;
    }
    return $dropdown;

}

## Returns HTML for a single WordPress configuration tab
sub getWPtab {
    my $wp = shift;
    my $wpname = shift;
    my $wpaliases = shift;
    $wpaliases = join(' ', split(' ', $wpaliases));

    my $wpuser;
    if ($wp eq 'new') {
        $wpuser = "admin";
    } elsif ($wp eq 'wpsecurity') {
        my $allow = `cat /usr/share/wordpress/.htaccess`;
        my $wplimit;
        $wplimit = $1 if ($allow =~ /allow from (.+) \#stabile/);
        my $wpletsencrypt = (-e "/root/.getssl/$externalip.$dnssubdomain.$dnsdomain/getssl.cfg")?" checked":'';
        my $wpredirect = (`grep RewriteRule /etc/apache2/sites-available/000-default.conf`)?"checked":"";
        my $renewbtn = ($wpletsencrypt)?qq|<button onclick="\$('#wpletsencryptcheck').val('2'); salert('Hang on - this could take a minute or two...'); spinner(this); \$(this.form).submit();" class="btn btn-info btn-sm">renew</button>|:'';

        my $curipwp;
        $curipwp = qq|<span style="float: left; font-size: 13px;">leave empty to allow login from anywhere, your current IP is <a href="#" onclick="\$('#wplimit').val('$ENV{HTTP_X_FORWARDED_FOR} ' + \$('#wplimit').val());">$ENV{HTTP_X_FORWARDED_FOR}</a></span>| if ($ENV{HTTP_X_FORWARDED_FOR});

        my $wpsecurityform = <<END
<div class="tab-pane" id="wp-security">
    <form class="passwordform" action="index.cgi?action=wplimit\&tab=wordpress\&show=wp-security" method="post" accept-charset="utf-8" style="margin-bottom:36px;" autocomplete="off">
        <div>
            <small>Limit wordpress login for all sites to:</small>
            <div class="row">
                <div class="col-sm-10">
                    <input id="wplimit" type="text" name="wplimit" value="$wplimit" placeholder="IP address or network, e.g. '192.168.0.0/24 127.0.0.1'">
                    $curipwp
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default" type="submit" onclick="spinner(this);">Set!</button>
                </div>
            </div>
        </div>
    </form>
    <form class="passwordform" action="index.cgi?action=wpletsencrypt\&tab=wordpress\&show=wp-security" method="post" accept-charset="utf-8" autocomplete="off">
        <div style="display:inline-block;">
            <input id="wpletsencrypt" type="checkbox" $wpletsencrypt name="wpletsencrypt" value="wpletsencrypt" onchange="if (this.checked) {\$('#wpletsencryptcheck').val('2'); salert('Hang on - this could take a minute or two...');} spinner(this); \$(this.form).submit();">
            <small>Get Let's Encrypt certificate and enable TLS for all sites $renewbtn</small>
        </div>
        <input type="hidden" id="wpletsencryptcheck" name="wpletsencryptcheck" value="1">
    </form>
    <form class="passwordform" id="wpredirectform" action="index.cgi?action=wpletsencrypt\&tab=wordpress\&show=wp-security" method="post" accept-charset="utf-8" autocomplete="off">
        <div>
            <input id="wpredirect" type="checkbox" $wpredirect name="wpredirect" value="wpredirect" onchange="if (this.checked) {\$('#wpredirectcheck').val('2');} spinner(this); \$(this.form).submit();">
            <small>Redirect http &#8594; https for all sites</small>
        </div>
        <input type="hidden" id="wpredirectcheck" name="wpredirectcheck" value="1">
    </form>
</div>
END
        ;
        return $wpsecurityform;
    } else {
        my $db = "wordpress_$wpname";
        $wpuser = `echo "select user_login from wp_users where id=1;" | mysql -s $db`;
        chomp $wpuser;
        $wpuser = $wp unless ($wpuser);
    }

    my $resetbutton = qq|<button class="btn btn-danger" rel="tooltip" data-placement="top" title="This will remove your website and wipe your database - be absolutely sure this is what you want to do!" onclick="confirmWPAction('wpremove', '$wpname');" type="button">Remove website</button>|;

    my $backup_tooltip = "Click to back up your WordPress database";

    my $manageform = <<END
    <div class="tab-pane" id="$wpname-site">
    <form class="passwordform wpform" id="wpform_$wpname" action="index.cgi?tab=wordpress\&show=$wpname-site" method="post" accept-charset="utf-8" autocomplete="off">
        <div>
            <small>The website's domain name:</small>
            <input class="wpdomain" id="wpdomain_$wpname" type="text" name="wpdomain_$wpname" value="$wp" disabled autocomplete="off">
        </div>
        <small>Aliases for the website:</small>
        <div class="row">
            <div class="col-sm-10">
                <input class="wpalias" id="wpaliases_$wpname" type="text" name="wpaliases_$wpname" value="$wpaliases" autocomplete="off" />
                <input type="hidden" id="wpaliases_h_$wpname" name="wpaliases_h_$wpname" value="$wpaliases" autocomplete="off" />
            </div>
            <div class="col-sm-2">
                <button type="submit" class="btn btn-default" onclick="spinner(this); \$('#action_$wpname').val('wpaliases'); submit();" rel="tooltip" data-placement="top" title="Aliases that are not FQDNs will be created in the $dnsdomain domain as [alias].$dnsdomain">Set!</button>
            </div>
        </div>
        <small>Set password for WordPress user '$wpuser':</small>
        <div class="row">
            <div class="col-sm-10">
                <input id="wppassword_$wpname" type="password" name="wppassword" autocomplete="off" value="" class="password">
            </div>
            <div class="col-sm-2">
                <button type="submit" class="btn btn-default" onclick="spinner(this); \$('#action_$wpname').val('wppassword'); submit();">Set!</button>
            </div>
        </div>
    <div style="height:10px;"></div>
END
    ;

    my $backupbutton = qq|<button class="btn btn-primary" rel="tooltip" data-placement="top" title="$backup_tooltip" onclick="\$('#action_$wpname').val('wpbackup'); \$('#wpform_$wpname').submit(); spinner(this);">Backup database</button>|;

    if ($wp eq 'new') {
        $backup_tooltip = "You must save before you can back up";
        $resetbutton = qq|<button class="btn btn-info" type="button" rel="tooltip" data-placement="top" title="Click to create your new website!" onclick="if (\$('#wpdomain_new').val()) {spinner(this); \$('#action_$wpname').val('wpcreate'); \$('#wpform_$wpname').submit();} else {\$('#wpdomain_new').css('border','1px solid #f39c12'); \$('#wpdomain_new').focus(); return false;}">Create website</button>|;

        $manageform = <<END
    <div class="tab-pane" id="$wp-site">
    <form class="passwordform wpform" id="wpform_$wpname" action="index.cgi?tab=wordpress\&show=$wpname-site" method="post" accept-charset="utf-8" autocomplete="off">
        <div>
            <small>The website's domain name:</small>
            <input class="wpdomain required" id="wpdomain_$wpname" type="text" name="wpdomain_$wpname" value="" autocomplete="off">
        </div>
        <div>
            <small>Aliases for the website:</small>
            <input class="wpdomain" id="wpaliases_$wpname" type="text" name="wpaliases_$wpname" value="$wpaliases" autocomplete="off">
        </div>
        <small>Set password for WordPress user 'admin':</small>
        <div class="row">
            <div class="col-sm-10">
                <input id="wppassword_$wpname" type="password" name="wppassword" autocomplete="off" value="" disabled class="disabled" placeholder="Password can be set after creating website">
            </div>
            <div class="col-sm-2">
                <button class="btn btn-default disabled" disabled>Set!</button>
            </div>
        </div>
    <div style="height:10px;"></div>
END
        ;
        $backupbutton = qq|<button class="btn btn-primary disabled" rel="tooltip" data-placement="top" title="$backup_tooltip" onclick="spinner(this); return false;">Backup database</button>|;
    }

    my $restorebutton = qq|<button class="btn btn-primary disabled" rel="tooltip" data-placement="top" title="You must back up before you can restore" onclick="spinner(this); return false;">Restore database</button>|;
    my $ftime;

    if (-e "/var/lib/wordpress/wordpress_$wpname.sql") {
        $ftime = make_date( (stat("/var/lib/wordpress/wordpress_$wpname.sql"))[9] ) . ' ' . `date +%Z`;
        $restorebutton = qq|<button class="btn btn-primary" rel="tooltip" data-placement="top" title="Restore database from backup made $ftime" onclick="spinner(this); \$('#action_$wpname').val('wprestore'); \$('#wpform_$wpname').submit();">Restore database</button>|;
    }

    my $backupform .= <<END
    <div class="mbl">
        $backupbutton
        $restorebutton
        $resetbutton
        <input type="hidden" name="action" id="action_$wpname">
        <input type="hidden" name="wp" id="wp_$wpname" value="$wp">
    </div>
    </form>
    </div>
END
    ;
     return $manageform . "\n" . $backupform;
}

1;
