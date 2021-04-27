#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license

package Stabile::Nodes;

# use LWP::Simple;
use Error qw(:try);
use File::Basename;
use Config::Simple;
use lib dirname (__FILE__);
use Stabile;


my $backupdir = $Stabile::config->get('STORAGE_BACKUPDIR') || "/mnt/stabile/backups";
my $tenderpaths = $Stabile::config->get('STORAGE_POOLS_LOCAL_PATHS') || "/mnt/stabile/images";
my @tenderpathslist = split(/,\s*/, $tenderpaths);
my $tendernames = $Stabile::config->get('STORAGE_POOLS_NAMES') || "Standard storage";
my @tendernameslist = split(/,\s*/, $tendernames);
$amtpasswd = $Stabile::config->get('AMT_PASSWD') || "";
$brutalsleep = $Stabile::config->get('BRUTAL_SLEEP') || "";

$uiuuid;
$uistatus;
$help = 0; # If this is set, functions output help

our %ahash; # A hash of accounts and associated privileges current user has access to
#our %options=();
# -a action -h help -u uuid -m match pattern -f full list, i.e. all users
# -v verbose, include HTTP headers -s impersonate subaccount -t target [uuid or image]
# -g args to gearman task
#Getopt::Std::getopts("a:hfu:g:m:vs:t:", \%options);

try {
    Init(); # Perform various initalization tasks
    if (!$isadmin && $action ne "list" && $action ne "listnodeidentities" && $action ne "listlog" && $action ne "help") {return "Status=Error Insufficient privileges for $user ($tktuser)\n"};
    process() if ($package);

} catch Error with {
    my $ex = shift;
    print header('text/html', '500 Internal Server Error') unless ($console);
    if ($ex->{-text}) {
        print "Got error: ", $ex->{-text}, " on line ", $ex->{-line}, " in file ", $ex->{-file}, "\n";
    } else {
        print "Status=ERROR\n";
    }
} finally {
};

1;

sub getObj {
    my %h = %{@_[0]};
    $console = 1 if $h{"console"};
    $api = 1 if $h{"api"};
    $action = $action || $h{'action'};
    my $mac = $h{"uuid"} || $h{"mac"};
    my $dbobj = $register{$mac} || {};
    my $obj;
    my $status = $dbobj->{'status'} || $h{"status"}; # Trust db status if it exists
    if ($action =~ /all$|configurecgroups/) {
        $obj = \%h;
    } else {
        return 0 unless (($mac && length $mac == 12) );
        my $name = $h{"name"} || $dbobj->{'name'};
        $obj = $dbobj;
        $obj->{"name"} = $name if ($name);
        $obj->{"status"} = $status if ($status);
    }
    return $obj;
}

sub Init {
    # Tie database tables to hashes
    unless ( tie(%register,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac'}, $Stabile::dbopts)) ) {return "Unable to access nodes register"};
    unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username'}, $Stabile::dbopts)) ) {return "Unable to access user register"};

    # simplify globals initialized in Stabile.pm
    $tktuser = $tktuser || $Stabile::tktuser;
    $user = $user || $Stabile::user;

    # Create aliases of functions
    *header = \&CGI::header;

    *Fullstats = \&Stats;
    *Fullstatsb = \&Stats;

    *do_help = \&action;
    *do_remove = \&do_delete;
    *do_tablelist = \&do_list;
    *do_listnodes = \&do_list;
    *do_stats = \&action;
    *do_fullstats = \&privileged_action;
    *do_fullstatsb = \&privileged_action;
    *do_updateamtinfo = \&privileged_action;
    *do_configurecgroups = \&privileged_action;
    *do_gear_updateamtinfo = \&do_gear_action;
    *do_gear_fullstats = \&do_gear_action;
    *do_gear_fullstatsb = \&do_gear_action;
    *do_gear_configurecgroups = \&do_gear_action;

}

sub do_listnodeidentities {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
List the identities supported by this engine.
END
    }
    unless ( tie(%idreg,'Tie::DBI', Hash::Merge::merge({table=>'nodeidentities', key=>'identity'}, $Stabile::dbopts)) ) {return "Unable to access identity register"};
    my @idvalues = values %idreg;
    my @newidvalues;
    my $i = 1;
    foreach my $val (@idvalues) {
        my %h = %$val;
        if ($h{'identity'} eq "default") {$h{'id'} = "0";}
        else {$h{'id'} = "$i"; $i++;};
        push @newidvalues,\%h;
    }
    untie %idreg;
    my $json_text = to_json(\@newidvalues, {pretty=>1});
    $postreply = qq|{"identifier": "id", "label": "name", "items": $json_text }|;
    return $postreply;
}

sub do_terminal {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Open direct ssh access to specified node through shellinabox.
END
    }
    my $mac = $uuid || $params{'mac'} || $obj->{'mac'};
    if ($mac && $isadmin) {
        my $macip = $register{$mac}->{'ip'};
        my $macname = $register{$mac}->{'name'};
        my $terminalcmd = qq[/usr/share/stabile/shellinabox/shellinaboxd --cgi -t --css=$Stabile::basedir/static/css/shellinabox.css --debug -s "/:www-data:www-data:HOME:/usr/bin/ssh -l irigo -i /var/www/.ssh/id_rsa_www -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no $macip" 2>/tmp/sib.log];
        my $cmdout = `$terminalcmd`;
        $cmdout =~ s/<title>.+<\/title>/<title>Node: $macname<\/title>/;
        $cmdout =~ s/:(\d+)\//\/shellinabox\/$1\//g;
        $postreply = $cmdout;
    } else {
        $postreply = "Status=ERROR Unable to open terminal: $Stabile::basedir\n";
    }
    return $postreply;
}

sub do_save {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
PUT:name:
Set the name of node.
END

    }
}

