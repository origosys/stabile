#!/usr/bin/perl

use JSON;
use Digest::MD5 qw(md5 md5_hex md5_base64);

my $dnsdomain_json = `curl -k https://$gw/stabile/networks?action=getdnsdomain`;
my $dom_obj = from_json ($dnsdomain_json);
my $dnsdomain =  $dom_obj->{'domain'};
my $dnssubdomain = $dom_obj->{'subdomain'};
$dnsdomain = '' unless ($dnsdomain =~  /\S+\.\S+$/ || $dnsdomain =~  /\S+\.\S+\.\S+$/);
my $esc_dnsdomain = $dnsdomain;
$esc_dnsdomain =~ s/\./\\./g;
my $dom = ($dnsdomain)?"$externalip.$dnssubdomain.$dnsdomain":$externalip;

sub matomo {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
        my $form;
        # Redirect to upgrade page if still upgrading
        if (-e "/tmp/restoring") {
            $form .=  qq|<script>loc=document.location.href; setTimeout(function(){document.location=loc;}, 1500); </script>|;
        }
        $form .= <<END
    <div class="tab-pane" id="matomo">
        <form class="passwordform" action="index.cgi?action=changematomopassword&tab=matomo" method="post" onsubmit="spinner('#matomopassword_button');" accept-charset="utf-8" id="matomoform" autocomplete="off">
            <div>
                Here you can manage basic security for Matomo.
            </div>
            <small>Set password for Matomo user "stabile":</small>
            <div class="row">
                <div class="col-sm-10">
                    <input type="password" name="matomopassword" autocomplete="off" value="" class="password">
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default" type="submit" id="matomopassword_button">Set!</button>
                </div>
            </div>
            <small style="margin-top:10px;">
                After setting the password <a target="_blank" href="https://$dom/matomo">log in here</a> with username "stabile" and your password.
            </small>
        </form>
    </div>
END
        ;

        return $form;

    } elsif ($action eq 'js') {
        # Generate and return javascript the UI for this tab needs
        my $js = <<END
        \$("#currentwpadmin").attr("href", "https://$dom/matomo");
        \$("#currentwpadmin").text("to Matomo");
        \$("#currentwpadmin").parent().show()
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

    } elsif ($action eq 'changematomopassword' && defined $in{matomopassword}) {
        my $message;
        my $pwd = $in{matomopassword};
        if ($pwd) {
#            my $password = md5_base64($pwd);
            my $password = `php -r 'echo password_hash(md5("$pwd"), PASSWORD_DEFAULT);'`;
            $message .= `mysql matomo -e 'UPDATE matomo_user SET password = "$password" WHERE login = "stabile" AND superuser_access = 1;'`;
            $message .= "<div class=\"message\">The Matomo password was changed!</div>";
        }
        return $message;
    }
}

1;