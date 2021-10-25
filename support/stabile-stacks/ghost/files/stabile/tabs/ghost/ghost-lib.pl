#!/usr/bin/perl

use JSON;
use Digest::SHA qw(sha1_base64 sha1_hex);
use Digest::MD5 qw(md5 md5_hex md5_base64);

my $dnsdomain =  $appinfo{dnsdomain};
my $dnssubdomain = $appinfo{'dnssubdomain'};
my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":"$externalip";


sub ghost {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    my $email = `echo "select email as '' from users where id = '1';" | mysql ghost`;
    $email =~ s/\n//g;
    chomp $email;
    my $meref = show_me();
    my $memail = $meref->{email};
    $memail = $meref->{username}  if (!$memail || $memail eq '--' || !($memail =~ /\w+\@\w+/));
    if ($email && $email =~ /ghost\@example\.com/) { # If Ghost ready and email has not been updated, update
        $res = `echo "UPDATE users set email='$memail' where id='1';" | mysql ghost 2>&1`;
        $email = $memail;
    } elsif (!$email) { # If Ghost is still not ready fall back to own email
        $email = $memail;
    }
    my $ghostaliases = `cat /root/.getssl/$dom/getssl.cfg | grep SANS=`;
    if ($ghostaliases =~ /SANS="(.+)"/) {
        $ghostaliases = $1;
        $ghostaliases = join(' ', split(/, ?/, $ghostaliases));
    } else {
        $ghostaliases = '';
    }
    my $res;

    if ($action eq 'form' || $action eq 'ghostform') {
        my $form;
        my $running = `systemctl is-active stabile-ghost`;
        chomp $running;
        $running = 1 unless ($running =~ /inactive/);
        unless ($running && $email) {
            my $status = `tail -n 15 /tmp/ghost.log`;
            $form .= <<END
    <script>
        setTimeout(function() {
            \$.get("index.cgi?action=ghostform&tab=ghost", function(result) {
                \$("#ghost").html(result);
            });
        }, 3000);
    </script>
    <div class="tab-pane container" id="ghost">
        <table><tr><td>
            <div class="sk-wave">
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
            </div>
        </td><td>
            <h5 style="margin-left: 20px;">Preparing Ghost - this may take a few minutes...</h5>
        </td><tr></table>
        <pre>$status
        </pre>
    </div>
END
        } else {
            $form .= <<END
        <form class="passwordform" id="ghostpassword_form" action="index.cgi?action=changeghostpassword&tab=ghost" method="post" onsubmit="limitGhostSpinner('ghostpassword'); \$('#ghostpassword').val(''); return false;" accept-charset="utf-8" autocomplete="off">
            <div>
                Here you can manage some basic settings for your ghost installation.
            </div>
            <small>Set the password for the ghost user "$email":</small>
            <div class="row">
                <div class="col-sm-10">
                    <input type="password" id="ghostpassword" name="ghostpassword" autocomplete="off" value="" class="password kubebutton">
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default kubebutton" type="submit" id="ghostpassword_button">Set!</button>
                </div>
            </div>
        </form>
        <small style="margin-top:10px;">
            After setting the password, <a target="_blank" href="https://$dom/ghost">log in here</a> as user "$email" with your password.
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
    <div class="tab-pane container" id="ghost">
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
        \$("#currentwp").text("to ghost");

    function limitGhostSpinner(target) {
        if (!target) target = "ghostpassword";
        \$("#" + target + "_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        var ser = \$('#' + target + '_form').serialize();
        \$(".kubebutton").prop("disabled", true );
        \$.post('index.cgi?action=' + target + '&tab=ghost', ser, function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".kubebutton").prop("disabled", false );

            setTimeout(function() {
                \$.get("index.cgi?action=ghostform&tab=ghost", function(result) {
                    \$("#ghost").html(result);
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
    linkElement.href = "tabs/ghost/spinkit.css";
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

    } elsif ($action eq 'ghostpassword' && defined $in{ghostpassword}) {
        my $message;
        my $pwd = $in{ghostpassword};
        if ($pwd) {
            $message = `echo "UPDATE users SET status='active' WHERE id = '1';" | mysql ghost`;
            my $password = `htpasswd -bnBC 10 "" '$pwd' | tr -d ':\n'`;
            chomp $password;
            $password =~ s/\$/\\\$/g;
            $message = `echo "UPDATE users SET password='$password' WHERE id = '1';" | mysql -vv ghost`;
            if ($message =~ /Rows matched ?: ?1/) {
                $message = "The Ghost password was changed!";
            } else {
                $message =~ s/\n/ /g;
                $message = "There was a problem setting the password: $message";
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;
    }
}

1;
