#!/usr/bin/perl

use JSON;
use Digest::SHA qw(sha1_base64 sha1_hex);
use Digest::MD5 qw(md5 md5_hex md5_base64);

sub codiad {
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
    <div class="tab-pane container" id="codiad">
        <div>
            Here you can manage basic security for the Codiad Web IDE.
        </div>
        <small>Set password for Codiad user "stabile":</small>
        <form class="passwordform" action="index.cgi?action=changecodiadpassword&tab=codiad" method="post" onsubmit="passwordSpinner();" accept-charset="utf-8" id="codiadform" autocomplete="off">
            <div class="row">
                <div class="col-sm-10">
                    <input type="password" name="codiadpassword" autocomplete="off" value="" class="password" onfocus="doStrength(this);">
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default" type="submit">Set!</button>
                </div>
            </div>
        </form>
        <small style="margin-top:10px;">
            After setting the password <a target="_blank" href="https://$dom">log in here</a> with username "stabile" and your password.
        </small>
    </div>
END
        ;

        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
        \$("#currentwpadmin").attr("href", "https://$externalip.$appinfo{dnsdomain}/");
        \$("#currentwpadmin").text("to Codiad Web IDE");
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

    } elsif ($action eq 'changecodiadpassword' && defined $in{codiadpassword}) {
        my $message;
        my $pwd = $in{codiadpassword};
        if ($pwd) {
            my $password = sha1_hex(md5_hex($pwd));
            $message .= `perl -pi -e 's/password"\:".*"/password":"$password"/' /var/www/html/data/users.php`;
            $message .= "<div class=\"message\">The Codiad password was changed!</div>";
        }
        return $message;
    }
}


1;
