#!/usr/bin/perl

use JSON;
use Digest::SHA qw(sha1_base64 sha1_hex);
use Digest::MD5 qw(md5 md5_hex md5_base64);

my $dnsdomain =  $appinfo{dnsdomain};
my $dnssubdomain = $appinfo{'dnssubdomain'};
my $dom = ($dnsdomain && $dnssubdomain)?"$externalip.$dnssubdomain.$dnsdomain":"$externalip";

sub jupyter {
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
    <div class="tab-pane container" id="jupyter">
        <div>
            Here you can manage basic security for your Jupyter Notebook.
        </div>
        <small>Set the password for your Jupyter notebook:</small>
        <form class="passwordform" action="index.cgi?action=jupyterpassword&tab=jupyter" method="post" onsubmit="jupyterSpinner(); \$('#jupyterpassword').val(''); return false;" accept-charset="utf-8" id="jupyterpassword_form" autocomplete="off">
            <div class="row">
                <div class="col-sm-10">
                   <input type="password" name="jupyterpassword" id="jupyterpassword" autocomplete="off" value="" class="password"">
                </div>
                <div class="col-sm-2">
                    <button class="btn btn-default" type="submit" id="jupyterpassword_button">Set!</button>
                </div>
            </div>
        </form>
        <small style="margin-top:10px;">
            After setting the password, <a target="_blank" href="https://$dom:8889">log in here</a> with your password.
        </small>
    </div>
END
        ;

        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
        \$("#currentwp").attr("href", "https://$dom:8889/");
        \$("#currentwp").text("to Jupyter Notebook");
        \$("#currentwp").parent().show()

    function jupyterSpinner(target) {
        if (!target) target = "jupyterpassword";
        \$("#" + target + "_button").prop("disabled", true ).html('Set! <i class="fa fa-cog fa-spin"></i>');
        var ser = \$('#' + target + '_form').serialize();
        \$.post('index.cgi?action=' + target + '&tab=jupyter', ser, function(data) {}
        ,'json'
        ).done(function( data ) {
            salert(data.message);
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
        }).fail(function() {
            salert( "An error occurred :(" );
            \$("#" + target + "_button").prop("disabled", false ).html('Set!');
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

    } elsif ($action eq 'jupyterpassword' && defined $in{jupyterpassword}) {
        my $message;
        my $salt = `openssl rand -base64 5  | xargs echo -n`;
        my $pwd = $in{jupyterpassword};
        if ($pwd) {
            my $password = sha1_hex($pwd . $salt);
            $message .= `perl -pi -e "s/.*c\\.NotebookApp\\.password =.*/c.NotebookApp.password = 'sha1:$salt:$password'/" /home/stabile/.jupyter/jupyter_notebook_config.py`;
            $message .= `pkill -f jupyter`;
            $message .= "The Jupyter password was changed!";
        }
        return qq|Content-type: application/json\n\n{"message": "$message"}|;
    }
}


1;