sub do_sol {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Open serial over lan access to specified node through shellinabox.
END
    }
    my $mac = $uuid || $params{'mac'} || $obj->{'mac'};
    if ($mac && $isadmin) {
        my $solcmd;
        my $macname = $register{$mac}->{'name'};
        my $amtip = $register{$mac}->{'amtip'};
        my $ipmiip = $register{$mac}->{'ipmiip'};
        if ($amtip && $amtip ne '--') {
            `pkill -f 'amtterm $amtip'`;
            $amtpasswd =~ s/\!/\\!/;
            $solcmd = "AMT_PASSWORD='$amtpasswd' /usr/bin/amtterm $amtip";
        } elsif ($ipmiip && $ipmiip ne '--') {
            `ipmitool -I lanplus -H $ipmiip -U ADMIN -P ADMIN sol deactivate`;
            $solcmd .= "ipmitool -I lanplus -H $ipmiip -U ADMIN -P ADMIN sol activate";
        }
        if ($solcmd ) {
            my $terminalcmd = qq[/usr/share/stabile/shellinabox/shellinaboxd --cgi -t --css=$Stabile::basedir/static/css/shellinabox.css --debug -s "/:www-data:www-data:HOME:$solcmd" 2>/tmp/sib.log];
         #   print header(), "Got sol $terminalcmd\n"; exit;
            my $cmdout = `$terminalcmd`;
            $cmdout =~ s/<title>.+<\/title>/<title>SOL: $macname<\/title>/;
            $cmdout =~ s/:(\d+)\//\/shellinabox\/$1\//g;
            $postreply = $cmdout;
        } else {
            $postreply = "Status=ERROR This node does not support serial over lan\n";
        }
    } else {
        $postreply = "Status=ERROR You must specify mac address and have admin rights.\n";
    }
    return $postreply;
}

sub do_maintenance {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Puts the specified node in maintenance mode. A node in maintenance mode is not available for starting new servers.
END
    }
    my $status = $obj->{'status'};
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    my $dbstatus = $register{$mac}->{'status'};
    if ($dbstatus eq "running") {
        $uistatus = "maintenance";
        $uiuuid = $mac;
        $register{$mac}->{'status'} = $uistatus;
        $register{$mac}->{'maintenance'} = 1;
        my $logmsg = "Node $mac marked for $action";
        $main::syslogit->($user, "info", $logmsg);
        $postreply .= "Status=$uistatus OK putting $name in maintenance mode\n";
        $main::updateUI->({tab=>"nodes", user=>$user, uuid=>$uiuuid, status=>$uistatus});
    } else {
        $postreply .= "Status=ERROR Cannot $action a $status node\n";
    }
    return $postreply;
}

sub do_sleep {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Put an idle node to sleep. S3 sleep must be supported and enabled.
END
    }
    my $status = $obj->{'status'};
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    my $dbstatus = $register{$mac}->{'status'};

    if ($status eq "running" && $register{$mac}->{'vms'}==0) {
        my $logmsg = "Node $mac marked for $action ";
        $uiuuid = $mac;
        if ($brutalsleep && (
            ($register{$mac}->{'amtip'} && $register{$mac}->{'amtip'} ne '--')
                || ($register{$mac}->{'ipmiip'} && $register{$mac}->{'ipmiip'} ne '--')
        )) {
            my $sleepcmd;
            $uistatus = "asleep";
            if ($register{$mac}->{'amtip'} && $register{$mac}->{'amtip'} ne '--') {
                $sleepcmd = "echo 'y' | AMT_PASSWORD='$amtpasswd' /usr/bin/amttool $register{$mac}->{'amtip'} powerdown";
            } else {
                $uistatus = "asleep";
                $sleepcmd = "ipmitool -I lanplus -H $register{$mac}->{'ipmiip'} -U ADMIN -P ADMIN power off";
            }
            $uiuuid = $mac;
            $register{$mac}->{'status'} = $uistatus;
            $logmsg .= `$sleepcmd`;
        } else {
            $uistatus = "sleeping";
            my $tasks = $register{$mac}->{'tasks'};
            $register{$mac}->{'tasks'} = $tasks . $action . " $user \n";
            $register{$mac}->{'action'} = "";
        }
        $register{$mac}->{'status'} = $uistatus;
        $logmsg =~ s/\n/ /g;
        $main::syslogit->($user, "info", $logmsg);
        $postreply .= "Status=$uistatus OK putting $name to sleep\n";
    } else {
        $postreply .= "Status=ERROR Cannot $action a $dbstatus node or a node with running VMs\n";
    }
    return $postreply;
}

sub do_wake {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Tries to wake or start a node by sending a wake-on-LAN magic packet to the node.
END
    }
    my $status = $obj->{'status'};
    my $mac = $obj->{'mac'} || $uuid;
    my $name = $obj->{'name'};
    my $wakecmd;

    if (1 || $status eq "asleep" || $status eq "inactive" || $status eq "shutdown") {
        $uistatus = "waking";
        my $logmsg = "Node $mac marked for wake ";
        if ($brutalsleep && (
            ($register{$mac}->{'amtip'} && $register{$mac}->{'amtip'} ne '--')
                || ($register{$mac}->{'ipmiip'} && $register{$mac}->{'ipmiip'} ne '--')
        )) {
            if ($register{$mac}->{'amtip'} && $register{$mac}->{'amtip'} ne '--') {
                $wakecmd = "echo 'y' | AMT_PASSWORD='$amtpasswd' /usr/bin/amttool $register{$mac}->{'amtip'} powerup pxe";
            } else {
                $wakecmd = "ipmitool -I lanplus -H $register{$mac}->{'ipmiip'} -U ADMIN -P ADMIN power on";
            }
            $register{$mac}->{'status'} = $uistatus;
            $logmsg .= `$wakecmd`;
        } else {
            $realmac = substr($mac,0,2).":".substr($mac,2,2).":".substr($mac,4,2).":".substr($mac,6,2).":".substr($mac,8,2).":".substr($mac,10,2);
            my $broadcastip = $register{$mac}->{'ip'};
            $broadcastip =~ s/\.\d{1,3}$/.255/;
            $broadcastip = $broadcastip || '10.0.0.255';
            $wakecmd = "/usr/bin/wakeonlan -i $broadcastip $realmac";
            $logmsg .= `$wakecmd`;
        }
        $logmsg =~ s/\n/ /g;
        $main::syslogit->($user, "info", $logmsg);
        $register{$mac}->{'status'} = 'waking';
        $postreply .= "Status=$uistatus OK $uistatus $name ($mac)\n";
    } else {
        $postreply .= "Status=ERROR Cannot $action up a $status node\n";
    }
    return $postreply;
}

sub do_carryon {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Puts the specified node out of maintenance mode. A node in maintenance mode is not available for starting new servers.
END
    }
    my $status = $obj->{'status'};
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    my $dbstatus = $register{$mac}->{'status'};
    if ($dbstatus eq "maintenance") {
        $uistatus = "running";
        $uiuuid = $mac;
        $register{$mac}->{'status'} = $uistatus;
        $register{$mac}->{'maintenance'} = 0;
        my $logmsg = "Node $mac marked for $action";
        $main::syslogit->($user, "info", $logmsg);
        $postreply .= "Status=$uistatus OK putting $name out of maintenance mode\n";
        $main::updateUI->({tab=>"nodes", user=>$user, uuid=>$uiuuid, status=>$uistatus});
    } else {
        $postreply .= "Status=ERROR Cannot $action a $status node\n";
    }
    return $postreply;
}

