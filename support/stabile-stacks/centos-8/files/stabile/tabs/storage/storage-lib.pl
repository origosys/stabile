#!/usr/bin/perl

sub storage {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
# Generate and return the HTML form for this tab
        my $form = <<END
<div class="tab-pane container" id="storage">
<form id="storage_form" autocomplete="off">
<div style="margin-bottom: 5px; width:97%;" id="storageresultpane" class="resultpane">
</div>
</form>
<form style="margin-bottom:18px; margin-top:18px;" class="passwordform" action="index.cgi?tab=storage" onsubmit="return false;">
<button class="btn btn-default" id="update_storage" title="Click to reload storage status." rel="tooltip" data-placement="bottom" onclick="\$('[rel=tooltip]').tooltip('hide'); updatestorageStatus(); return false;"><span class="glyphicon glyphicon-repeat"></button>
<button class="btn btn-default" id="resize_storage" title="Click to resize storage." rel="tooltip" data-placement="bottom" onclick="\$('[rel=tooltip]').tooltip('hide'); resizestorage(); return false;">Resize</button>
</form>
<div class="small">
Please be aware that you can only increase disk volume size - NOT decrease. Also note, that this cannot be undone. Once your disk volume has been increased,
the only way to reduce storage use is to create a new disk, copy your data to this, and delete the old disk.
</div>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
    function updatestorageStatus() {
        \$("#storageresultpane").html('<table style="display:inline-block; margin:0; padding:4px;"><tr><td><img src="images/loader.gif"></td></tr></table>');
        \$( "#noupdate_storage" ).prop( "disabled", true );
        \$( "#resize_storage" ).prop( "disabled", true );
        target = "index.cgi?action=storagestatus&tab=storage";
        \$.post( target, "json")
        .done(function( data ) {
            showstorageStatus(data.servers);
        })
        .fail(function() {
            salert( "An error occurred :(" );
        });
    }

    function showstorageStatus(servs) {
        \$.post( "index.cgi?action=getresults&tab=storage", {servers: JSON.stringify(servs)}, "json")
        .done(function( data ) {
            if (data) {
                \$("#storageresultpane").html(data);
                if (\$(".resize-available").length>0) \$( "#resize_storage" ).prop( "disabled", false );
                \$( "#update_storage" ).prop( "disabled", false );
                \$(".storage_size").val("");
                \$("[rel=tooltip]").tooltip({delay: { show: 500, hide: 100 }});
            } else { // http probably timeout because of a long running command - try again
                if (cmdtries < 2) {
                    cmdtries++;
                    \$("#storageresultpane").html('<span class="label label-info">Still waiting for results...(' + cmdtries + ')</span>');
                    showstorageStatus(servs);
                } else {
                    cancelstorageResults();
                }
            }
        })
        .fail(function() {
            cancelstorageResults();
        });
    }

    function resizestorage() {
        \$("#storageresultpane").html('<table style="display:inline-block; margin:0; padding:4px;"><tr><td><img src="images/loader.gif"></td></tr></table>');
        \$( "#noupdate_storage" ).prop( "disabled", true );
        \$( "#resize_storage" ).prop( "disabled", true );
        target = "index.cgi?action=resizestorage&tab=storage";
        \$.post( target, \$("#storage_form").serialize())
        .done(function( data ) {
            showresizeStatus(data.servers);
        })
        .fail(function() {
            salert( "An error occurred :(" );
        });

    }

    function showresizeStatus(servs) {
        \$.post( "index.cgi?action=getresults&tab=storage", {servers: JSON.stringify(servs)}, "json")
        .done(function( data ) {
            if (data) {
                \$( "#update_storage" ).prop( "disabled", false );
                \$("#storageresultpane").html(data);
            } else { // http probably timeout because of a long running command - try again
                if (cmdtries < 2) {
                    cmdtries++;
                    \$("#storageresultpane").html('<span class="label label-info">Still waiting for results...(' + cmdtries + ')</span>');
                    showresizeStatus(servs);
                } else {
                    cancelstorageResults();
                }
            }
        })
        .fail(function() {
            cancelstorageResults();
        });
    }

    function cancelstorageResults() {
        cmdtries = 0;
        \$.get( "index.cgi?action=cancelstorage&tab=storage")
        .done(function( data ) {
            \$("#storageresultpane").html('<span class="label label-info">No results received :(</span>');
        })
    }

    \$(document).ready(function () {
        \$( "#resize_storage" ).prop( "disabled", true );
        updatestorageStatus();
    });

END
;
        return $js;

    } elsif ($action eq 'storagestatus') {
        my $res = "Content-type: application/json\n\n";
        my $json_text = `curl -ks "https://$gw/stabile/servers?system=this"`;
        my $cmd = "stabile-helper liststorage";
        $res .= run_command($cmd, 0, $internalip);
        return $res;

    } elsif ($action eq 'resizestorage') {
        my $res = "Content-type: application/json\n\n";
        my $specific_commands = {};
        foreach my $k (keys(%in)) {
            if ($k =~ /(\d+-\d+-\d+-\d+)-(\w+)-resize/) {
                my $serv = $1;
                my $dev = $2;
                $serv =~ s/-/./g;
                $specific_commands->{$serv} = qq|stabile-helper resizestorage $in{$k}G| if ($in{$k});
            }
        }
        $res .= run_command("echo 'Running server-specific commands.", 0, $internalip, $specific_commands);
        return $res;

    } elsif ($action eq 'getresults') {
        my $res = "Content-type: text/html\n\n";
        my $servers = from_json($in{servers});
        $res .= get_results($servers);
        return $res;

    } elsif ($action eq 'cancelresults') {
        my $res = "Content-type: text/html\n\n";
        $res .= cancel_results();
        return $res;
    }
}

1;
