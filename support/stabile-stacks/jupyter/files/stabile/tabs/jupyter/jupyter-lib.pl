#!/usr/bin/perl

use JSON;
use Digest::SHA qw(sha1_base64 sha1_hex);
use Digest::MD5 qw(md5 md5_hex md5_base64);

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
    <div class="tab-pane" id="jupyter">
        <div>
            Here you can manage basic security for your Jupyter Notebook.
        </div>
        <small>Set the password for your Jupyter notebook:</small>
        <form class="passwordform" action="index.cgi?action=changejupyterpassword&tab=jupyter" method="post" onsubmit="passwordSpinner();" accept-charset="utf-8" id="jupyterform" autocomplete="off">
            <input type="password" name="jupyterpassword" autocomplete="off" value="" class="password" onfocus="doStrength(this);">
            <button class="btn btn-default" type="submit">Set!</button>
        </form>
        <small style="margin-top:10px;">
            After setting the password, <a target="_blank" href="https://$externalip.$appinfo{dnsdomain}:8889">log in here</a> with your password.
        </small>
    </div>
END
        ;

        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
        \$("#currentwpadmin").attr("href", "https://$externalip.$appinfo{dnsdomain}:8889/");
        \$("#currentwpadmin").text("to Jupyter Notebook");
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

    } elsif ($action eq 'changejupyterpassword' && defined $in{jupyterpassword}) {
        my $message;
        my $salt = `openssl rand -base64 5  | xargs echo -n`;
        my $pwd = $in{jupyterpassword};
        if ($pwd) {
            my $password = sha1_hex($pwd . $salt);
            $message .= `perl -pi -e "s/.*c\\.NotebookApp\\.password =.*/c.NotebookApp.password = 'sha1:$salt:$password'/" /home/stabile/.jupyter/jupyter_notebook_config.py`;
            $message .= `pkill -f jupyter`;
            $message .= "<div class=\"message\">The Jupyter password was changed!</div>";
        }
        return $message;
    }
}


1;
