#!/usr/bin/perl

sub security {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
# Generate and return the HTML form for this tab

        my $allow = `cat /etc/hosts.allow`;
        my $limitssh;
        $limitssh = $1 if ($allow =~ /sshd: ?(.*) #stabile/);

        my $pwform = <<END
    <div class="tab-pane active container" id="security">
    <div>
        Here you can manage basic security settings for the servers in your stack.
    </div>
    <form class="passwordform" id="passwordform" action="index.cgi?action=changelinuxpassword&tab=security" method="post" onsubmit="passwordSpinner(); return false;" accept-charset="utf-8" id="linform" autocomplete="off">
    	<div class="small">Set password for Linux user "stabile":</div>
	    <div class="row">
    	    <div class="col-sm-10">
        	    <input id="linuxpassword" type="password" name="linuxpassword" autocomplete="off" value="" class="password">
   	     	</div>
    	    <div class="col-sm-2">
            	<button class="btn btn-default" type="submit" id="password_button">Set!</button>
        	</div>
    	</div>
    </form>
END
;

        my $curip;
        $curip = qq|<div style="font-size: 13px;">leave empty to disallow all access, your current IP is <a style="text-decoration: none;" href="#" onclick="\$('#limitssh').val('$ENV{HTTP_X_FORWARDED_FOR} ' + \$('#limitssh').val());">$ENV{HTTP_X_FORWARDED_FOR}</a></div>| if ($ENV{HTTP_X_FORWARDED_FOR});

        my $curipwp;
        my $dispextip = $externalip || '--';
        my $dispintip = $internalip || '--';
        $curipwp = qq|<div style="font-size: 13px;">leave empty to allow login from anywhere, your current IP is <a href="#" onclick="\$('#wplimit').val('$ENV{HTTP_X_FORWARDED_FOR} ' + \$('#wplimit').val());">$ENV{HTTP_X_FORWARDED_FOR}</a></div>| if ($ENV{HTTP_X_FORWARDED_FOR});

        my $limitform = <<END
    <form class="passwordform" id="limitsshform" action="index.cgi?action=limitssh&tab=security" method="post" onsubmit="limitSpinner(); return false;" accept-charset="utf-8">
	    <div class="small">Allow <a href="ssh://stabile\@$externalip">ssh</a> and <a href="https://$externalip:10001" target="_blank">webmin</a> login from:</div>
	    <div class="row">
 	       <div class="col-sm-10">
	            <input id="limitssh" type="text" name="limitssh" value="$limitssh" placeholder="IP address or network, e.g. '192.168.0.0/24 127.0.0.1'">
	 	       $curip
 	       </div>
  			<div class="col-sm-2">
   		     	<button class="btn btn-default" type="submit" id="limit_button">Set!</button>
            </div>
        </div>
        <div class="small well" style="margin-top:30px; padding:8px;">The internal IP of this server is: $dispintip, the external IP is $dispextip.</div>
    </form>
    </div>
END
;
        return "$pwform\n$limitform";

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
    \$(document).ready(function () {
        \$('#linuxpassword').strength({
            strengthClass: 'strength',
            strengthMeterClass: 'strength_meter',
            strengthButtonClass: 'button_strength',
            strengthButtonText: 'Show Password',
            strengthButtonTextToggle: 'Hide Password'
        });
        \$('#linuxpassword').val('');
    });

    function doStrength(item) {
        console.log("Strengthening", item);
        \$(item).strength({
            strengthClass: 'strength',
            strengthMeterClass: 'strength_meter',
            strengthButtonClass: 'button_strength',
            strengthButtonText: 'Show Password',
            strengthButtonTextToggle: 'Hide Password',
            id: item.id
        });
        \$(item).val('');
    };

    function passwordSpinner() {
        \$("#password_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        \$.post('index.cgi?action=changelinuxpassword&tab=security', \$('form#passwordform').serialize(), function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#linuxpassword").val('').blur();
            \$(".strength_meter > div").removeClass()
            \$("#password_button").prop("disabled", false ).html('Set!');
        }).fail(function() {
            salert( "An error occurred :(" );
        });
    }
    function limitSpinner(button_id) {
        \$("#limit_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        \$.post('index.cgi?action=limitssh&tab=security', \$('form#limitsshform').serialize(), function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#limit_button").prop("disabled", false ).html('Set!');
        }).fail(function() {
            salert( "An error occurred :(" );
        });
    }

