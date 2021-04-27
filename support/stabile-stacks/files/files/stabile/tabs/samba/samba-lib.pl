#!/usr/bin/perl

sub samba {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    my $dominfo;
    my $intip = `cat /tmp/internalip`;
    $intip = `cat /etc/origo/internalip` if (-e '/etc/origo/internalip');
    $dominfo = `samba-tool domain info $intip` unless ($action eq 'restore');
    my $sambadomain;
    $sambadomain = $1 if ($dominfo =~ /Domain\s+: (\S+)/);
    my $sambahost;
    $sambahost = `hostname` unless ($action eq 'restore');
    chomp $sambahost;

    if ($action ne 'restore' && `grep "AjyxgfFJ69234u" /etc/apache2/conf.d/auth_tkt.conf`) { #Change default tkt secret
        my @chars = ("A".."Z", "a".."z", "0".."9");
        my $secret;
        $secret .= $chars[rand @chars] for 1..24;
        `perl -pi -e 's/AjyxgfFJ69234u/$secret/;' /etc/apache2/conf.d/auth_tkt.conf`;
        `/etc/init.d/apache2 restart`;
    }

    if ($action eq 'form') {
# Generate and return the HTML form for this tab
        my $cmd = qq[cat /etc/samba/smb.conf | grep "write list"];
        my $wlist = `$cmd`;
        chomp $wlist;
        my $sambawritelist;
        if ($wlist =~ /write list =(.+)/) {
            $wlist = $1;
            my @writers = quotewords('\s+', 1, $wlist);
            my @vals;
            foreach my $writer (@writers) {
                $writer = $2 if ($writer =~ /(\+)?".+\\(.+)"/);
                push(@vals, "$writer") if ($writer);
            }
            $sambawritelist = join(", ", @vals);
        }

        $cmd = qq[cat /etc/samba/smb.conf | grep "invalid users" | uniq];
        my $invalids = `$cmd`;
        chomp $invalids;
        my $sambainvalids;
        if ($invalids =~ /invalid users =(.+)/) {
            $invalids = $1;
            my @writers = quotewords('\s+', 1, $invalids);
            my @vals;
            foreach my $writer (@writers) {
                $writer = $2 if ($writer =~ /(\+)?".+\\(.+)"/);
                push(@vals, "$writer") if ($writer);
            }
            $sambainvalids = join(", ", @vals);
        }

        $cmd = qq[cat /etc/samba/smb.conf | grep "hosts allow"];
        my $hallow = `$cmd`;
        chomp $hallow;
        my $sambahostsallow;
        if ($hallow =~ /hosts allow =(.+)/) {
            $hallow = $1;
            my @ahosts = quotewords('\s+', 1, $hallow);
            my @vals;
            foreach my $host (@ahosts) {
                $host = $1 if ($host =~ /([\d\.]+)/);
                push(@vals, "$host") if ($host);
            }
            $sambahostsallow = join(", ", @vals);
        }

        my $form = <<END
<div class="tab-pane" id="samba-provision">
    <form class="passwordform" action="index.cgi?action=changesambadomain\&tab=samba\&show=samba-provision" id="sambaform" method="post" accept-charset="utf-8" onsubmit="provisionSpinner();">
        <small>Host name (e.g. "dc"):</small>
        <input id="sambahost" type="text" name="sambahost" autocomplete="off" value="$sambahost">
        <br />
        <small>Domain name (e.g. "hq.company.int"):</small>
        <input id="sambadomain" type="text" name="sambadomain" autocomplete="off" value="$sambadomain">
        <br />
        <small>Administrator password:</small>
        <input id="sambapwd" name="sambapwd" type="password" name="sambapwd" autocomplete="off" value="" class="password">
        <br />
    </form>
    <div style="width:422px;">
        <button id="provision_button" class="btn btn-default btn-info pull-right" style="margin-top:10px;" type="submit" onclick="confirmSambaAction('#sambaform');">Provision new domain!</button>
    </div>
</div>
<div class="tab-pane" id="samba-config">
    <form class="passwordform" accept-charset="utf-8" id="sambaconfigform">
        <small>Write list (e.g. "administrator, Domain Admins"):</small><br />
        <input type="text" name="sambawritelist" id="sambawritelist" value="$sambawritelist" class="password">
        <button id="changewritelist_button" class="btn btn-default" type="button" onclick="changeWritelist();">Set!</button>
        <span style="float: left; font-size: 13px;">leave empty to allow all users write access to "shared".</span>
        <br style="clear:both;" />
        <small>External users (e.g. "friend1, Domain Guests"):</small><br />
        <input type="text" name="sambainvalids" id="sambainvalids" value="$sambainvalids" class="password">
        <button id="changeinvalids_button" class="btn btn-default" type="button" onclick="changeInvalids();">Set!</button>
        <span style="float: left; font-size: 13px;">these users do not have access to "shared" and have no home-dir.</span>
        <br style="clear:both;" />
        <small>Hosts to allow (e.g. "192.168.1. 195.41.32.80"):</small><br />
        <input type="text" name="sambahostsallow" id="sambahostsallow" value="$sambahostsallow" class="password">
        <button id="changehostsallow_button" class="btn btn-default" type="button" onclick="changeHostsAllow();">Set!</button>
        <span style="float: left; font-size: 13px;">leave empty to allow all SMB/CIFS access from everywhere.</span>
    </form>
    <div style="width:422px; clear:both;">
        <button class="btn btn-default" id="restartsamba_button" style="margin-top:10px;" type="submit" onclick="restartSamba();">Restart Samba</button>
    </div>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $elfinderlink;
        my $suuid;
        my $sservers_ref = list_simplestack_networks();
        my @sservers = @$sservers_ref;
        foreach my $sserv (@sservers) {
            my $sip = $sserv->{internalip};
            my $uuid = $sserv->{uuid};
            if ($sip eq $internalip) {
                $suuid = $uuid;
                $elfinderlink .= qq|openElfinder("$sip", "$uuid")|;
                last;
            }
        }

        my $js = <<END
    function openElfinder(sip, uuid, nfsname) {
        var url = "/stabile/pipe/http://" + uuid + ":10000/stabile/index.cgi?tab=samba&action=elfinder&storageid=" + sip;
        if (nfsname) url += "&nfsname=" + nfsname;
        window.open(url, sip);
        return false;
    }
    \$(document).ready(function () {
        \$('#go_ul').append(
            \$('<li>').append(
                \$('<a>').attr('href','https://$externalip/origo/elfinder/index.cgi').attr('target','_blank').append("to file browser")
        ));
        \$('#go_ul').append(
            \$('<li>').append(
                \$('<a>').attr('href','smb://administrator\@$externalip').append("to SMB file service")
        ));
    });
    function confirmSambaAction(action) {
        \$('#confirmdialog').prop('actionform', action);
        \$('#confirmdialog').modal({'backdrop': false, 'show': true});
        return false;
    };
    function restartSamba() {
        \$("#restartsamba_button").prop("disabled", true ).html('Restart Samba <i class="fa fa-cog fa-spin"></i>');
        \$.get( "index.cgi?action=restart\&tab=samba")
        .done(function( data ) {
            \$("#restartsamba_button").html('Restart Samba').prop( "disabled", false );
        })
    }
    function changeWritelist() {
        \$("#changewritelist_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        \$.post( "index.cgi?action=changewritelist\&tab=samba\&show=samba-config", \$("#sambaconfigform").serialize())
        .done(function( data ) {
            \$("#changewritelist_button").html('Set!').prop( "disabled", false );
            \$("#sambawritelist").val(data.writelist)
        })
    }
    function changeInvalids() {
        \$("#changeinvalids_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        \$.post( "index.cgi?action=changeinvalids\&tab=samba\&show=samba-config", \$("#sambaconfigform").serialize())
        .done(function( data ) {
            \$("#changeinvalids_button").html('Set!').prop( "disabled", false );
            \$("#sambainvalids").val(data.invalids)
        })
    }
    function changeHostsAllow() {
        \$("#changehostsallow_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        \$.post( "index.cgi?action=changehostsallow\&tab=samba\&show=samba-config", \$("#sambaconfigform").serialize())
        .done(function( data ) {
            \$("#changehostsallow_button").html('Set!').prop( "disabled", false );
            \$("#sambahostsallow").val(data.hostsallow)
        })
    }
    function provisionSpinner() {
        \$("#provision_button").prop("disabled", true ).html('Provision new domain! <i class="fa fa-cog fa-spin"></i>');
    }

END
;
        return $js;

    } elsif ($action eq 'restart') {
        my $res = `/etc/init.d/samba4 restart`;
        $res = uri_encode($res),
        return <<END
Content-type: application/json; charset=utf-8

{"result": "$res"}
END
;

    } elsif ($action eq 'tab') {
        return getSambaDropdown();

# This is called from index.cgi (the UI)
    } elsif ($action eq 'upgrade') {
        my $res;
        my $srcloc = "/opt/samba4";
        my $dumploc = $in{targetdir};

        if (-d $dumploc) {
            # Stop Samba server
            `/etc/init.d/samba4 stop`;
            unless (-e "$srcloc/var/run/samba.pid") {
                # Copy Samba configuration
                `rm -r "$dumploc/samba4.tgz"`;
                `(cd /opt; tar -zcf "$dumploc/samba4.tgz" samba4)`;
                `rm -r "$dumploc/etc"`;
                # Also copy /etc/samba
                `cp -r "/etc/samba" "$dumploc/etc-samba"`;
            }
        }

        my $dumpsize = `du -bs $dumploc/samba4.tgz`;
        $dumpsize = $1 if ($dumpsize =~ /(\d+)/);
        if ($dumpsize > 10000000) {
            $res = "OK: Samba data and database dumped successfully to $dumploc";
        } else {
            $res = "There was a problem dumping Samba data to $dumploc ($dumpsize)!";
        }
        return $res;

# This is called from origo-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {
        my $srcloc = $in{sourcedir};
        my $res;
        my $dumploc  = "/opt/samba4/";
        `bash -c "service samba4 stop"`;
        if ($srcloc && -d $srcloc && -d $dumploc && !(-e "$srcloc/var/run/samba.pid")) {
            $res = "OK: ";

            my $srcfile = "samba4.tgz";
            $res .= qq|restoring $srcloc/$srcfile -> $dumploc, |;
            $res .= `bash -c "tar -zcf /tmp/samba4.bak.tgz /opt/samba4"`;
            $res .= `bash -c "mv --backup /tmp/samba4.bak.tgz /opt/samba4.bak.tgz"`;
            $res .= `bash -c "(cd /opt; tar -zxf $srcloc/$srcfile)"`;

            my $srcdir = "etc-samba/*";
            $dumploc  = "/etc/samba/";
            $res .= qq|copying $srcloc/$srcdir -> $dumploc, |;
            $res .= `cp --backup -a $srcloc/$srcdir "$dumploc"`;

            chomp $res;
        }

        if ($res) {
            `service samba4 start`;
        } else {
            $res = "Not copying $srcloc -> $dumploc";
        }
#        `umount /mnt/fuel/*`;
        return $res;

    } elsif ($action eq 'changesambapassword' && defined $in{sambapassword}) {
        my $message;
        my $pwd = $in{sambapassword};
        if ($pwd) {
            my $cmd = qq[samba-tool user setpassword Administrator --newpassword=$pwd];
            my $res =  `$cmd 2>\&1`;
            if ($res =~ /password OK/) {
                $message .=  "<div class=\"message\">The Samba password was changed!</div>";
            } else {
                $message .= "<div class=\"message\">The Samba password was NOT changed! ($res)</div>";
            }
        }
        return $message;

    } elsif ($action eq 'changehostsallow' && defined $in{sambahostsallow}) {
        my $hostsallow = $in{sambahostsallow};
        my $ret_hostsallow;
        if ($in{sambahostsallow}) {
            my @ahosts = quotewords(',\s+', 1, $hostsallow);
            my @vals;
            foreach my $host (@ahosts) {
                $host = $1 if ($host =~ /"(.+)"/);
                if ($host =~ /([\d\.]+)(\/\d+)/) { # Samba does not support 192.68.2.0/24 syntax, only e.g. 192.168.2.
                    $host = $1;
                    $host =~ s/(\.0)+$/\./; # Replace e.g. 10.225.0.0 with 10.225.
                }
                push(@vals, $host) if ($host);
            }
            $hostsallow = join(" ", @vals);
            $ret_hostsallow = join(", ", @vals);
        }
        `perl -ni -e 'print unless (/hosts allow/)' /etc/samba/smb.conf`;
        `perl -pi -e 's/\\[global\\]/[global]\n   hosts allow = $hostsallow/;' /etc/samba/smb.conf` if ($hostsallow);
        my $res = `/etc/init.d/samba4 restart`;
        $res = uri_encode($res),
        return <<END
Content-type: application/json; charset=utf-8

{"result": "OK: $res", "hostsallow": "$ret_hostsallow"}
END
;

    } elsif ($action eq 'changewritelist' && defined $in{sambawritelist}) {
        my $writelist = '';
        my $ret_writelist = '';
        if ($in{sambawritelist}) { # Limit write access to shared
            my @garray = split(/\n/, `samba-tool group list`);
            my %ghash = map { lc $_ => $_ } @garray; # Create hash with all groups
            my @writers = split(/, ?/, $in{sambawritelist});
            my $writel;
            foreach my $writer (@writers) {
                my $plus = '';
                $plus = '+' if ($ghash{lc $writer});
                $writel .= qq|$plus"$sambadomain\\\\$writer" |;
                $ret_writelist .= qq|$writer, |;
            }
            $ret_writelist = substr($ret_writelist, 0, -2) if ($ret_writelist);
            $writelist = <<END

   read only = yes
   write list = $writel
END
;
            chomp $writelist;
        }
        `perl -ni -e 'print unless (/read only/)' /etc/samba/smb.conf`;
        `perl -ni -e 'print unless (/write list/)' /etc/samba/smb.conf`;
        `perl -pi -e 's/\\[shared\\]/[shared]$writelist/;' /etc/samba/smb.conf`;
        my $res = `/etc/init.d/samba4 restart`;
        $res = uri_encode($res),
        return <<END
Content-type: application/json; charset=utf-8

{"result": "OK: $res", "writelist": "$ret_writelist"}
END
;

    } elsif ($action eq 'changeinvalids' && defined $in{sambainvalids}) {
        my $invalids = '';
        my $ret_invalids = '';
        if ($in{sambainvalids}) { # Limit access to shared and home-dirs
            my @garray = split(/\n/, `samba-tool group list`);
            my %ghash = map { lc $_ => $_ } @garray; # Create hash with all groups
            my @writers = split(/, ?/, $in{sambainvalids});
            my $writel;
            foreach my $writer (@writers) {
                my $plus = '';
                $plus = '+' if ($ghash{lc $writer});
                $writel .= qq|$plus"$sambadomain\\\\$writer" |;
                $ret_invalids .= qq|$writer, |;
            }
            $ret_invalids = substr($ret_invalids, 0, -2) if ($ret_invalids);
            $invalids = <<END

   invalid users = $writel
END
;
            chomp $invalids;
        }
        `perl -ni -e 'print unless (/invalid users/)' /etc/samba/smb.conf`; # remove current invalids, if any
        `perl -pi -e 's/\\[shared\\]/[shared]$invalids/;' /etc/samba/smb.conf`;
        `perl -pi -e 's/\\[home\\]/[home]$invalids/;' /etc/samba/smb.conf`;
        my $res = `/etc/init.d/samba4 restart`;
        $res = uri_encode($res),
        return <<END
Content-type: application/json; charset=utf-8

{"result": "OK: $res", "invalids": "$ret_invalids"}
END
;

    } elsif ($action eq 'changesambadomain' && defined $in{sambadomain}) {
        my $message;
        my $newdomain = $in{sambadomain};
        $newdomain =~ s/ /_/;
        my $newhost = $in{sambahost};
        $newhost =~ s/ /_/;
        my $newpwd = $in{sambapwd};
        if ($newpwd && $newdomain && ($newdomain =~ /(\S+)\.\S+\.\S+/ || $newdomain =~ /(\S+)\.\S+/)) {
            `hostname $newhost` if ($newhost && (lc $newhost) ne (lc $sambahost));
            $newhost = $newhost || `hostname`;
            chomp $newhost;
            my $writelist = '';
            my $ret_writelist = '';
            if (defined $in{sambawritelist}) { # Limit write access to shared
                my @garray = split(/\n/, `samba-tool group list`);
                my %ghash = map { lc $_ => $_ } @garray; # Create hash with all groups
                my @writers = split(/, ?/, $in{sambawritelist});
                my $writel;
                foreach my $writer (@writers) {
                    my $plus = '';
                    $plus = '+' if ($ghash{lc $writer});
                    $writel .= qq|$plus"$sambadomain\\\\$writer" |;
                    $ret_writelist .= qq|$writer, |;
                }
                $ret_writelist = substr($ret_writelist, 0, -2) if ($ret_writelist);
                $writelist = <<END

    read only = yes
    write list = $writel
END
;
            }

            my $ndom = $1;
            `mv /etc/samba/smb.conf /etc/samba/smb.conf.bak`;
            my $cmd = qq[samba-tool domain provision --realm=$newdomain --domain=$ndom --adminpass="$newpwd" --dnspass="$newpwd" --server-role=dc --dns-backend=SAMBA_INTERNAL --use-rfc2307 --use-xattrs=yes];
            my $res =  `$cmd 2>\&1`;
            if ($res =~ /ready to use/) {
                `perl -ni -e 'print unless (/dns forwarder/)' /etc/samba/smb.conf`;
                `perl -pi -e 's/\\[netlogon\\]/[netlogon]\n    browseable = No/;' /etc/samba/smb.conf`;
                `perl -pi -e 's/\\[sysvol\\]/[sysvol]\n    browseable = No/;' /etc/samba/smb.conf`;
                `perl -pi -e 's/\\[global\\]/[global]\n   root preexec = \\/bin\\/mkdir -p \\/mnt\\/data\\/users\\/\\%U\n   dns forwarder = $gw\n   log level = 2\n   log file = \\/var\\/log\\/samba\\/samba.log.\%m\n   max log size = 50\n   debug timestamp = yes/' /etc/samba/smb.conf`;
                $cmd = <<END

[home]
    path = /mnt/data/users/%U
    read only = no
    browseable = yes
    hide dot files = yes
    hide unreadable = yes
    valid users = %U
    create mode = 0660
    directory mode = 0770
    inherit acls = Yes
    veto files = /aquota.user/lost+found/

[shared]
    path = /mnt/data/shared
    read only = no
    browseable = yes
    hide dot files = yes
    hide unreadable = yes
    create mode = 0660
    directory mode = 0770
    inherit acls = Yes

include = /etc/samba/smb.conf.groups
END
;
                `echo "$cmd" >> /etc/samba/smb.conf`;
                `perl -pi -e 's/\\[shared\\]/[shared]$writelist/;' /etc/samba/smb.conf`;
                `service samba4 restart`;
                $message .=  "<div class=\"message\">The Samba domain was provisioned!</div>";
            } else {
                $message .= "<div class=\"message\">An error occurred! ($res)</div>";
            }
        } else {
            $message .= "<div class=\"message\">You must provide a valid domain name and password!</div>";
        }
        return $message;

    } elsif ($action eq 'elfinder') {
        my $url = 'php/connector.cgi';
        my $title = "Shared files on $in{storageid}";
        if ($in{nfsname}) {
            $url .= "?nfs=$in{storageid}";
            $title = "Browse files on $in{nfsname} ($in{storageid})";
        }
        my $elfinder = <<END
Content-type: text/html

<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>$title</title>
        <link rel="stylesheet" type="text/css" href="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.23/themes/smoothness/jquery-ui.css">
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.8.0/jquery.min.js"></script>
        <script src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.23/jquery-ui.min.js"></script>
        <link rel="stylesheet" type="text/css" href="css/elfinder.full.css">
        <link rel="stylesheet" type="text/css" href="css/theme.css">
        <script src="js/elfinder.full.js"></script>
        <script type="text/javascript" charset="utf-8">
            // Documentation for client options:
            // https://github.com/Studio-42/elFinder/wiki/Client-configuration-options
            \$(document).ready(function() {
                \$('#elfinder').elfinder({
                    url : "$url",  // connector URL (REQUIRED)
                    height: '600'
                });
            });
        </script>
    </head>
    <body>
        <div id="elfinder"></div>
    </body>
</html>
END
;
        return $elfinder;
    } elsif ($action eq 'smbmount') {
        my $hostname = $in{hostname};
        my $cookie = $ENV{HTTP_COOKIE};
        my $path = $in{path};
        my $tkt;

        $path = $2 if ($path =~ /(groups\/)(.+)/);
        $tkt = $1 if ($cookie =~ /auth_tkt=(\S+)\%/);
        my $tktuser = `/usr/local/bin/ticketmaster.pl $tkt`;
        chomp $tktuser;
        $path = $1 if ($path =~ /(.+)\/$/);
        $path = "home" if ($path =~ /users\//);
        my $res = <<END
Content-type: text/html

smb://$tktuser\@$hostname/$path
END
;
        return $res;
    }
}

sub getSambaDropdown {
    my $dropdown = <<END
        <li class="dropdown">
            <a href="#" id="myTabDrop1" class="dropdown-toggle" data-toggle="dropdown">samba <b class="caret"></b></a>
            <span class="dropdown-arrow"></span>
            <ul class="dropdown-menu" role="menu" aria-labelledby="myTabDrop1">
                <li><a href="#samba-provision" tabindex="-1" data-toggle="tab">Provision domain</a></li>
                <li><a href="#samba-config" tabindex="-1" data-toggle="tab">Samba configuration</a></li>
            </ul>
        </li>
END
;
    return $dropdown;

}

1;

