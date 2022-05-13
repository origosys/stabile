#!/usr/bin/perl

sub software {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
# Generate and return the HTML form for this tab
        my $form = <<END
<div class="tab-pane" id="software">
To update all software on all servers to latest version, click "upgrade".
<div style="margin-bottom: 5px;" id="softwareresultpane" class="resultpane">
</div>
<form style="margin-bottom:18px;" class="passwordform" action="index.cgi?tab=software" onsubmit="return false;">
<button class="btn btn-default" id="update_software" title="Click to check if upgrades are available." rel="tooltip" data-placement="bottom" onclick="\$('[rel=tooltip]').tooltip('hide'); updateSoftwareStatus(); return false;"><span class="glyphicon glyphicon-repeat"></button>
<button class="btn btn-default" id="upgrade_software" title="Click to update. The result will be shown below." rel="tooltip" data-placement="bottom" onclick="\$('[rel=tooltip]').tooltip('hide'); upgradeSoftware(); return false;">Upgrade</button>
</form>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
    function updateSoftwareStatus() {
        \$("#softwareresultpane").html('<table style="display:inline-block; margin:0; padding:4px;"><tr><td><img src="images/loader.gif"></td></tr></table>');
        \$( "#update_software" ).prop( "disabled", true );
        \$( "#upgrade_software" ).prop( "disabled", true );
        target = "index.cgi?action=softwarestatus&tab=software";
        \$.post( target, "json")
        .done(function( data ) {
            showSoftwareStatus(data.servers);
        })
        .fail(function() {
            salert( "An error occurred :(" );
        });
    }

    function showSoftwareStatus(servs) {
        \$.post( "index.cgi?action=getresults&tab=software", {servers: JSON.stringify(servs)}, "json")
        .done(function( data ) {
            if (data) {
                \$("#softwareresultpane").html(data);
                if (\$(".upgrade-available").length>0) \$( "#upgrade_software" ).prop( "disabled", false );
                \$( "#update_software" ).prop( "disabled", false );
            } else { // http probably timeout because of a long running command - try again
                if (cmdtries < 2) {
                    cmdtries++;
                    \$("#softwareresultpane").html('<span class="label label-info">Still waiting for results...(' + cmdtries + ')</span>');
                    showSoftwareStatus(servs);
                } else {
                    cancelSoftwareResults();
                }
            }
        })
        .fail(function() {
            cancelSoftwareResults();
        });
    }

    function upgradeSoftware() {
        \$("#softwareresultpane").html('<table style="display:inline-block; margin:0; padding:4px;"><tr><td><img src="images/loader.gif"></td></tr></table>');
        \$( "#update_software" ).prop( "disabled", true );
        \$( "#upgrade_software" ).prop( "disabled", true );
        target = "index.cgi?action=upgradesoftware&tab=software";
        \$.post( target, "json")
        .done(function( data ) {
            showUpgradeStatus(data.servers);
        })
        .fail(function() {
            salert( "An error occurred :(" );
        });

    }

    function showUpgradeStatus(servs) {
        \$.post( "index.cgi?action=getresults&tab=software", {servers: JSON.stringify(servs)}, "json")
        .done(function( data ) {
            if (data) {
                \$( "#update_software" ).prop( "disabled", false );
                \$("#softwareresultpane").html(data);
            } else { // http probably timeout because of a long running command - try again
                if (cmdtries < 2) {
                    cmdtries++;
                    \$("#softwareresultpane").html('<span class="label label-info">Still waiting for results...(' + cmdtries + ')</span>');
                    showUpgradeStatus(servs);
                } else {
                    cancelSoftwareResults();
                }
            }
        })
        .fail(function() {
            cancelSoftwareResults();
        });
    }

    function cancelSoftwareResults() {
        cmdtries = 0;
        \$.get( "index.cgi?action=cancelsoftware&tab=software")
        .done(function( data ) {
            \$("#softwareresultpane").html('<span class="label label-info">No results received :(</span>');
        })
    }

    \$(document).ready(function () {
        \$( "#upgrade_software" ).prop( "disabled", true );
        updateSoftwareStatus();
    });

END
;
        return $js;

    } elsif ($action eq 'softwarestatus') {
        my $res = "Content-type: application/json\n\n";
        my $cmd = "echo 'n' | apt-get -V -u upgrade | tail -n +4 | head -n -1";
        $res .= run_command($cmd, 0, $internalip);
        return $res;

    } elsif ($action eq 'upgradesoftware') {
        my $res = "Content-type: application/json\n\n";
        $res .= run_command("TERM=linux DEBIAN_FRONTEND=noninteractive apt-get -q -y --force-yes -V -u upgrade", 0, $internalip);
        return $res;

    } elsif ($action eq 'getresults') {
        my $res = "Content-type: text/html\n\n";
        my $servers = from_json($in{servers});
        $res .= get_results($servers);
        return $res;

    } elsif ($action eq 'cancelresults') {
        my $res = "Content-type: text/html\n\n";
        ## !! Please observe that cancel_results is defined in commands-lib.pl, which therefore must be loaded !!
        $res .= cancel_results();
        return $res;
    }
}

1;