END
;
        return $js;

# This is called from the UI
    } elsif ($action eq 'upgrade') {
        my $res;
        my $json_text = `curl -ks "https://$gw/stabile/servers/this"`;
        my $rdom = from_json($json_text);
        my $uuid = $rdom->{uuid};
        my $dumploc;
        my %activepools = mountPools();
        foreach my $pool (values %activepools) {
            my $sid = "pool" . $pool->{id};
            if ($mounts =~ /\mnt\/fuel\/$sid/) { # pool mounted
                $dumploc = "/mnt/fuel/$sid/upgradedata/$uuid";
                `mkdir -p $dumploc`;
                last;
            }
        }
        if (-d $dumploc) {
            # Dump limit
            my $limit = get_limit();
            `echo "$limit" > $dumploc/security.limit`;
            if (-e "$dumploc/security.limit") {
                $res = "OK: Security data dumped successfully to $dumploc";
            } else {
                $res = "There was a problem dumping security data to $dumploc!";
            }
        } else {
            $res = "There was a problem dumping limit $limit to $dumploc!";
        }
        return $res;

# This is called from stabile-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {
        my $srcloc = $in{sourcedir};
        my $res;
        if (-e "$srcloc/security.limit") {
            my $limit;
            $limit = `cat $srcloc/security.limit`;
            chomp $limit;
            $res = "OK: ";
            $res .= set_limit($limit);
        }
        $res = "Unable to restore security settings from $srcloc/security.limit!" unless ($res);
        return $res;

    } elsif ($action eq 'changelinuxpassword' && defined $in{linuxpassword}) {
        my $message;
        my $pwd = $in{linuxpassword};
        if ($pwd) {
            my $cmd = qq[echo "stabile:$pwd" | chpasswd];
            $message .=  `$cmd`;
            # Also configure other servers in app
            my $rstatus = run_command($cmd, $internalip) if (defined &run_command);
            $message .= $rstatus unless ($rstatus =~ /OK:/);
            # Also allow Webmin to execute calls on remote servers
         #   `perl -pi -e 's/pass=.*/pass=$in{linuxpassword}/' /etc/webmin/servers/*.serv`; # We now use separate Webmin password
         #   $message .=  "<div class=\"message\">The Linux password was changed!</div>";
            $message .= "The Linux password was changed!";
        } else {
            $message = "Please supply a password!";
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;

    } elsif ($action eq 'limitssh' && defined $in{limitssh}) {
        my $limit = $in{limitssh};
        return set_limit($limit);
    }
}

## Validates a string of ipv4 addresses and networks
sub validate_limit {
    my $limit = shift;
    my $mess;
    my @limits = split(/ +/, $limit);
    my @validlimits;
    my @sshlimits;
    foreach my $lim (@limits) {
        # Check if valid ipv4 address or network
        my $ip = $lim;
        my $net;
        if ($lim =~ /(\S+)\/(\S+)/) {
            $ip = $1;
            $net = $2;
            $lim = "$1\\/$2";
            $ip = '' unless ($net =~ /^\d\d?$/);
        }
        if (!(defined &check_ipaddress) || check_ipaddress($ip)) {
            push @validlimits, $lim;
            push @sshlimits, '*' . "\\@" . $lim;
        } else {
            $mess .=  "<div class=\"message\">Invalid IP address or network!</div>";
        }
    };
    my $validlimit = join(' ', @validlimits);
    my $sshlimit = join(' ', @sshlimits);
    return ($validlimit, $sshlimit, $mess);
}