sub do_reboot {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Reboots the specified node.
END
    }
    my $status = $obj->{'status'};
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    if ($status eq "running" && $register{$mac}->{'vms'}==0) {
        $uistatus = "rebooting";
        $uiuuid = $mac;
        my $tasks = $register{$mac}->{'tasks'};
        $register{$mac}->{'tasks'} = $tasks . $action . " $user\n";
        $register{$mac}->{'action'} = "";
        $register{$mac}->{'status'} = $uistatus;
        my $logmsg = "Node $mac marked for $action";
        $main::syslogit->($user, "info", $logmsg);
        $postreply = "Status=$uistatus OK rebooting $name\n";
    } else {
        $postreply = "Status=ERROR Cannot $action a $status node or a node with running VMs\n";
    }
    return $postreply;
}

sub do_halt {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Halts the specified node.
END
    }
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    $uistatus = "halting";
    $uiuuid = $mac;
	my $tasks = $register{$mac}->{'tasks'};
	$register{$mac}->{'tasks'} = $tasks . $action . " $user\n";
	$register{$mac}->{'action'} = "";
	$register{$mac}->{'status'} = $uistatus;
	my $logmsg = "Node $mac marked for $action";
	$main::syslogit->($user, "info", $logmsg);
	$postreply .= "Status=$uistatus OK $uistatus $name\n";
    return $postreply;
}

sub do_delete {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Deletes a node. Use if a node has been physically removed from engine.
END
    }
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    if ($status ne "running" && $status ne "maintenance" && $status ne "sleeping"
        && $status ne "reload" && $status ne "reloading") {
        if ($register{$mac}) {
            $uistatus = "deleting";
            $uiuuid = $mac;
            my $logmsg = "Node $mac marked for deletion";
            $main::syslogit->($user, "info", $logmsg);
            $postreply .= "Status=$uistatus OK deleting $name ($mac)\n";
            $mac =~ /(\w\w)(\w\w)(\w\w)(\w\w)(\w\w)(\w\w)/;
            my $file = "/mnt/stabile/tftp/pxelinux.cfg/01-$1-$2-$3-$4-$5-$6";
            unlink $file if (-e $file);
            delete $register{$mac};
            $main::updateUI->({tab=>"nodes", user=>$user});
        } else {
            $postreply .= "Status=ERROR Node $mac not found\n" . Dumper($obj);
        }
    } else {
        $postreply .= "Status=ERROR Cannot $action a $status node\n";
    }
    return $postreply;
}

sub do_shutdown {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Shuts down the specified node.
END
    }
    my $status = $obj->{'status'};
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    if ($status eq "running" && $register{$mac}->{'vms'}==0) {
        $uistatus = "shuttingdown";
        $uiuuid = $mac;
        my $tasks = $register{$mac}->{'tasks'};
        $register{$mac}->{'tasks'} = $tasks . $action . " $user\n";
        $register{$mac}->{'action'} = "";
        $register{$mac}->{'status'} = $uistatus;
        my $logmsg = "Node $mac marked for $action";
        $main::syslogit->($user, "info", $logmsg);
        $postreply .= "Status=$uistatus OK shutting down $name\n";
    } else {
        $postreply .= "Status=ERROR Cannot $action a $status node or a node with running VMs\n";
    }
}

sub do_evacuate {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Evacuates the specified node, i.e. tries to migrate all servers away from the node. Node must be in maintenance mode.
END
    }
    my $status = $obj->{'status'};
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    my $dbstatus = $register{$mac}->{'status'};
    if ($dbstatus eq "maintenance" || $dbstatus eq "running") {
        $register{$mac}->{'status'} = 'maintenance' if ($dbstatus eq "running");
        $uistatus = "evacuating";
        $uiuuid = $mac;
        unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};

        my $actionstr;
        my $i = 0;
        foreach my $dom (keys %domreg) {
            if ($domreg{$dom}->{'mac'} eq $mac &&
                ($domreg{$dom}->{'status'} eq 'running' || $domreg{$dom}->{'status'} eq 'paused')) {
                $actionstr .= qq[{"uuid": "$dom", "action": "move", "console": 1}, ];
                $i++;
            }
        }
        untie %domreg;
        if ($actionstr) {
            $actionstr = substr($actionstr,0,-2);
            my $postdata = URI::Escape::uri_escape(
                qq/{"identifier": "uuid", "label": "uuid", "items":[$actionstr]}/
            );
            my $res;
            if ($console) {
                $res = `REMOTE_USER=$user $Stabile::basedir/cgi/servers.cgi $postdata`;
                $postreply .= "Stroke=OK Move: $res\n";
            } else {
                $res = `/usr/bin/ssh -l irigo -i /var/www/.ssh/id_rsa_www -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no localhost REMOTE_USER=$user $Stabile::basedir/cgi/servers.cgi $postdata`;
                # $postreply .= "Stroke=OK Now moving: $res\n";
            }
            $res =~ s/\n/ - /g;
            my $logmsg = "Node $mac marked for $action: $res";
            $main::syslogit->($user, "info", $logmsg);
            $postreply .= "Status=OK Node $name marked for evacuation ($i servers)\n";
        } else {
            $postreply .= "Status=OK No servers found to evacaute\n";
        }
    } else {
        $postreply .= "Status=ERROR Cannot $action a $status node (not in maintenance, not running)\n";
    }
    return $postreply;
}


sub do_reset {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Resets the specified node.
END
    }
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    my $dbstatus = $register{$mac}->{'status'};
    if (($dbstatus eq "maintenance" && $register{$mac}->{'vms'} == 0)
        || $dbstatus eq "inactive"
        || $dbstatus eq "waking"
        || $dbstatus eq "sleeping"
        || $dbstatus eq "shuttingdown"
        || $dbstatus eq "shutdown"
        || $dbstatus eq "joining"
    ) {
        my $resetcmd;
        if ($register{$mac}->{'amtip'} && $register{$mac}->{'amtip'} ne '--') {
            $uistatus = "reset";
            $resetcmd = "echo 'y' | AMT_PASSWORD='$amtpasswd' /usr/bin/amttool $register{$mac}->{'amtip'} reset bios";
        } elsif ($register{$mac}->{'ipmiip'} && $register{$mac}->{'ipmiip'} ne '--') {
            $uistatus = "reset";
            $resetcmd = "ipmitool -I lanplus -H $register{$mac}->{'ipmiip'} -U ADMIN -P ADMIN power reset";
        } else {
            $postreply .= "Status=ERROR This node does not support hardware reset\n";
        }
        if ($uistatus eq 'reset') {
            $uiuuid = $mac;
            $register{$mac}->{'status'} = $uistatus;
            my $logmsg = "Node $mac marked for $action";
            $logmsg .= `$resetcmd`;
            $logmsg =~ s/\n/ /g;
            $main::syslogit->($user, "info", $logmsg);
            $postreply .= "Stroke=$uistatus OK resetting $name ";
        }
    } else {
        $postreply .= "Status=ERROR Cannot $action a $dbstatus node\n";
    }
    return $postreply;
}

