#!/usr/bin/perl

use JSON;
use Digest::SHA qw(sha1_base64 sha1_hex);
use Digest::MD5 qw(md5 md5_hex md5_base64);

sub mongodb {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
        my $dnsdomain_json = `curl -k https://$gw/stabile/networks?action=getdnsdomain`;
        my $dom_obj = from_json ($dnsdomain_json);
        my $dnsdomain =  $dom_obj->{'domain'};
        my $dnssubdomain = $dom_obj->{'subdomain'};
        $dnsdomain = '' unless ($dnsdomain =~  /\S+\.\S+$/ || $dnsdomain =~  /\S+\.\S+\.\S+$/);
        my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":$externalip;

        my $allow = `cat /etc/apache2/sites-available/default-ssl.conf`;
        my $mongodblimit = $1 if ($allow =~ /allow from (.+)/);
        my $curip = qq|<div style="font-size: 13px;">leave empty to disallow all access, your current IP is <a style="text-decoration: none;" href="#" onclick="\$('#limitmongodb').val('$ENV{HTTP_X_FORWARDED_FOR} ' + \$('#limitmongodb').val());">$ENV{HTTP_X_FORWARDED_FOR}</a></div>| if ($ENV{HTTP_X_FORWARDED_FOR});

        if (-s "/var/www/html/config.php") {
            ;
        } else {
            ;# "Already patched\n";
        }
        my $form;
        # Redirect to upgrade page if still upgrading
        if (-e "/tmp/restoring") {
            $form .=  qq|<script>loc=document.location.href; setTimeout(function(){document.location=loc;}, 1500); </script>|;
        }
        $form .= <<END
    <div class="tab-pane container" id="mongodb">
        <div>
            Here you can manage basic security for the Mongodb Web UI
        </div>
		<form class="passwordform" id="limitmongodb_form" action="index.cgi?action=limitmongodb&tab=mongodb" method="post" onsubmit="limitMongodbSpinner(); return false;" accept-charset="utf-8">
			<div class="small">Allow access to MongoDB on port 27017 and MongoDB Web UI from:</div>
			<div class="row">
				<div class="col-sm-10">
					<input id="limitmongodb" type="text" name="limitmongodb" value="$mongodblimit" placeholder="IP address or network, e.g. '192.168.0.0/24 127.0.0.1'">
					$curip
				</div>
				<div class="col-sm-2">
					<button class="btn btn-default" type="submit" id="limitmongodb_button">Set!</button>
				</div>
			</div>
		</form>
        <form class="passwordform" id="mongodbpassword_form" action="index.cgi?action=mongodbpassword&tab=mongodb" method="post" onsubmit="limitMongodbSpinner('mongodbpassword'); \$('#mongodbpassword').val(''); return false;" accept-charset="utf-8" id="linform" autocomplete="off">
            <div class="small">Set password for user "stabile" in dashboard and MongoDB:</div>
            <div class="row">
                <div class="col-sm-10">
                    <input id="mongodbpassword" type="password" name="mongodbpassword" autocomplete="off" value="" class="password">
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default" type="submit" id="mongodbpassword_button">Set!</button>
                </div>
            </div>
        </form>
        <div class="small">
            After allowing access from your IP address, you can access the <a target="_blank" href="https://$dom/">MongoDB Web UI</a> with username 'stabile'. To access your sharded MongoDB server, simply type 'localhost' as 'host', and hit 'Login'.
        </div>
    </div>
END
        ;

        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $dnsdomain_json = `curl -k https://$gw/stabile/networks?action=getdnsdomain`;
        my $dom_obj = from_json ($dnsdomain_json);
        my $dnsdomain =  $dom_obj->{'domain'};
        my $dnssubdomain = $dom_obj->{'subdomain'};
        $dnsdomain = '' unless ($dnsdomain =~  /\S+\.\S+$/ || $dnsdomain =~  /\S+\.\S+\.\S+$/);
        my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":$externalip;

        my $js = <<END

    \$("#currentwp").attr("href", "https://$dom/");
    \$("#currentwp").text("to Mongodb Web UI");

    function limitMongodbSpinner(target) {
        if (!target) target = "limitmongodb";
        \$("#" + target + "_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        \$(".mongodbbutton").prop("disabled", true );
        \$.post('index.cgi?action=' + target + '&tab=mongodb', \$('form#' + target + '_form').serialize(), function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".mongodbbutton").prop("disabled", false );
        }).fail(function() {
            salert( "An error occurred :(" );
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".mongodbbutton").prop("disabled", false );
        });
    }

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

    } elsif ($action eq 'limitmongodb') {
        my $message = "Please supply a limit!";
        if (defined $in{limitmongodb}) {
            my $limit = $in{limitmongodb};
            my ($validlimit, $mess) = validate_limit($limit);
            my $conf = "/etc/apache2/sites-available/default-ssl.conf";
            if ($validlimit) {
                if (`grep 'allow from' /etc/apache2/sites-available/default-ssl.conf`)
                {
                    $message =  "MongoDB dashboard access was changed!";
                    $message .= `perl -pi -e 's/allow from (.*)/allow from $validlimit/;' $conf`;

                    my $opfile = "/etc/iptables/rules.v4";
                    open(FILE, "<$opfile") or {throw Error::Simple("Unable to open $opfile")};
                    my @lines = <FILE>;
                    close FILE;
                    my @newlines;
                    foreach my $line (@lines) {
                        chomp $line;
                        push @newlines, $line unless ($line =~ /^-A INPUT.*27017/ || $line =~ /^-A INPUT.*4200/ || $line =~ /COMMIT/);
                    }
                    foreach my $lim (split(" ", $validlimit)) {
                        $lim =~ s/\\//;
                        push @newlines, "-A INPUT -s $lim -p tcp -m tcp --dport 27017 -j ACCEPT";
                    }
                    push @newlines, "-A INPUT -s 0.0.0.0/0 -p tcp -m tcp --dport 27017 -j DROP";
                    push @newlines, "-A INPUT -s $gw -p tcp -m tcp --dport 4200 -j ACCEPT";
                    push @newlines, "-A INPUT -s 0.0.0.0/0 -p tcp -m tcp --dport 4200 -j DROP";
                    push @newlines, "COMMIT";
                    open(FILE, ">$opfile") or {throw Error::Simple("Unable to open $opfile")};
                    print FILE join("\n", @newlines);
                    print FILE "\n";
                    close FILE;
                    `iptables-restore /etc/iptables/rules.v4`;
                } else {
                    $message =  "Unable to process default-ssl.conf!";
                }
                `systemctl reload apache2`;
            } else {
                $message =  $mess;
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;

    } elsif ($action eq 'mongodbpassword') {
        my $message = "Please supply a password!";
        if (defined $in{mongodbpassword} && $in{mongodbpassword} =~ /^\S+$/) {
            my $pwd = $in{mongodbpassword};
            my $oldpwd = `cat /etc/mongod.pass`;
            chomp $oldpwd;
            my $conf = "/etc/apache2/mongodbpasswords";
            if ($pwd) {
                my $res = `echo "db.getSiblingDB('admin').updateUser('stabile',{pwd:'$pwd'})" | mongo -u "stabile" -p "$oldpwd"  --authenticationDatabase "admin"`;
                unless (system(qq|htpasswd -b $conf stabile $pwd|) || $res =~ /exception/) {
                    `echo "$pwd" > /etc/mongod.pass`;
                    `echo "$pwd" > /usr/share/webmin/stabile/tabs/mongodb/mongod.pass`;
                    $message =  "MongoDB dashboard password was changed!";
                } else {
                    $message =  "Unable to change password! $res";
                }
            } else {
                $message =  "Please supply a password";
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;
    }
}


1;
