#!/usr/bin/perl

use JSON;
use Digest::SHA qw(sha1_base64 sha1_hex);
use Digest::MD5 qw(md5 md5_hex md5_base64);
use Data::Password qw(IsBadPassword);
$Data::Password::MINLEN = 8;
$Data::Password::MAXLEN = 128;

my $dnsdomain =  $appinfo{dnsdomain};
my $dnssubdomain = $appinfo{'dnssubdomain'};
my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":"$externalip";


sub minio {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    my $meref = show_me();
    my $email = $meref->{email};
    $email = $meref->{username}  if (!$email || $email eq '--' || !($email =~ /\w+\@\w+/));

    if ($action eq 'form' || $action eq 'minioform') {
        my $form;
        my $running = `systemctl is-active stabile-minio`;
        chomp $running;
        $running = 1 unless ($running =~ /inactive/);

        my $allow = `cat /etc/apache2/conf-available/minio.conf`;
        my $miniolimit = $1 if ($allow =~ /Require ip (.+)/);
        my $curip = qq|<div style="font-size: 13px;">leave empty to allow access from anywhere, your current IP is <a style="text-decoration: none;" href="#" onclick="\$('#limitminio').val('$ENV{HTTP_X_FORWARDED_FOR} ' + \$('#limitminio').val());">$ENV{HTTP_X_FORWARDED_FOR}</a></div>| if ($ENV{HTTP_X_FORWARDED_FOR});

        unless ($running && $email) {
            my $status = `tail -n 15 /tmp/minio.log`;
            $form .= <<END
    <script>
        setTimeout(function() {
            \$.get("index.cgi?action=minioform&tab=minio", function(result) {
                \$("#minio").html(result);
            });
        }, 3000);
    </script>
    <div class="tab-pane container" id="minio">
        <table><tr><td>
            <div class="sk-wave">
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
                <div class="sk-wave-rect"></div>
            </div>
        </td><td>
            <h5 style="margin-left: 20px;">Preparing minio - this may take a few minutes...</h5>
        </td><tr></table>
        <pre>$status
        </pre>
    </div>
END
        } else {
            my $miniopwform .= <<END
        <form class="passwordform" id="miniopassword_form" action="index.cgi?action=changeminiopassword&tab=minio" method="post" onsubmit="limitMinioSpinner('miniopassword'); \$('#miniopassword').val(''); return false;" accept-charset="utf-8" autocomplete="off">
            <small>Set the password for the minio user stabile:</small>
            <div class="row">
                <div class="col-sm-10">
                    <input type="password" id="miniopassword" name="miniopassword" autocomplete="off" value="" class="password miniobutton">
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default miniobutton" type="submit" id="miniopassword_button">Set!</button>
                </div>
            </div>
        </form>
        <small style="margin-top:10px;">
            After setting the password, <a target="_blank" href="https://$dom/">log in here</a> as user stabile with your password.
        </small>
END
            ;
            $miniolimitform = <<END
        <div>
            Here you can manage some basic settings for your Minio installation.
        </div>
    <div>
		<form class="passwordform" id="limitminio_form" action="index.cgi?action=limitminio&tab=minio" method="post" onsubmit="limitMinioSpinner('limitminio'); return false;" accept-charset="utf-8">
			<div class="small">Allow Minio login from:</div>
			<div class="row">
				<div class="col-sm-10">
					<input id="limitminio" type="text" name="limitminio" value="$miniolimit" placeholder="IP address or network, e.g. '192.168.0.0/24 127.0.0.1'">
					$curip
				</div>
				<div class="col-sm-2">
					<button class="btn btn-default" type="submit" id="limitminio_button">Set!</button>
				</div>
			</div>
		</form>
$miniopwform
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
    <div class="tab-pane container" id="minio">
        $miniolimitform
    </div>
END
            ;
        } else {
            return <<END
Content-type: text/htm

$miniolimitform
END
        }

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
        \$("#currentwp").attr("href", "https://$dom/");
        \$("#currentwp").text("to minio");

    function limitMinioSpinner(target) {
        if (!target) target = "miniopassword";
        \$("#" + target + "_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        var ser = \$('#' + target + '_form').serialize();
        \$(".miniobutton").prop("disabled", true );
        \$.post('index.cgi?action=' + target + '&tab=minio', ser, function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".miniobutton").prop("disabled", false );

            setTimeout(function() {
                \$.get("index.cgi?action=minioform&tab=minio", function(result) {
                    \$("#minio").html(result);
                });
            }, 200);

        }).fail(function() {
            salert( "An error occurred :(" );
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
            \$(".miniobutton").prop("disabled", false );
        });
    }

    var linkElement = document.createElement("link");
    linkElement.rel = "stylesheet";
    linkElement.href = "tabs/minio/spinkit.css";
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

    } elsif ($action eq 'limitminio') {
        my $message = "Please supply a limit!";
        if (defined $in{limitminio}) {
            my $limit = $in{limitminio};
            my ($validlimit, $mess) = validate_limit($limit);
            my $conf = "/etc/apache2/conf-available/minio.conf";
            if ($validlimit) {
                if (`grep 'Require ip' /etc/apache2/conf-available/minio.conf`)
                {
                    $message =  "Minio https access was changed!";
                    $message .= `perl -pi -e 's/Require ip (.*)/Require ip $validlimit/;' $conf`;
                    `systemctl reload apache2`;
                } else {
                    $message =  "Unable to process minio.conf!";
                }
            } else {
                $message =  $mess;
            }
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;
    } elsif ($action eq 'miniopassword' && defined $in{miniopassword}) {
        my $message;
        my $pwd = $in{miniopassword};
        my $pmsg = IsBadPassword($pwd);
        if ($pmsg) {
            $message = "Please choose a stronger password: $pmsg";
        } else {
            `echo "$pwd" > /etc/stabile/miniopwd`;
            `systemctl restart stabile-minio`;
            $message = "The Minio password was changed!";
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;
    }
}

1;