sub do_unjoin {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Disassciates a node from the engine and reboots it. After rebooting, it will join the engine with the default
node identity
END
    }
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    my $dbstatus = $register{$mac}->{'status'};
    if ($dbstatus eq "running" && $register{$mac}->{'vms'}==0) {
        $uistatus = "unjoining";
        $uiuuid = $mac;
        my $tasks = $register{$mac}->{'tasks'};
        $register{$mac}->{'tasks'} = $tasks . $action . " $user\n";
        $register{$mac}->{'action'} = "";
        $register{$mac}->{'status'} = $uistatus;
        my $logmsg = "Node $mac marked for $action";
        $main::syslogit->($user, "info", $logmsg);
        $postreply .= "Status=$uistatus OK unjoining $name\n";
    } else {
        $postreply .= "Status=ERROR Cannot $action a $dbstatus node or a node with running VMs\n";
    }
    return $postreply;
}

sub do_wipe {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac:
Erases a node's harddrive and formats it with either ext4 or zfs, depending on settings.
Only allowed if /mnt/stabile/node is empty.
END
    }
    my $mac = $obj->{'mac'};
    my $name = $obj->{'name'};
    unless ($register{$mac}) {
        $postreply .= "Status=ERROR Please specify a valid mac.\n";
        return $postreply;
    }
    my $dbstatus = $register{$mac}->{'status'};
    if ($dbstatus eq "running" && $register{$mac}->{'vms'}==0) {
        $uistatus = "wiping";
        $uiuuid = $mac;
        my $tasks = $register{$mac}->{'tasks'};
        $register{$mac}->{'tasks'} = $tasks . $action . " $user\n";
        $register{$mac}->{'action'} = "";
        $register{$mac}->{'status'} = $uistatus;
        my $logmsg = "Node $mac marked for $action";
        $main::syslogit->($user, "info", $logmsg);
        $postreply .= "Status=$uistatus OK wiping $name\n";
    } else {
        $postreply .= "Status=ERROR Cannot $action a $dbstatus node or a node with running VMs\n";
    }
    return $postreply;
}

sub do_setdefaultnodeidentity {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:hid,sleepafter:
Sets the default identity a node should boot as. [sleepafter] is in seconds, [hid] is [name] of one the alternatives listed by [listnodeidentities].
END
    }
    my $hid = $params{'hid'};
    my $sleepafter = $params{'sleepafter'};
    unless ($hid) {return "Status=ERROR No identity selected\n"};
    unless ( tie(%idreg,'Tie::DBI', Hash::Merge::merge({table=>'nodeidentities', key=>'name'}, $Stabile::dbopts)) ) {return "Unable to access id register"};
    my @idvalues = values %idreg;
    foreach my $val (@idvalues) {
        my $identity = $val->{'name'};
        if ($identity eq $hid) {$identity = "default"}
        $idreg{$val->{'name'}} = {
            identity=>$identity,
            sleepafter=>int($sleepafter)
        }
    }
    tied(%idreg)->commit;
    untie %idreg;
    $postreply = "Status=OK Set $hid as new default identity, sleeping after $sleepafter minutes\n";
}

sub do_listlog {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Lists the last 200 lines from the local activity log file.
END
    }
    $postreply = header("text/plain");
    if ($isadmin) {
        $postreply .= `tail -n 200 $main::logfile`;
    } else {
        $postreply .= `tail -n 200 $main::logfile | grep ': $user :'`;
    }
}

sub do_clearlog {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Clear the local activity log file.
END
    }
    `> $main::logfile`;
    # unlink $logfile;
    $postreply = header("text/plain");
    $postreply .=  "Status=OK Log cleared\n";
    return $postreply;
}

sub do_updateregister {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Updates the node register.
END
    }
    updateRegister();
    $postreply = "Stream=OK Updated node register for all users\n";
    return $postreply;
}

sub do_reload {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac,nodeaction:
Reload configuration on the specified node or perform specified action.
END
    }
    my $status = $obj->{'status'};
    my $mac = $obj->{'mac'};
    my $nodeaction = "reload" || $obj->{'nodeaction'};
    if ($status eq "running") {
        $uistatus = "reloading";
        $uiuuid = $mac;
        my $tasks = $register{$mac}->{'tasks'};
        $register{$mac}->{'tasks'} = $tasks . $nodeaction . " $user\n";
        $register{$mac}->{'action'} = "";
        $register{$mac}->{'status'} = $uistatus;
        my $logmsg = "Node $mac marked for $action";
        $main::syslogit->($user, "info", $logmsg);
        $postreply .= "Status=$uistatus OK reloading $name\n";
    }
    else {
        $postreply .= "Status=ERROR Cannot $action a $status node\n";
    }
    return $postreply;
}

sub do_reloadall {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:nodeaction:
Reload configuration on all nodes. Alternatively specify a "nodeaction" to have it executed on all nodes.
Currently supported nodeactions: CGLOAD [reload cgroup configuration]
END
    }
    my $nodeaction = $obj->{'nodeaction'} || "reload";
    my @regvalues = values %register;
    # Only include pistons we have heard from in the last 20 secs
    foreach $val (@regvalues) {
        my $curstatus =  $val->{'status'};
        my $mac = $val->{'mac'};
        my $name = $val->{'name'};
        if ($curstatus eq "running" || $curstatus eq "maintenance") {
            $uistatus = "reloading";
            $uiuuid = $mac;
            my $tasks = $register{$mac}->{'tasks'};
            $register{$mac}->{'tasks'} = $tasks . $nodeaction . " $user\n";
            $register{$mac}->{'action'} = "";
            $register{$mac}->{'status'} = $uistatus;
            my $logmsg = "Node $mac marked for $nodeaction";
            $main::syslogit->($user, "info", $logmsg);
            $postreply .= "Status=OK $uistatus $name\n";
        } else {
            $postreply .= "Status=OK Node $mac ($register->{$mac}) is $register{$mac}->{'status'} not reloading\n";
        }
    }
    return $postreply;
}

