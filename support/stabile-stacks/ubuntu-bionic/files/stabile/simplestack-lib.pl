use JSON;
use Data::Dumper;
use URI::Encode qw(uri_encode uri_decode);
use WebminCore;
init_config();

my $dev = 'eth0';
$dev = 'ens3';
$ip = $1 if (`ifconfig $dev` =~ /inet (\d+\.\d+\.\d+)\.\d+/);
$gw = "$ip.1" if ($ip);

sub get_internalip {
    my $internalip;
    if (!(-e "/tmp/internalip") && !(-e "/etc/stabile/internalip")) {
        $internalip = $1 if (`curl -sk https://$gw/stabile/networks/this` =~ /"internalip" : "(.+)",/);
        chomp $internalip;
        `echo "$internalip" > /tmp/internalip` if ($internalip);
        `mkdir /etc/stabile` unless (-e '/etc/stabile');
        `echo "$internalip" > /etc/stabile/internalip` if ($internalip);
    } else {
        $internalip = `cat /tmp/internalip` if (-e "/tmp/internalip");
        $internalip = `cat /etc/stabile/internalip` if (-e "/etc/stabile/internalip");
        chomp $internalip;
    }
    return $internalip;
}

sub get_externalip {
    my $externalip;
    if (!(-e "/tmp/externalip")) {
        $externalip = $1 if (`curl -sk https://$gw/stabile/networks/this` =~ /"externalip" : "(.+)",/);
        chomp $externalip;
        if ($externalip eq '--') {
            # Assume we have ens4 up with an external IP address
            $externalip = `ifconfig ens4 | grep -o 'inet addr:\\\S*' | sed -n -e 's/^inet addr://p'`;
            chomp $externalip;
        }
        `echo "$externalip" > /tmp/externalip` if ($externalip);
    } else {
        $externalip = `cat /tmp/externalip` if (-e "/tmp/externalip");
        chomp $externalip;
    }
    return $externalip;
}

sub get_appid {
    my $appid;
    if (!(-e "/tmp/appid")) {
        $appid = $1 if (`curl -sk https://$gw/stabile/servers?action=getappid` =~ /appid: (.+)/);
        chomp $appid;
        `echo "$appid" > /tmp/appid` if ($appid);
    } else {
        $appid = `cat /tmp/appid` if (-e "/tmp/appid");
        chomp $appid;
    }
    return $appid;
}

sub get_appinfo {
    my $appinfo;
    $appinfo = `curl -sk https://$gw/stabile/servers?action=getappinfo`;
    my $json_hash_ref = from_json($appinfo);
    return $json_hash_ref;
}

sub list_simplestack_networks {
    my $json_text = `curl -ks "https://$gw/stabile/networks?system=this"`;
    $json_array_ref = from_json($json_text);
    return $json_array_ref;
}

sub list_simplestack_storagepools {
    my $json_text = `curl -ks "https://$gw/stabile/images?action=liststoragepools"`;
    $json_array_ref = from_json($json_text);
    return $json_array_ref;
}

sub get_network {
    my $domuuid = shift;
    my $json_text = `curl -ks "https://$gw/stabile/networks?system=$domuuid"`;
    $json_array_ref = from_json($json_text);
    my @json_array = @$json_array_ref;
    push @json_array, () unless (@json_array);
    return $json_array[0];
}

sub list_webmin_servers {
    foreign_require("servers", "servers-lib.pl");
    my @wservers = &foreign_call("servers", "list_servers");
    #foreach my $wserv (@wservers) {
    #    $wserv->{status} = ((&foreign_call("servers", "test_server", $wserv->{host}))?"unavailable":"ready");
    #}
    return @wservers;
}

sub save_webmin_server {
    my $host = shift;
    my $pass = shift;
    my $id = $host;
    $id = $1 if ($id =~ /.*\.(\d+)$/); # Use last number in IP address
    $pass = `cat /etc/webmin/servers/$id.serv | sed -n -e 's/^pass=//p'` unless ($pass);
    chomp $pass;
    $pass = 'stabile' unless ($pass);
    my $s = {
              'user' => 'admin',
              'pass' => $pass,
              'ssl' => '0',
              'file' => "/etc/webmin/servers/$id.serv",
              'port' => '10000',
              'host' => $host,
              'realhost' => '',
              'id' => $id,
              'type' => 'ubuntu',
              'fast' => '0'
            };
    foreign_require("servers", "servers-lib.pl");
    my $status = &foreign_call("servers", "save_server", $s);
    return $status;
}

sub delete_webmin_server {
    my $id = shift;
    $id = $1 if ($id =~ /.*\.(\d+)$/);
    foreign_require("servers", "servers-lib.pl");
    my $status = &foreign_call("servers", "delete_server", $id);
    return $status;
}

sub test_webmin_server {
    my $host = shift;
    foreign_require("servers", "servers-lib.pl");
    my $status = &foreign_call("servers", "test_server", $host);
    return $status;
}

