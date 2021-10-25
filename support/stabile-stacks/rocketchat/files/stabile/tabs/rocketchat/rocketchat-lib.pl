#!/usr/bin/perl

use JSON;
use Digest::SHA qw(sha1_base64 sha1_hex);
use Digest::MD5 qw(md5 md5_hex md5_base64);

my $dnsdomain =  $appinfo{dnsdomain};
my $dnssubdomain = $appinfo{'dnssubdomain'};
my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":"$externalip";

sub rocketchat {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form' || $action eq 'rocketform') {
        my $form;

        # Redirect to upgrade page if still upgrading
        if (-e "/tmp/restoring") {
            $form .=  qq|<script>loc=document.location.href; setTimeout(function(){document.location=loc;}, 1500); </script>|;
        }
        my $startcount = `journalctl -u rocketchat | grep RUNNING | wc -l`;
        chomp $startcount;
        my $runcount = 0;
        if (-e "/tmp/runcount") {
            my $runcountage = `echo \$(( \`date +\%s\` - \`stat -L --format \%Y /tmp/runcount\` ))`; # file age in seconds
            chomp $runcountage;
            if ($runcountage < 4 * 3600) { # 4 hours
                $runcount = `cat /tmp/runcount`;
                chomp $runcount; $runcount = $runcount + 0;
            } else {
                $runcount = -1; # If server has been running for many hours, unit log may have been rotated, so assume things are running
            }
        }

        if ($startcount <= $runcount) {
            my $status = `journalctl -u rocketchat | tail -n 15`;
            $form .= <<END
    <script>
        setTimeout(function() {
            \$.get("index.cgi?action=rocketform&tab=rocketchat", function(result) {
                \$("#rocket").html(result);
            });
        }, 3000);
    </script>
    <div class="tab-pane container" id="rocket">
        <table><tr><td>
            <div class="sk-wave">
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
            </div>
        </td><td>
            <h5 style="margin-left: 20px;">Preparing RocketChat - this may take a few minutes...</h5>
        </td><tr></table>
        <pre>$status
        </pre>
    </div>
END
        } else {
            $form .= <<END
        <form class="passwordform" id="rocketchatpassword_form" action="index.cgi?action=changerocketchatpassword&tab=rocketchat" method="post" onsubmit="limitRocketSpinner('rocketchatpassword'); \$('#rocketchatpassword').val(''); return false;" accept-charset="utf-8" autocomplete="off">
            <div>
                Here you can manage basic security for your RocketChat installation.
            </div>
            <small>Set the password for the RocketChat user "stabile":</small>
            <div class="row">
                <div class="col-sm-10">
                    <input type="password" id="rocketchatpassword" name="rocketchatpassword" autocomplete="off" value="" class="password kubebutton">
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default kubebutton" type="submit" id="rocketchatpassword_button">Set!</button>
                </div>
            </div>
        </form>
        <small style="margin-top:10px;">
            After setting the password, <a target="_blank" href="http://$dom">log in here</a> as user "stabile" with your password.
        </small>
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
    <div class="tab-pane container" id="rocketchat">
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
        \$("#currentwp").text("to RocketChat");

    function limitRocketSpinner(target) {
        if (!target) target = "rocketchatpassword";
        \$("#" + target + "_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        var ser = \$('#' + target + '_form').serialize();
        \$(".kubebutton").prop("disabled", true );
        \$.post('index.cgi?action=' + target + '&tab=rocketchat', ser, function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".kubebutton").prop("disabled", false );

            setTimeout(function() {
                \$.get("index.cgi?action=rocketform&tab=rocketchat", function(result) {
                    \$("#rocket").html(result);
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
    linkElement.href = "tabs/rocketchat/spinkit.css";
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

    } elsif ($action eq 'rocketchatpassword' && defined $in{rocketchatpassword}) {
        my $message;
        my $pwd = $in{rocketchatpassword};
        if ($pwd) {
            my $password = `htpasswd -bnBC 10 "" \$(echo -n "$pwd" | sha256sum | cut -d " " -f 1) | tr -d ':\n' | sed 's/\$2y/\$2a/'`;
            # my $password = `bcrypt-cli \$(echo -n "$pwd" | sha256sum | cut -d " " -f 1) 10`;
            chomp $password;
            $message = `echo 'db.getCollection("users").update({username:"stabile"}, { \$set: {"services" : { "password" : {"bcrypt" : "$password"}}}})' | mongo rocketchat`;
            if ($message =~ /"nMatched" ?: ?1/) {
                $message = "The Rocket.Chat password was changed!";
            } else { # stabile user has not yet logged in - change the systemd unit
                $message .= `perl -pi -e 's/ADMIN_PASS=.*/ADMIN_PASS=$pwd/;' /lib/systemd/system/rocketchat.service`;
                `systemctl daemon-reload`;
                `systemctl restart rocketchat`;
                $message = "The (initial) Rocket.Chat password was changed - please wait for service restart!";
                my $startcount = `journalctl -u rocketchat | grep RUNNING | wc -l`;
                chomp $startcount;
                `echo $startcount > /tmp/runcount`;
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;
    }
}


1;
