#!/usr/bin/perl

sub commands {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
# Generate and return the HTML form for this tab
        my $form = <<END
<div class="tab-pane" id="commands">
To run a command on all servers, type it below and click "run".
<form style="margin-bottom:18px;" class="passwordform" action="index.cgi?tab=commands" onsubmit="return false;">
<input id="command" name="command" type="text" title="Type the command you want to run on all servers" rel="tooltip" data-placement="bottom" value="uptime" style="width:80%; display: inline; margin-right:3px;"></input>
<button class="btn btn-default" id="run_command" title="Click to run the command. The result will be shown below." rel="tooltip" data-placement="bottom" onclick="\$('[rel=tooltip]').tooltip('hide'); runCommand(); return false;">Run</button>
</form>
<div style="margin-bottom: 5px;" id="resultpane" class="resultpane">
</div>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
    function runCommand() {
        console.log("Running command on webmin servers");
        var cmd = \$("#command").val();
        \$( "#command" ).prop( "disabled", true );
        \$( "#run_command" ).prop( "disabled", true );
        \$("#resultpane").html('<span class="label label-info">Waiting for results...</span>');
        \$.post( "index.cgi?action=runcommand&tab=commands", { command: cmd })
        .done(function( data ) {
            getResults(data.servers);
        })
        .fail(function() {
            salert( "An error occurred :(" );
            \$( "#command" ).prop( "disabled", false );
            \$( "#run_command" ).prop( "disabled", false );
        });
    }

    function getResults(servs) {
        \$.post( "index.cgi?action=getresults&tab=commands", {servers: JSON.stringify(servs)}, "json")
        .done(function( data ) {
            if (data) {
                \$("#resultpane").html(data);
                \$("#command" ).prop( "disabled", false );
                \$("#run_command" ).prop( "disabled", false );
            } else { // http probably timeout because of a long running command - try again
                if (cmdtries < 2) {
                    cmdtries++;
                    \$("#resultpane").html('<span class="label label-info">Still waiting for results...(' + cmdtries + ')</span>');
                    getResults(servs);
                } else {
                    cancelResults();
                }
            }
        })
        .fail(function() {
            cancelResults();
        });
    }

    function cancelResults() {
        cmdtries = 0;
        \$.get( "index.cgi?action=cancelresults&tab=commands")
        .done(function( data ) {
            \$( "#command" ).prop( "disabled", false );
            \$( "#run_command" ).prop( "disabled", false );
            \$("#resultpane").html('<span class="label label-info">No results received :(</span>');
        })
    }
END
;
        return $js;

    } elsif ($action eq 'runcommand') {
        my $res = "Content-type: application/json\n\n";
        $res .= run_command($in{command}, 0, $internalip);
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
