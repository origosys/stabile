#!/usr/bin/perl

sub servers {
    my $action = shift;
    my $in_ref = shift;
    my %in = %{$in_ref};

    if ($action eq 'form') {
# Generate and return the HTML form for this tab
        my $form = <<END
<div class="tab-pane container" id="servers">
The servers in this stack are listed below.
<div class="small">
Click on a server to launch a terminal and log in with username "stabile" and the password you set in the "security" tab.
</div>
<div style="margin-bottom: 5px;" id="loadservers">
<table style="display:inline-block; margin:0; padding:4px;"><tr><td><img src="images/loader.gif"></td></tr></table>
</div>
<form style="margin-bottom:8px;" class="passwordform" action="index.cgi?tab=servers" onsubmit="return false;">
<input id="n" name="n" type="text" title="The number of servers you want to add/remove" rel="tooltip" data-placement="bottom" value="1" style="width:40px; display: inline; margin-right:3px;"></input>
<input type="hidden" name="delete" id="delete">
<button class="btn btn-default" id="add_servers" title="Click to add servers to your stack. Type in the number of servers you want to add in the text field." rel="tooltip" data-placement="bottom" onclick="\$('[rel=tooltip]').tooltip('hide'); addServers('', \$('#n').val()); return false;"><span class="glyphicon glyphicon-plus"></span></button>
<button class="btn btn-default" id="remove_servers" title="Click to remove servers from your stack. Type in the number of servers you want to remove in the text field." rel="tooltip" data-placement="bottom" onclick="\$('[rel=tooltip]').tooltip('hide'); addServers(1, \$('#n').val()); return false;"><span class="glyphicon glyphicon-minus"></span></span></button>
<button class="btn btn-default" id="refresh_servers" title="Refresh" onclick="listServers(true); return false;"><span class="glyphicon glyphicon-repeat"></span></button>
</form>
</div>
END
;
        return $form;

    } elsif ($action eq 'js') {
# Generate and return javascript the UI for this tab needs
        my $js = <<END
    \$(document).ready(function () {
        listServers(true);
        timeout = setTimeout(function() {
              listServers(true);
        }, 5000);
        interval = setInterval(function() {
              listServers(true);
        }, 15000);
    });

    function addServers(del, n) {
        if (n>0) {
            if (del) {
                salert("Removing " + n + " server" + (n==1?"":"s"));
            } else {
                salert("Adding " + n + " server" + (n==1?"":"s"));
            }
            \$( "#n" ).prop( "disabled", true );
            \$( "#add_servers" ).prop( "disabled", true );
            \$( "#remove_servers" ).prop( "disabled", true );
            \$( "#refresh_servers" ).prop( "disabled", true );
            \$.post( "index.cgi?action=addservers&tab=servers", { n: 1, delete: del }, "json")
              .done(function( data ) {
                  salert( data.message );
                  listServers(true);
                  n--;
                  addServers(del, n);
              })
              .fail(function() {
                 salert( "An error occurred :(" );
                \$( "#n" ).prop( "disabled", false );
                \$( "#add_servers" ).prop( "disabled", false );
                \$( "#remove_servers" ).prop( "disabled", false );
                \$( "#refresh_servers" ).prop( "disabled", false );
                listServers(true);
              })
              ;
              updating = true;
              listServers(true);
        } else {
            \$( "#n" ).prop( "disabled", false );
            \$( "#add_servers" ).prop( "disabled", false );
            \$( "#remove_servers" ).prop( "disabled", false );
            \$( "#refresh_servers" ).prop( "disabled", false );
            updating = false;
            listServers(true);
        }
    };

    function saveWebminServers() {
        console.log("Registering webmin servers");
        \$.get( "index.cgi?action=savewebminservers&tab=servers", "json")
        .done(function( data ) {
            console.log(data);
        });
    }

    function loadTerm(networkuuid1, name, title) {
        if (\$("#terminal").length==0) {
            \$("#nav-tabs").append('<li title="' + name + '"><a data-toggle="tab" href="#terminal">' + name + '&nbsp;</a> <span class="no-closeText">x</span> </li>');
            \$("#tab-content").append('<div id="terminal" class="tab-pane">Terminal</div>');

            \$("#nav-tabs").on("click", "a", function(e){
                  e.preventDefault();
                  \$(this).tab('show');
                })
                .on("click", "span", function () {
                    var anchor = \$(this).siblings('a');
                    \$(anchor.attr('href')).remove();
                    \$(this).parent().remove();
                    \$(".nav-tabs li").children('a').last().click();
                });

        }
        \$('#nav-tabs li:last-child a').click();
        if (\$("#" + networkuuid1).length==0)
            \$("#terminal").html('<iframe src="https://' + location.host + '/stabile/pipe/http://' + networkuuid1 + ':4200/" style="height:364px; width:100%; nowidth:710px; border:none;" id="' + networkuuid1 + '">Terminal</iframe>');
        return false;
    }

    function listServers(webmin) {
        //console.log("listing servers", (updating?"spinner":"no spinner"), updating, webmin);
        var bgcolors = {
                ready: "lightgreen",
                running: "darkgreen",
                starting: "orange",
                shuttingdown: "orange",
                resuming: "orange",
                suspending: "orange",
                shutoff: "red",
                inactive: "gray",
                paused: "gray"
                };
        var stext = '';
        var sloading = false;
        var target;
        if (webmin) target = "index.cgi?action=listservers&webmin=1&tab=servers";
        else target = "index.cgi?action=listservers&tab=servers";
        \$.post( target, "json")
        .done(function( data ) {
            if (data.length<2) \$("#net_test").hide(); // Net test only works with 2 servers or more
            else \$("#net_test").show();
            for (var s in data) {
                serv = data[s];
                // var termurl = '/stabile/pipe/http://' + serv.networkuuid1 + ':4200/';
                // var termurl = 'index.cgi?action=terminal&tab=servers&ip=' + serv.internalip; + '/'

                stext += '<table title="' + serv.internalip + ' (' + serv.name + ')' + ':' + serv.status + '" id="' + serv.uuid + '" style="display:inline-block; margin:0; padding:0;"><tr><td style="background-color: ' + bgcolors[serv.status] +
                ';"><a href="https://' + location.host + '/stabile/pipe/http://' + serv.networkuuid1 + ':4200/" target="_blank" noonclick="loadTerm(\\\'' + serv.networkuuid1 + '\\\', \\\'' + serv.internalip + '\\\', \\\'' + serv.name + '\\\');"><img src="images/server-black.png"></a></td></tr></table> ';
//                if ( bgcolors[serv.status]=="orange" || bgcolors[serv.status]=="darkgreen" ) sloading = true;
                if ( bgcolors[serv.status]=="orange" ) sloading = true;
            }
            if (updating) {
                stext += '<table style="display:inline-block; margin:0; padding:4px;"><tr><td><img src="images/loader.gif"></td></tr></table> ';
            } else if (sloading && !webmin) {
                clearTimeout(timeout);
                timeout = setTimeout(function() {
                      listServers(true);
                }, 5000);
            }
            \$("#loadservers").html(stext);
        });
    }
END
;
        return $js;

    } elsif ($action eq 'listservers') {
        my $res = "Content-type: application/json\n\n";
        my $json_text = `curl -ks "https://$gw/stabile/servers?system=this"`;
        my %wservers_hash;
        my @wservers = ();
        @wservers = list_webmin_servers() if ($in{webmin});
        foreach my $wserv (@wservers) {
            # $wservers_hash{$wserv->{host}} = $wserv->{status};
            $wservers_hash{$wserv->{host}} = 'ready';
        }

        my $servers_ref = from_json($json_text);
        my @servers = @$servers_ref;
        foreach my $serv (@servers) {
            my $ip = $serv->{internalip};
            my $wstatus = $wservers_hash{$ip};
            $serv->{status} = $wstatus if ($wstatus eq 'ready' && $serv->{status} eq 'running');
            $serv->{status} = 'ready' if ($serv->{self});
            $serv->{webminstatus} = $wstatus;
        }
        @servers = sort {$a->{'name'} cmp $b->{'name'}} @servers;
        $json_text = to_json(\@servers, {pretty => 1});
        $res .= $json_text;
        return $res;

    } elsif ($action eq 'addservers') {
        $res = "Content-type: application/json\n\n";
        my $n = $in{'n'} + 0;
        $n = 1 unless ($n);
        my $delete;
        my @servers;
        if ($in{'delete'} || $n<0) {
            $delete = 1;
            $n = -1 * $n if ($n<0);
            my $s = list_simplestack_servers();
            @servers = @$s;
        }
        my $inc=0;
        $message .= ($delete)?"Removed server(s) ":"Added server(s) ";
        for (my $i=0; $i < $n; $i++) {
            if ($delete) {
                if ($servers[$i]->{self}) { # Dont delete myself
                    $n++;
                    $i++;
                }
                if ($servers[$i+$inc]->{uuid}) {
                    delete_simplestack_server($servers[$i+$inc]);
                    if ($servers[$i+$inc]->{internalip} && $servers[$i+$inc]->{internalip} ne '--') {
                        delete_webmin_server($servers[$i+$inc]->{internalip});
                    }
                }
            } else {
                my $mess = create_simplestack_server();
                $message .= $mess;
            }
        }
        $res .= qq|{"message": "$message"}|;
        return $res;

    } elsif ($action eq "terminal") {
        if ($in{ip}) {
            my $s = list_simplestack_servers();
            @servers = @$s;
            my $serv;
            foreach $serv (@servers) {
                last if ($serv->{internalip} eq $in{ip})
            }

            my $terminalcmd = qq[/usr/share/webmin/stabile/tabs/servers/shellinaboxd --cgi -t --css=/usr/share/webmin/stabile/tabs/servers/shellinabox.css --debug 2>/tmp/sib.log];
            my $cmdout;
            $cmdout .= `$terminalcmd`;
            $cmdout =~ s/<title>.+<\/title>/<title>Server: $serv->{name}<\/title>/;
            $cmdout =~ s/:(\d+)\//\/shellinabox\/$1\//g;
            return $cmdout;
        } else {
            return "ERROR Unable to open terminal\n";
        }

    }
}

sub create_simplestack_server {
    my ($site) = @_;
    my $name = $site->{'name'};
    my $nstr = ($name?"&name=$name":'');
    my $cmd = qq[curl -ks "https://$gw/stabile/systems?action=buildsystem&monitors=ping&start=1$nstr"];
    my $json_text = `$cmd`;
    if ($json_text =~ /Status=starting (.*)/) {
    	return $1;
    } else {
    	return "Error - unable to start your new server";
    }
}

sub delete_simplestack_server {
    my ($site) = @_;
    my $uuid = $site->{'uuid'};

    my $postdata = qq/{"uuid": "$uuid", "action": "destroy", "wait": "true"}/;
    my $cmd = qq[curl -ks -X POST --data-urlencode 'POSTDATA=$postdata' https://$gw/stabile/servers];

    my $reply = `$cmd`;

    my $putdata = qq/{"uuid": "$uuid", "action": "deletesystem"}/;
    $cmd = qq[curl -ks -X PUT --data-urlencode 'PUTDATA=$putdata' https://$gw/stabile/systems];
    $reply .= `$cmd`;

    return $reply;
}

1;