sub do_rebootall {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Reboot all active nodes.
END
    }
    my @regvalues = values %register;
# Only include pistons we have heard from in the last 20 secs
    foreach $val (@regvalues) {
        my $curstatus =  $val->{'status'};
        my $mac = $val->{'mac'};
        $action = "reboot";
        my $name = $val->{'name'};
        my $identity = $val->{'identity'};
        if (($curstatus eq "running" || $curstatus eq "maintenance") && $identity ne 'local_kvm')
        {
              $uistatus = "rebooting";
              $uiuuid = $mac;
              my $tasks = $register{$mac}->{'tasks'};
              $register{$mac}->{'tasks'} = $tasks . $action . " $user\n";
              $register{$mac}->{'action'} = "";
              $register{$mac}->{'status'} = $uistatus;
              my $logmsg = "Node $mac marked for $action";
              $main::syslogit->($user, "info", $logmsg);
              $postreply .= "Status=OK $uistatus $name\n";
        }
    }
    $postreply = $postreply || "Status=ERROR No active nodes found\n";
    return $postreply;
}

sub do_haltall {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:nowait:
Unceremoniously halt all active nodes.
END
    }
    my @regvalues = values %register;
    my $nowait = $obj->{'nowait'};
# Only include pistons we have heard from in the last 20 secs
    foreach $val (@regvalues) {
        my $curstatus =  $val->{'status'};
        my $identity = $val->{'identity'};
        my $mac = $val->{'mac'};
        $action = "halt";
        my $name = $val->{'name'};
        if (($curstatus eq "running" || $curstatus eq "maintenance") && $identity ne 'local_kvm')
        {
              $uistatus = "halting";
              $uiuuid = $mac;
              my $tasks = $register{$mac}->{'tasks'};
              $register{$mac}->{'tasks'} = $tasks . $action . " $user\n";
              $register{$mac}->{'action'} = "";
              $register{$mac}->{'status'} = $uistatus;
              my $logmsg = "Node $mac marked for $action";
              $main::syslogit->($user, "info", $logmsg);
              $postreply .= "Status=OK $uistatus $name\n";
        }
    }
    unless ($nowait) {
        $postreply .= "Status=OK Waiting up to 100 seconds for running nodes to shut down\n";
        my $livenodes = 0;
        for (my $i; $i<10; $i++) {
            $livenodes = 0;
            do_list();
            foreach $val (@regvalues) {
                my $curstatus =  $val->{'status'};
                my $identity = $val->{'identity'};
                my $mac = $val->{'mac'};
                my $name = $val->{'name'};
                if (($curstatus eq "running" || $curstatus eq "maintenance" || $curstatus eq "halting") && $identity ne 'local_kvm') {
                    $livenodes = 1;
                }
            }
            last unless ($livenodes);
            sleep 10;
        }

    }
    $postreply = $postreply || "Status=ERROR No active nodes found\n";
    return $postreply;
}

sub Updateamtinfo {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Updates info about the nodes' AMT configuration by scanning the network.
END
    }
    $postreply = updateAmtInfo();
    return $postreply;
}