sub show_me {
    my $json_text = `curl -ks "https://$gw/stabile/users/me"`;
    if ($json_text =~ /^\[/) {
        $json_hash_ref = from_json($json_text);
        return $json_hash_ref->[0];
    }
}

sub show_running_server {
    my $json_text = `curl -ks "https://$gw/stabile/servers/this"`;
    $json_hash_ref = from_json($json_text);
    return $json_hash_ref;
}

sub show_management_server {
    # Try twice
    my $json_text = `curl -ks "https://$gw/stabile/systems/this"`;
    if ($json_text =~ /^\[/) {
        $json_array_ref = from_json($json_text);
        return $json_array_ref->[0];
    } else {
        sleep 5;
        $json_text = `curl -ks "https://$gw/stabile/systems/this"`;
        if ($json_text =~ /^\[/) {
            $json_array_ref = from_json($json_text);
            return $json_array_ref->[0];
        }
    }
}

sub modify_simplestack_server {
    my ($site) = @_;
    my $uuid = $site->{'uuid'};
    my $name = $site->{'name'};
    my $putdata = qq/{"uuid": "$uuid", "name": "$name"}/;
    my $cmd = qq[curl -ks -X PUT --data-urlencode 'PUTDATA=$putdata' https://$gw/stabile/servers];
    my $reply = `$cmd`;
    return $reply;
}

sub apply_configuration {
    kill_byname_logged('HUP', 'simplestackd');
}

sub run_command {
    my $command = shift;
    my $skip_servers = shift;
    my $internalip = shift;
    my $specific_commands = shift;
    foreign_require("cluster-shell", "cluster-shell-lib.pl");
    foreign_require("servers", "servers-lib.pl");
    my @servers = &foreign_call("servers", "list_servers");
    my @servs;

    # Make sure admin server is registered
    if (!@servers && $internalip) {
        save_webmin_server($internalip) unless ( -e "/etc/webmin/servers/$internalip.serv");
        @servers = &foreign_call("servers", "list_servers");
    }

    # Index actual servers so we don't run a command on a server that has been removed but is still in Webmin
    my $sservers_ref = list_simplestack_servers();
    @sservers = @$sservers_ref;
    my %sstatuses;
    foreach my $sserv (@sservers) {
        $sstatuses{$sserv->{internalip}} = $sserv->{status};
    }

    cancel_results();

    # Run one each one in parallel and display the output
    $p = 0;
    foreach $s (@servers) {
        my $host = $s->{'host'};
        next unless ($sstatuses{$host} eq 'running');
        next if ($skip_servers && $host eq $skip_servers);
        push @servs, $host;
        `/usr/bin/mkfifo -m666 "/tmp/OPIPE-$host"` unless (-e "/tmp/OPIPE-$host");
        if (!fork()) {
            # Run the command in a subprocess
            close($rh);
            &remote_foreign_require($host, "webmin", "webmin-lib.pl");
            if ($inst_error_msg) {
                # Failed to contact host ..
                exit;
            }
            # Run the command and capture output
            my $cmd = $command;
            $cmd = $specific_commands->{$host} if ($specific_commands && $specific_commands->{$host});
            if ($cmd) {
                local $q = quotemeta($cmd);
                local $rv = &remote_eval($s->{'host'}, "webmin", "\$x=`($q) </dev/null 2>&1`");
                my $result = &serialise_variable([ 1, $rv ]);
                `/bin/echo "$result" > "/tmp/OPIPE-$s->{'host'}"`;
            }
            exit;
        }
        $p++;
    }
    return qq|{"status": "OK: Ran command on $p servers, $internalip", "servers": | . to_json(\@servs). "}";
}

sub get_results {
    # Get back all the results
    my $servers_ref = shift;
    my $tab = shift || $in{tab};
    my @servers = @$servers_ref;
    `pkill -f "/bin/cat < /tmp/OPIPE"`; # Terminate previous blocking reads that still hang
    $p = 0;
    my $res;
    foreach $d (@servers) {
        my $line = `/bin/cat < /tmp/OPIPE-$d`; # Read from pipe - this blocks, eventually http read will time out
        local $rv = &unserialise_variable($line);
        my $result;
        if (!$line) {
            # Comms error with subprocess
            $res .= qq|<span class="label label-warning">$d failed to run the command for unknown reasons :(</span><br />\n|;
        } elsif (!$rv->[0]) {
            # Error with remote server
            $res .= qq|<span class="label label-warning">$d returned an error $rv->[1]</span><br />\n|;
        } else {
            # Done - show output
            if ($in{tab} eq 'software') {
                $result = &html_escape($rv->[1]);
                chomp $result;
                my $d2 = $d;
                $d2 =~ tr/./-/;
                my $rid = "$tab-result-$d2";
                $rid =~ tr/-/_/;
                my $disp = "display:none; ";
                if ($result =~ /Setting up/) {
                    $res .= qq|<span class="label label-success" style="cursor:pointer;" onclick='\$("#$rid").toggle();'>$d has been upgraded</span>\n|;
                    $res .= qq|<ul><pre id="$rid" style="max-height:160px; font-size:12px; overflow: auto; $disp">$result</pre></ul>\n|;
                } elsif ($result =~ /The following packages/) {
                    $res .= qq|<span class="label label-success upgrade-available" style="cursor:pointer;" onclick='\$("#$rid").toggle();'>$d has software upgrades available</span>\n|;
                    $res .= qq|<ul><pre id="$rid" style="max-height:160px; font-size:12px; overflow: auto; $disp">$result</pre></ul>\n|;
                } else {
                    $res .= qq|<span class="label label-success">$d has no software upgrades available</span><br />\n|;
                }
            } elsif ($in{tab} eq 'storage') {
                $result = $rv->[1];
                my $d2 = $d;
                $d2 =~ tr/./-/;
                if ($result && $result =~ /^[\[\{]/) {
                    my $fs = from_json($result);
                    $res .= qq|<div style="margin-bottom: 20px;">Storage mounted on $d:</div>\n|;
                    foreach my $fs (@{$fs}) {
                    	unless ($fs->{Filesystem} =~ /tmpfs/) {
                            my $fsname = $1 if ($fs->{Filesystem} =~ /\/dev\/(.+)/);
                            my $pclass = "info";
                            my $bsize = '';
                            $pclass = "warning" if ($fs->{'Use%'} > 75);
                            $pclass = "error" if ($fs->{'Use%'} > 90);
                            my @fsizes = (20,40,60,80,100,150,200,400,600,800,1000);
                            my $options = '';
                            $bsize = $fs->{Blocksize} || $fs->{Size};
                            foreach my $size (@fsizes) {
                                $options .= qq|<option value="$size">$size GB</option>| if ($bsize<$size);
                            }
                            if ($fs->{Mounted} eq '/' || !$options) { # We cannot resize root partition
                                $options = ''
                            } else {
                                $bsize = $1 if ($bsize =~ /(\d+)/);
                                my $boption = qq|<option value="$bsize">$bsize GB</option>|;
                                $options = qq|<span class="resize-available glyphicon glyphicon-resize-full" style="margin-left:20px;" aria-hidden="true" id="$fsname"></span> <select onchange='if (\$(this).val()!=$bsize) \$("#$d2-$fsname-resize").val(\$(this).val()); else \$("#$d2-$fsname-resize").val("");'>$boption$options</select>\n|;
                                $options .= <<END
<script>
if (!\$("#$d2-$fsname-resize").length) {
var input = document.createElement("input"); input.type = "hidden"; input.autocomplete = "off"; input.name=input.id="$d2-$fsname-resize"; input.value=""; \$("#storage_form").append(input);
\$(input).addClass("storage_size"); }
</script>
END
                            }
                        	$res .= <<END
<div class="row">
<div class="col-sm-6 col-md-6">
<div class="progress" style="height: 30px; margin-bottom:5px; width:100%; background-color:#CCC; border-radius:5px;" title="$fs->{Filesystem} is mounted on $fs->{Mounted}" rel="tooltip" data-placement="bottom">
  <div class="progress-bar progress-bar-$pclass" role="progressbar" style="width: $fs->{'Use%'};" aria-valuemin="0" aria-valuemax="100">
     <span style="position:absolute; left: 30px; font-size: 15px; margin-top: 8px;"><strong>$fsname:</strong> $fs->{Size}B total, $fs->{'Use%'} used.</span>
  </div>
</div>
</div>
<div class="col-sm-3 col-md-3" style="padding-left:0; margin-bottom:4px;">
$options
</div>
</div>
END
                        }
                    }
                } elsif ($result) {
                    $res .= qq|<span class="label label-success">$d returned:</span><br /><pre>$result</pre>\n|;
                } else {
                    $res .= qq|<span class="label label-success">$d did not return anything.</span><br />\n|;
                }
            } else {
                $result = &html_escape($rv->[1]);
                chomp $result;
                my $d2 = $d;
                $d2 =~ tr/./-/;
                my $rid = "$tab-result-$d2";
                $rid =~ tr/-/_/;
                my $disp = ($p==0)?'':"display:none; ";
                if ($result) {
                    $res .= qq|<span class="label label-success" style="cursor:pointer;" onclick='\$("#$rid").toggle();'>$d ran command succesfully</span>\n|;
                    $res .= qq|<ul><pre id="$rid" style="max-height:160px; font-size:12px; overflow: auto; $disp">$result</pre></ul>\n|;
                } else {
                    $res .= qq|<span class="label label-success">$d ran command succesfully</span><br />\n|;
                }
            }
        }
        $p++;
    }
    return $res;
}

sub cancel_results {
    `pkill -f "/bin/cat < /tmp/OPIPE"`; # Terminate previous blocking reads that still hang
}

sub list_simplestack_servers {
    my $json_text = `curl -ks "https://$gw/stabile/servers?system=this"`;
    $json_array_ref = from_json($json_text);
    return $json_array_ref;
}

# Check if a domain name
sub dns_check {
    my $name = shift;
    my $check = `curl -k --max-time 5 "https://$gw/stabile/networks?action=dnscheck\&name=$name"`;
    return ($check && $check =~ /Status=OK/);
}

1;