sub get_limit {
    my $limit;
    my $conf = "/etc/apache2/sites-available/webmin-ssl";
    # Handle name change in Xenial
    $conf .= '.conf' if (-e "$conf.conf");

    open FILE, "<$conf";
    my @lines = <FILE>;
    for (@lines) {
        if ($_ =~ /allow from (.*)/) {
            $limit = $1;
            last;
        }
    }
    close(FILE);
    return $limit;
}

sub set_limit {
    my $limit = shift;
    my $message;
    my ($validlimit, $sshlimit, $mess) = validate_limit($limit);
    $message .= $mess;
    my $iip = "$1.0" if ($internalip =~ /(\d+\.\d+\.\d+)\.\d+/);
    my $cmd;
    # Configure webmin on admin server
    $cmd = qq|perl -pi -e "s/allow=(.*)/allow=$iip\\/24 127.0.0.1 $validlimit/;" /etc/webmin/miniserv.conf|;
    $message .= `$cmd`;
    my $conf = "/etc/apache2/sites-available/webmin-ssl";
    # Handle name change in Xenial
    $conf .= '.conf' if (-e "$conf.conf");
    $cmd = qq|perl -pi -e 's/allow from (.*)/allow from $validlimit/;' $conf|;
    $message .= `$cmd`;
    `systemctl reload apache2`;
    # Configure ssh on admin server
    $cmd = qq|perl -pi -e 's/sshd: ?(.*) \#stabile/sshd: $validlimit #stabile/;' /etc/hosts.allow|;
    $message .= `$cmd`;
    $cmd = qq|perl -pi -e 's/AllowUsers ?(.*) \#stabile/AllowUsers $sshlimit #stabile/;' /etc/ssh/sshd_config|;
    $message .= `$cmd`;
    `systemctl restart sshd`;
    # Also configure ssh on other servers in app
    my $rstatus = run_command($cmd, $internalip) if (defined &run_command);
    $message .= $rstatus unless ($rstatus =~ /OK:/);
    # Verify a bit
    my $allow = `cat /etc/hosts.allow`;
    if ($allow=~ /sshd: ?(.*) #stabile/)
    {
        $limitssh = $1;
        if ($limitssh) {
            $message .=  "SSH and Webmin can be accessed from $limitssh!";
        } else {
            $message .=  "SSH and Webmin access removed!";
        }
    } else {
        $message .=  "<div class=\"message\">SSH has been manually configured - trying to reconfigure</div>";
        $validlimit =~ s/\\//g;
        `echo "allow=$iip/24 127.0.0.1 $validlimit" >> /etc/webmin/miniserv.conf` unless (`grep "allow=" /etc/webmin/miniserv.conf`);
        `echo "sshd: ALL" >> /etc/hosts.deny` unless (`grep "sshd: ALL" /etc/hosts.deny`);
        `echo "sshd: $validlimit #stabile" >> /etc/hosts.allow` unless (`grep "sshd: .*stabile" /etc/hosts.allow`);
        `echo "AllowUsers $sshlimit #stabile" >> /etc/ssh/sshd_config` unless (`grep "AllowUsers .*stabile" /etc/sshd_config`);
        $limitssh = $1 if (`cat /etc/hosts.allow` =~ /sshd: ?(.*) #stabile/);
    }
    # Reload Webmin
    if (defined (&reload_miniserv)) {
        reload_miniserv();
    } else {
        `systemctl reload webmin`;
    }
    # Reload apache
    $cmd = qq|systemctl apache2 reload|;
    `$cmd`;
    # Also reload on other servers
    run_command($cmd, $internalip) if (defined &run_command);
    chomp $message;
    return qq|Content-type: application/json\n\n{"message": "$message"}|;
}

1;