sub Stats {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Collect and show stats for this engine. May also be called as fullstats or fullstatsb (includes backup info).
END
    }
    return "Status=Error Not allowed\n" unless ($isadmin);
    my @regvalues = values %register;
    my %stats;
    my $cpuloadsum = 0;
    my $memtotalsum = 0;
    my $memfreesum = 0;
    my $memusedsum = 0;
    my $corestotal = 0;
    my $vmstotal = 0;
    my $vmvcpustotal = 0;
    my $nodestorfree = 0;
    my $nodestorused = 0;
    my $nodestortotal = 0;
    my $i = 0;

    $Stabile::Systems::user = $user;
    require "$Stabile::basedir/cgi/systems.cgi";
    $Stabile::Systems::console = 1;
    #$console = 1;

    # Only include pistons we have heard from in the last 20 secs
    foreach $val (@regvalues) {
        if ((($val->{'status'} eq "asleep") || ($current_time - ($val->{'timestamp'}) < 20)) && ($val->{'status'} ne "joining") && ($val->{'status'} ne "shutdown") && ($val->{'status'} ne "reboot") ) {
            $cpuloadsum += $val->{'cpuload'} / ($val->{'cpucount'} * $val->{'cpucores'}) if ($val->{'cpucount'}>0);
            $memtotalsum += $val->{'memtotal'};
            $memfreesum += $val->{'memfree'};
            $corestotal += $val->{'cpucount'} * $val->{'cpucores'};
            $vmstotal += $val->{'vms'};
            $vmvcpustotal += $val->{'vmvcpus'};
            $nodestorfree += $val->{'storfree'};
            $nodestortotal += $val->{'stortotal'};
            $readynodes ++ if ($val->{'status'} eq 'running' || $val->{'status'} eq 'maintenance' || $val->{'status'} eq 'asleep');
            $i++;
#        } elsif (($val->{'identity'} ne "local_kvm") &&($val->{'status'} eq 'running' || $val->{'status'} eq 'maintenance')) {
#            $readynodes++;
        }
    }
    $memusedsum = $memtotalsum - $memfreesum;
    $nodestorused = $nodestortotal - $nodestorfree;

    $cpuloadsum = $cpuloadsum / $i if ($i > 0); # Avoid division by zero
    my %avgs = ("cpuloadavg" => $cpuloadsum, "memtotalsum" =>  $memtotalsum, "memfreesum" =>  $memfreesum,
        "nodestotal" => $i,"corestotal" => $corestotal, "readynodes" => $readynodes,
        "vmstotal" => $vmstotal, "vmvcpustotal" => $vmvcpustotal,
        "nodestortotal" => $nodestortotal, "nodestorfree" => $nodestorfree);

    my %storavgs;
    my $stortext;
    my $j = 0;
    push @tenderpathslist, $backupdir;
    push @tendernameslist, "Backup";
    foreach my $storpath (@tenderpathslist) {
        my $storfree = `df $storpath`;
        $storfree =~ m/(\d\d\d\d+)(\s+)(\d\d+)(\s+)(\d\d+)(\s+)(\S+)/i;
        my $stortotal = $1;
        my $storused = $3;
        $storfree = $5;
        $storavgs{$tendernameslist[$j].'-used'} = $storused;
        $storavgs{$tendernameslist[$j].'-total'} = $stortotal;
        $stortext .= $tendernameslist[$j] . ": " .int($storused/1024/1024) . " (" . int($stortotal/1024/1024) . ") GB&nbsp;&nbsp;";
        $j++;
    }

    my %mons;
    my @monservices = ('ping', 'diskspace', 'http', 'https', 'smtp', 'smtps', 'ldap', 'imap', 'imaps', 'telnet');
    if ($action eq "fullstats" || $action eq "fullstatsb") {
        $Stabile::Systems::fulllist = 1;
        %mons = Stabile::Systems::getOpstatus();
        $Stabile::Systems::fulllist = 0;
    }
    if ($action eq "fullstatsb") {
        require "images.cgi";
        $Stabile::Images::isadmin = $isadmin;
        $Stabile::Images::console = 1;
    }
    my @lusers;
    # We use images billing to report storage usage
    unless ( tie(%billingreg,'Tie::DBI', Hash::Merge::merge({table=>'billing_images', key=>'userstoragepooltime'}, $Stabile::dbopts)) ) {return "Unable to access billing register"};
    foreach my $uref (values %userreg) {
        my %uval = %{$uref};

        delete $uval{'password'};
        delete $uval{'lasttkt'};
        delete $uval{'tasks'};

        # Skip if not logged in in 5 days
        # next unless ($uval{'lastlogin'} && ($current_time-$uval{'lastlogin'} < 5 * 86400));
        my @systems = Stabile::Systems::getSystemsListing('arraylist', '', $uval{'username'});
        # Skip if user has no systems
        # next unless (@systems);

        my @returnsystems;
        my $vcpus = 0;
        my $mem = 0;
        my $servers = 0;
        foreach my $sys (@systems) {
            my $sysvcpus = 0;
            my $sysmem = 0;
            my $sysstor = 0;
            my $sysnodestor = 0;
            if ($sys->{'issystem'}) {
                foreach my $dom (@{$sys->{'children'}}) {
                    my $status = $dom->{'status'};
                    if ($status ne 'shutoff' && $status ne 'inactive') {
                        $sysvcpus += $dom->{'vcpu'};
                        $sysmem += $dom->{'memory'};
                    }
                    $sysstor += $dom->{'storage'}/1024/1024;
                    $sysnodestor += $dom->{'nodestorage'}/1024/1024;
                }
            } else {
                my $status = $sys->{'status'};
                if ($status ne 'shutoff' && $status ne 'inactive') {
                    $sysvcpus = $sys->{'vcpu'};
                    $sysmem = $sys->{'memory'};
                }
                $sysstor = $sys->{'storage'}/1024/1024;
                $sysnodestor = $sys->{'nodestorage'}/1024/1024;
            }
            $vcpus += $sysvcpus;
            $mem += $sysmem;
            my $serveruuids = $sys->{'uuid'};
            if ($sys->{'issystem'}) {
                my @suuids;
                foreach my $child (@{$sys->{'children'}}) {
                    push @suuids, $child->{'uuid'};
                };
                $serveruuids = join(', ', @suuids);
            }

            $returnsys = {
                'appid'=>$sys->{'appid'},
                'version'=>$sys->{'version'},
                'managementurl'=>$sys->{'managementurl'},
                'upgradeurl'=>$sys->{'upgradeurl'},
                'terminalurl'=>$sys->{'terminalurl'},
                'master'=>$sys->{'master'},
                'name'=>$sys->{'name'},
                'image'=>$sys->{'image'},
                'status'=>$sys->{'status'},
                'user'=>$sys->{'user'},
                'uuid'=>$sys->{'uuid'},
                'servers'=>($sys->{'issystem'}?scalar @{$sys->{'children'}}:1),
                'serveruuids' => $serveruuids,
                'vcpus' => $sysvcpus,
                'memory' => $sysmem,
                'storage' => $sysstor+0,
                'nodestorage' => $sysnodestor+0,
                'externalips' => $sys->{'externalips'}+0,
                'externalip' => $sys->{'externalip'},
                'internalip' => $sys->{'internalip'}
            };
            $servers += ($sys->{'issystem'}?scalar @{$sys->{'children'}}:1);
            my $monitors;
            my $backups;

            if (%mons || $action eq "fullstatsb") {
                if ($sys->{'issystem'}) {
                    foreach my $dom (@{$sys->{'children'}}) {
                        foreach my $service (@monservices) {
                            my $id = $dom->{'uuid'} . ":$service";
                            if ($mons{$id}) {
                                my $last_status = $mons{$id}->{'last_success'} || $mons{$id}->{'last_failure'};
                                $monitors .= "$dom->{'name'}/$service/$mons{$id}->{'status'}/$last_status, " ;
                            }
                        }
                        if ($action eq "fullstatsb") {
                            my $bups = Stabile::Images::Getserverbackups($dom->{'uuid'});
                            $backups  .= "$bups, " if ($bups);
                        }
                    }
                    $monitors = substr($monitors, 0,-2) if ($monitors);
                    $backups = substr($backups, 0,-2) if ($backups);
                } else {
                    foreach my $service (@monservices) {
                        my $id = $sys->{'uuid'} . ":$service";
                        if ($mons{$id}) {
                            my $last_status = $mons{$id}->{'last_success'} || $mons{$id}->{'last_failure'};
                            $monitors .= "$sys->{'name'}/$service/$mons{$id}->{'status'}/$last_status, ";
                        }
                    }
                    $monitors = substr($monitors, 0,-2) if ($monitors);
                    $backups = Stabile::Images::Getserverbackups($sys->{'uuid'}) if ($action eq "fullstatsb");
                }
                $returnsys->{'monitors'} = $monitors if ($monitors);
                $returnsys->{'backups'} = $backups if ($backups);
            }

            push @returnsystems, $returnsys;
        }
        $uval{'systems'} = \@returnsystems;

        $uval{'nodestorage'} = int($billingreg{"$uval{username}--1-$year-$month"}->{'virtualsize'}/1024/1024) if ($billingreg{"$uval{username}--1-$year-$month"});
        my $stor = 0;
        for (my $i=0; $i <= scalar @tenderpathslist; $i++) {
            $stor += $billingreg{"$uval{username}-$i-$year-$month"}->{'virtualsize'} if ($billingreg{"$uval{username}-$i-$year-$month"});
        }
        $uval{'storage'} = int($stor/1024/1024);
        $uval{'vcpu'} = $vcpus;
        $uval{'memory'} = $mem;
        $uval{'servers'} = $servers;

        push @lusers, \%uval;
    }
    untie %billingreg;
    my $ver = `cat /etc/stabile/version`; chomp $ver;

    $stortext .= "Nodes: " . int($nodestorused/1024/1024) . " (" . int($nodestortotal/1024/1024) . ") GB";
    $stats{'status'} = ($readynodes>0?'ready':'nonodes');
    $stats{'storavgs'} = \%storavgs;
    $stats{'avgs'} = \%avgs;
    $stats{'users'} = \@lusers;
    $stats{'stortext'} = $stortext;
    # $stats{'version'} = $version;
    $stats{'version'} = $ver;

    my $json_text = to_json(\%stats, {pretty=>1});
    $json_text =~ s/\x/ /g;
    $json_text =~ s/null/""/g;
    #$postreply = header("application/json") unless ($console);
    $postreply .= $json_text;
    return $postreply;
}

