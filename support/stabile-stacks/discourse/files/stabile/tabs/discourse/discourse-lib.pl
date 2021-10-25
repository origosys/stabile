#!/usr/bin/perl

use JSON;

my $dnsdomain =  $appinfo{dnsdomain};
my $dnssubdomain = $appinfo{'dnssubdomain'};
my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":"$externalip";

sub discourse {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form' || $action eq 'discourseform') {
        my $form;
        my $meref = show_me();
        my $email = $meref->{email};
        $email = $meref->{username} if (!$email || $email eq '--' || !($email =~ /\w+\@\w+/));
        # Redirect to upgrade page if still upgrading
        if (-e "/tmp/restoring") {
            $form .=  qq|<script>loc=document.location.href; setTimeout(function(){document.location=loc;}, 1500); </script>|;
        }

        my $running = (-e "/etc/discourse.seeded");
        unless ($running && $email) {
            my $status = `tail -n 15 /tmp/discourse.out`;
            $form .= <<END
    <script>
        setTimeout(function() {
            \$.get("index.cgi?action=discourseform&tab=discourse", function(result) {
                \$("#discourse").html(result);
            });
        }, 3000);
    </script>
    <div class="tab-pane container" id="discourse">
        <table><tr><td>
            <div class="sk-wave">
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
            </div>
        </td><td>
            <h5 style="margin-left: 20px;">Preparing Discourse - this may take up to 20 minutes...</h5>
        </td><tr></table>
        <pre>$status
        </pre>
    </div>
END
        } else {
            $form .= <<END
    <div class="tab-pane container" id="discourse">
        <div>
            Here you can manage basic security for Discourse.
        </div>
        <small>Set password for Discourse user "$email":</small>
        <form class="passwordform" action="index.cgi?action=discoursepassword&tab=discourse" method="post" onsubmit="discourseSpinner(); return false;" accept-charset="utf-8" id="discoursepassword_form" autocomplete="off">
            <div class="row">
                <div class="col-sm-10">
                    <input type="password" name="discoursepassword" id="discoursepassword" autocomplete="off" value="" class="password">
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default" type="submit" id="discoursepassword_button">Set!</button>
                </div>
            </div>
        </form>
        <small style="margin-top:10px;">
            After setting the password you can <a target="_blank" href="https://$dom">log in here</a> with username "$email" and your password.
        </small>
    </div>
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
    <div class="tab-pane container" id="discourse">
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
        \$("#currentwp").text("to Discourse");
        \$("#currentwp").parent().show()

    function discourseSpinner(target) {
        if (!target) target = "discoursepassword";
        \$("#" + target + "_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        var ser = \$('#' + target + '_form').serialize();
        \$("#" + target).prop("disabled", true );
        \$.post('index.cgi?action=' + target + '&tab=discourse', ser, function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#" + target).val('').prop("disabled", false );
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
        }).fail(function() {
            salert( "An error occurred :(" );
            \$("#" + target).prop("disabled", false );
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
        });
    }

    var linkElement = document.createElement("link");
    linkElement.rel = "stylesheet";
    linkElement.href = "tabs/discourse/spinkit.css";
    document.head.appendChild(linkElement);
END
        ;
        return $js;


        # This is called from index.cgi (the UI)
    } elsif ($action eq 'upgrade') {
        my $res;
        return $res;

        # This is called from origo-ubuntu.pl when rebooting and with status "upgrading"
    } elsif ($action eq 'restore') {
        my $res;
        return $res;

    } elsif ($action eq 'discoursepassword' && defined $in{discoursepassword}) {
        my $message;
        my $meref = show_me();
        my $email = $meref->{email};
        $email = $meref->{username} if (!$email || $email eq '--' || !($email =~ /\w+\@\w+/));
        my $pwd = $in{discoursepassword};
        if ($pwd) {
            my $res = `cd /var/discourse ; export RAILS_ENV=production; printf "$email\nY\n$pwd\n$pwd\nY " | rake admin:create`;
            if ($res =~ /error/i || $res =~ /invalid/i) {
                $message .= $res;
                $message =~ s/\n/ /g;
                $message = $1 if ($message =~ /Repeat password:(.+)Email:  Password/);
            } else {
                $message .= "The Discourse password was changed for $email!";
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;
    }
}


1;