sub do_list {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
List the nodes running this engine.
END
    }
    if ($isadmin || index($privileges,"n")!=-1) {
        my @regvalues = values %register;
        my @curregvalues;
        # Only include pistons we have heard from in the last 20 secs
        foreach $valref (@regvalues) {
            my $curstatus =  $valref->{'status'};
            if (
                ($current_time - ($valref->{'timestamp'}) > 20)
                    && ($curstatus ne "joining") && ($curstatus ne "shutdown") && ($curstatus ne "reboot")
                    && ($curstatus ne "asleep") && ($curstatus ne "waking") && ($curstatus ne "sleeping")
            ) {$valref->{'status'} = "inactive"};

            $valref->{'name'} = $valref->{'mac'} unless ($valref->{'name'} && $valref->{'name'} ne '--');
            my %val = %{$valref}; # Deference and assign to new ass array, effectively cloning object
            # %{$valref}->{'cpucores'}  is the same as $valref->{'cpucores'};
            # These values should be sent as numbers
            $val{'cpucores'} += 0;
            $val{'cpucount'} += 0;
            $val{'memfree'} += 0;
            $val{'memtotal'} += 0;
            $val{'storfree'} += 0;
            $val{'stortotal'} += 0;
            $val{'vms'} += 0;
            $val{'cpuload'} += 0;

            push @curregvalues,\%val ;
        }

        # Sort @curregvalues
        my $sort = 'name';
        $sort = $2 if ($uripath =~ /sort\((\+|\-)(\S+)\)/);
        my $reverse;
        $reverse = 1 if ($1 eq '-');
        if ($reverse) { # sort reverse
            if ($sort =~ /cpucores|cpucount|memfree|memtotal|vms|cpuload/) {
                @curregvalues = (sort {$b->{$sort} <=> $a->{$sort}} @curregvalues); # Sort as number
            } else {
                @curregvalues = (sort {$b->{$sort} cmp $a->{$sort}} @curregvalues); # Sort as string
            }
        } else {
            if ($sort =~ /cpucores|cpucount|memfree|memtotal|vms|cpuload/) {
                @curregvalues = (sort {$a->{$sort} <=> $b->{$sort}} @curregvalues); # Sort as number
            } else {
                @curregvalues = (sort {$a->{$sort} cmp $b->{$sort}} @curregvalues); # Sort as string
            }
        }

        if ($action eq 'tablelist') {
            my $t2 = Text::SimpleTable->new(14,20,14,10,5,5,12,7);
            $t2->row('mac', 'name', 'ip', 'identity', 'cores', 'vms', 'memfree', 'status');
            $t2->hr;
            my $pattern = $options{m};
            foreach $rowref (@curregvalues){
                if ($pattern) {
                    my $rowtext = "$rowref->{'mac'} $rowref->{'name'} $rowref->{'ip'} $rowref->{'identity'} "
                        . "$rowref->{'vms'} $rowref->{'memfree'} $rowref->{'status'}";
                    $rowtext .= " " . $rowref->{'mac'} if ($isadmin);
                    next unless ($rowtext =~ /$pattern/i);
                }
                $t2->row($rowref->{'mac'}, $rowref->{'name'}, $rowref->{'ip'}, $rowref->{'identity'}, $rowref->{'cpucores'},
                    $rowref->{'vms'}, $rowref->{'memfree'}, $rowref->{'status'});
            }
            $postreply .= header("text/plain") unless ($console);
            $postreply .= $t2->draw;
        } elsif ($console) {
            $postreply = Dumper(\@curregvalues);
        } else {
            my $json_text = to_json(\@curregvalues, {pretty=>1});
            $json_text =~ s/""/"--"/g;
            $json_text =~ s/null/"--"/g;
            $json_text =~ s/\x/ /g;
            $postreply .= qq|{"identifier": "mac", "label": "name", "items":| if ($action && $action ne 'list');
            $postreply .= $json_text;
            $postreply .= "}" if ($action && $action ne 'list');
        }
    } else {
        $postreply .= q|{"identifier": "mac", "label": "name", "items":| if ($action && $action ne 'list');
        $postreply .= "[]";
        $postreply .= "}" if ($action && $action ne 'list');
    }
    return $postreply;
}

sub do_uuidlookup {
    if ($help) {
        return <<END
GET:uuid:
Simple action for looking up a uuid or part of a uuid and returning the complete uuid.
END
    }

    my $u = $options{u};
    $u = $params{'uuid'} unless ($u || $u eq '0');
    my $ruuid;
    if ($u || $u eq '0') {
        foreach my $uuid (keys %register) {
            if ($uuid =~ /^$u/ || $register{$uuid}->{'name'} =~ /^$u/) {
                return "$uuid\n";
            }
        }
    }
}

sub do_uuidshow {
    if ($help) {
        return <<END
GET:uuid:
Simple action for showing a single network.
END
    }
    my $u = $options{u};
    $u = $params{'uuid'} unless ($u || $u eq '0');
    if ($u || $u eq '0') {
        foreach my $uuid (keys %register) {
            if ($uuid =~ /^$u/) {
                my %hash = %{$register{$uuid}};
                delete $hash{'action'};
                my $dump = Dumper(\%hash);
                $dump =~ s/undef/"--"/g;
                return $dump;
            }
        }
    }
}

# Print list of available actions on objects
sub do_plainhelp {
    my $res;
    $res .= header('text/plain') unless $console;
    $res .= <<END
* reboot: Reboots a node
* shutdown: Shuts down a node
* unjoin: Disassciates a node from the engine and reboots it. After rebooting, it will join the engine with the default
node identity
* delete: Deletes a node. Use if a node has been physically removed from engine
* sleep: Puts an idle node to sleep. S3 sleep must be supported and enabled
* wake: Tries to wake or start a node by sending a wake-on-LAN magic packet to the node.
* evacuate: Tries to live-migrate all running servers away from node
* maintenance: Puts the node in maintenance mode. A node in maintenance mode is not available for starting new servers.
* carryon: Puts a node out of maintenance mode.
* reload: Reloads the movepiston daemon on the node.

END
;
}


sub updateRegister {
    my @regvalues = values %register;
# Mark pistons we haven't heard from in the last 20 secs as inactive
    foreach $valref (@regvalues) {
        my $curstatus =  $valref->{'status'};
        if (
            ($current_time - ($valref->{'timestamp'}) > 20)
            && ($curstatus ne "joining") && ($curstatus ne "shutdown") && ($curstatus ne "reboot")
            && ($curstatus ne "asleep") && ($curstatus ne "waking") && ($curstatus ne "sleeping")
        ) {
            $valref->{'status'} = 'inactive';
            print "Marking node as inactive\n";
            if ($curstatus ne 'inactive') {
                $main::updateUI->({tab=>'nodes', user=>$user, uuid=>$valref->{'mac'}, status=>'inactive'});
            }
        }
    }
}

sub trim {
   my $string = shift;
   $string =~ s/^\s+|\s+$//g;
   return $string;
}

sub updateAmtInfo {
    my @vals = values(%register);
    if (scalar @vals == 1 && $vals[0]->{identity} eq 'local_kvm') {
        return "Status=OK Only local node registered - not scanning for AMT\n"
    }
    my $amtinfo = `/usr/bin/nmap -n -v --send-ip -Pn -p 16992 10.0.0.*`;
    my $match;
    my %macs;
    my $amtip;
    my $res;
    foreach my $line (split /\n/, $amtinfo) {
        if ($line =~ /16992\/tcp open/) {
            $match = 1;
        } elsif ($line =~ /Nmap scan report for (\S+)/) {
            $amtip = $1;
        } elsif ($line =~ /Host (\S+) is up/) {
            $amtip = $1;
        }
        if ($match && $line =~ /MAC Address: (\S+)/) {
            my $amtmac = $1;
            $amtmac =~ tr/://d;
            $macs{$amtmac} = 1;
            $match = 0;
            $res .= "Status=OK Found $amtmac with $amtip\n";
            $register{$amtmac}->{'amtip'} = $amtip if ($register{$amtmac});
        }
    };
    if (%macs) {
        my $n = scalar values %macs;
        $res .= "Status=OK Found $n nodes with AMT enabled\n";
    } else {
        $res .= "Status=OK Could not find any nodes with AMT enabled\n";
    }
    return $res;
}

sub Configurecgroups {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Parse Stabile config nodeconfig.cfg and configure /etc/cgconfig.conf for all known node roots.
END
    }

    unless ( tie(%idreg,'Tie::DBI', Hash::Merge::merge({table=>'nodeidentities',key=>'identity',CLOBBER=>3}, $Stabile::dbopts)) ) {return "Unable to access id register"};
    my @noderoots;
    # Build hash of known node roots
    foreach my $valref (values %idreg) {
        my $noderoot = $valref->{'path'} . "/casper/filesystem.dir";
        next if ($noderoots{$noderoot}); # Node identities may share basedir and node config file
        if (-e $noderoot && -e "$noderoot/etc/cgconfig.conf" && -e "$noderoot/etc/stabile/nodeconfig.cfg") {
            push @noderoots, $noderoot;
        }
    }
    untie %idreg;
    push @noderoots, "/";
    foreach my $noderoot (@noderoots) {
        $noderoot = '' if ($noderoot eq '/');
        next unless (-e "$noderoot/etc/stabile/nodeconfig.cfg");
        my $nodecfg = new Config::Simple("$noderoot/etc/stabile/nodeconfig.cfg");
        my $vm_readlimit = $nodecfg->param('VM_READ_LIMIT'); # e.g. 125829120 = 120 * 1024 * 1024 = 120 MB / s
        my $vm_writelimit = $nodecfg->param('VM_WRITE_LIMIT');
        my $vm_iopsreadlimit = $nodecfg->param('VM_IOPS_READ_LIMIT'); # e.g. 1000 IOPS
        my $vm_iopswritelimit = $nodecfg->param('VM_IOPS_WRITE_LIMIT');

        my $piston_readlimit = $nodecfg->param('PISTON_READ_LIMIT'); # e.g. 125829120 = 120 * 1024 * 1024 = 120 MB / s
        my $piston_writelimit = $nodecfg->param('PISTON_WRITE_LIMIT');
        my $piston_iopsreadlimit = $nodecfg->param('PISTON_IOPS_READ_LIMIT'); # e.g. 1000 IOPS
        my $piston_iopswritelimit = $nodecfg->param('PISTON_IOPS_WRITE_LIMIT');

        my $file = "$noderoot/etc/cgconfig.conf";
        unless (open(FILE, "< $file")) {
            $postreply .= "Status=Error problem opening $file\n";
            return $postreply;
        }
        my @lines = <FILE>;
        close FILE;
        chomp @lines;
        my $group;
        my @newlines;
        for my $line (@lines) {
            $group = $1 if ($line =~ /group (\w+) /);
            if ($group eq 'stabile' && $noderoot) {
                # These are already set to valve values by pressurecontrol
                $line =~ s/(blkio.throttle.read_bps_device = "\d+:\d+).*/$1 $piston_readlimit";/;
                $line =~ s/(blkio.throttle.write_bps_device = "\d+:\d+).*/$1 $piston_writelimit";/;
                $line =~ s/(blkio.throttle.read_iops_device = "\d+:\d+).*/$1 $piston_iopsreadlimit";/;
                $line =~ s/(blkio.throttle.write_iops_device = "\d+:\d+).*/$1 $piston_iopswritelimit";/;
            }
            elsif ($group eq 'stabilevm') {
                $line =~ s/(blkio.throttle.read_bps_device = "\d+:\d+).*/$1 $vm_readlimit";/;
                $line =~ s/(blkio.throttle.write_bps_device = "\d+:\d+).*/$1 $vm_writelimit";/;
                $line =~ s/(blkio.throttle.read_iops_device = "\d+:\d+).*/$1 $vm_iopsreadlimit";/;
                $line =~ s/(blkio.throttle.write_iops_device = "\d+:\d+).*/$1 $vm_iopswritelimit";/;
            }
            push @newlines, $line;
        }
        unless (open(FILE, "> $file")) {
            $postreply .= "Status=Error Problem opening $file\n";
            return $postreply;
        }
        print FILE join("\n", @newlines);
        close(FILE);
        $postreply .= "Status=OK Setting VM and auxilliary cgroups limits in $file: $vm_readlimit, $vm_writelimit, $vm_iopsreadlimit, $vm_iopswritelimit\n";
    }
    return $postreply;
}