#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license

package Stabile::Systems;

use Webmin::API;
use File::Basename;
use lib dirname (__FILE__);
use Stabile;
use Error qw(:try);
use String::Escape qw( unbackslash backslash );
use Config::Simple;
use Time::Local;
use Mon::Client;
use File::Glob qw(bsd_glob);
use POSIX;
use Proc::Daemon;
use Data::UUID;
use LWP::Simple qw(!head);
use MIME::Lite;
use RRDTool::OO;
use Text::CSV_XS qw( csv );

my $cfg = new Config::Simple("/etc/stabile/config.cfg");

my $engineid = $Stabile::config->get('ENGINEID') || "";
my $enginename = $Stabile::config->get('ENGINENAME') || "";
my $doxmpp = $Stabile::config->get('DO_XMPP') || "";
my $disablesnat = $Stabile::config->get('DISABLE_SNAT') || "";
my ($datanic, $extnic) = $main::getNics->();
my $extiprangestart = $Stabile::config->get('EXTERNAL_IP_RANGE_START');
my $extiprangeend = $Stabile::config->get('EXTERNAL_IP_RANGE_END');

if (!$Stabile::Servers::q && !$Stabile::Images::q  && !$Stabile::Networks::q && !$Stabile::Users::q && !$Stabile::Nodes::q) { # We are not being called from another script
    $q = new CGI;
    my %cgiparams = $q->Vars;
    %params = %cgiparams if (%cgiparams);
} else {
    $console = 1;
}

my %ahash; # A hash of accounts and associated privileges current user has access to
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
    process() if ($package);

} catch Error with {
	my $ex = shift;
    print header('text/html', '500 Internal Server Error') unless ($console);
	if ($ex->{-text}) {
        print "Got error $package: ", $ex->{-text}, " on line ", $ex->{-line}, "\n";
	} else {
	    print "Status=ERROR\n";
	}
} finally {
};

1;

sub getObj {
    my %h = %{@_[0]};
    $console = 1 if $obj->{"console"};
    my $obj;
    $action =  $action || $h{'action'};
    if ($action =~ /updateaccountinfo|monitors|listuptime|buildsystem|removeusersystems|updateengineinfo|^register$|^packages$/) {
        $obj = \%h;
        $obj->{domuuid} = $curdomuuid if ($curdomuuid);
    } else {
        my $uuid =$h{"uuid"} || $curuuid;
        $uuid = $curuuid if ($uuid eq 'this');
        my $status = $h{"status"};
        if ((!$uuid && $uuid ne '0') && (!$status || $status eq 'new')) {
            my $ug = new Data::UUID;
            $uuid = $ug->create_str();
            $status = 'new';
        };
        return 0 unless ($uuid && length $uuid == 36);

        $obj = {uuid => $uuid};
        my @props = qw(uuid name  user  notes  created  opemail  opfullname  opphone  email  fullname  phone  services
            recovery  alertemail  image  networkuuid1  internalip autostart issystem system systemstatus from to
            appid callback installsystem installaccount networkuuids);
        if ($register{$uuid}) {
            foreach my $prop (@props) {
                my $val = $h{$prop} || $register{$uuid}->{$prop};
                $obj->{$prop} = $val if ($val);
            }
        } else {
            foreach my $prop (@props) {
                my $val = $h{$prop};
                $obj->{$prop} = $val if ($val);
            }
        }
    }
    return $obj;
}

sub Init {
    unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>1}, $Stabile::dbopts)) ) {$posterror = "Unable to access user register"; return;};
    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {$posterror = "Unable to access domain register"; return;};
    unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {$posterror = "Unable to access network register"; return;};
    unless ( tie(%register,'Tie::DBI', Hash::Merge::merge({table=>'systems'}, $Stabile::dbopts)) ) {$posterror = "Unable to access system register"; return;};

    $cursysuuid = $domreg{$curuuid}->{'system'}if ($domreg{$curuuid});
    $tktuser = $tktuser || $Stabile::tktuser;
    $user = $user || $Stabile::user;

    *Deletesystem = \&Removesystem;
    *Backup = \&systemAction;

    *do_help = \&action;
    *do_tablelist = \&do_list;
    *do_arraylist = \&do_list;
    *do_flatlist = \&do_list;
    *do_monitors = \&privileged_action;
    *do_suspend = \&systemAction;
    *do_resume = \&systemAction;
    *do_shutdown = \&systemAction;
    *do_destroy = \&systemAction;
    *do_start = \&systemAction;
    *do_backup = \&privileged_action;
    *do_packages_load = \&privileged_action;
    *do_monitors_save = \&privileged_action;
    *do_monitors_remove = \&privileged_action;
    *do_monitors_enable = \&privileged_action;
    *do_monitors_disable = \&privileged_action;
    *do_monitors_acknowledge = \&privileged_action;
    *do_save = \&privileged_action;
    *do_changemonitoremail = \&privileged_action;
    *do_buildsystem = \&privileged_action;
    *do_removesystem = \&privileged_action;
    *do_deletesystem = \&privileged_action;
    *do_removeusersystems = \&privileged_action;
    *do_updateengineinfo = \&privileged_action;

    *do_gear_backup = \&do_gear_action;
    *do_gear_packages_load = \&do_gear_action;
    *do_gear_monitors = \&do_gear_action;
    *do_gear_monitors_enable = \&do_gear_action;
    *do_gear_monitors_save = \&do_gear_action;
    *do_gear_monitors_remove = \&do_gear_action;
    *do_gear_monitors_disable = \&do_gear_action;
    *do_gear_monitors_acknowledge = \&do_gear_action;
    *do_gear_save = \&do_gear_action;
    *do_gear_changemonitoremail = \&do_gear_action;
    *do_gear_buildsystem = \&do_gear_action;
    *do_gear_removesystem = \&do_gear_action;
    *do_gear_deletesystem = \&do_gear_action;
    *do_gear_removeusersystems = \&do_gear_action;
    *do_gear_updateengineinfo = \&do_gear_action;
    *Monitors_remove = \&Monitors_save;
    *Monitors_enable = \&Monitors_action;
    *Monitors_disable = \&Monitors_action;
    *Monitors_acknowledge = \&Monitors_action;
}

sub do_uuidlookup {
    if ($help) {
        return <<END
GET:uuid:
Simple action for looking up a uuid or part of a uuid and returning the complete uuid.
END
    }
    my $res;
    $res .= header('text/plain') unless $console;
    my $u = $options{u};
    $u = $curuuid unless ($u || $u eq '0');
    my $ruuid;
    if ($u || $u eq '0') {
        my $match;
        foreach my $uuid (keys %register) {
            if ($uuid =~ /^$u/) {
                $ruuid = $uuid if ($register{$uuid}->{'user'} eq $user || index($privileges,"a")!=-1);
                $match = 1;
                last;
            }
        }
        unless ($match) {
            foreach my $uuid (keys %domreg) {
                if ($uuid =~ /^$u/) {
                    $ruuid = $uuid if ((!$domreg{$uuid}->{'system'} || $domreg{$uuid}->{'system'} eq '--' )&&  ($domreg{$uuid}->{'user'} eq $user || index($privileges,"a")!=-1));
                    last;
                }
            }
        }
    }
    $res .= "$ruuid\n" if ($ruuid);
    return $res;
}

sub do_uuidshow {
    if ($help) {
        return <<END
GET:uuid:
Simple action for showing a single system.
END
    }
    my $res;
    $res .= header('application/json') unless $console;
    my $u = $options{u};
    $u = $curuuid unless ($u || $u eq '0');
    if ($u) {
        foreach my $uuid (keys %register) {
            if (($register{$uuid}->{'user'} eq $user || $register{$uuid}->{'user'} eq 'common' || index($privileges,"a")!=-1)
                && $uuid =~ /^$u/) {
                my %hash = %{$register{$uuid}};
                delete $hash{'action'};
                delete $hash{'nextid'};
                my $dump = to_json(\%hash, {pretty=>1});
                $dump =~ s/undef/"--"/g;
                $res .= $dump;
                last;
            }
        }
    }
    return $res;
}

sub do_list {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
List systems current user has access to.
END
    }
    my $sysuuid;
    if ($uripath =~ /systems(\.cgi)?\/(\?|)(this)/) {
        $sysuuid = $cursysuuid || $curuuid;
    } elsif ($uripath =~ /systems(\.cgi)?\/(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})/) {
        $sysuuid = $2;
    } elsif ($params{'system'}) {
        $sysuuid = $obj->{'system'};
        $sysuuid = $cursysuuid || $curuuid if ($obj->{system} eq 'this');
    }
    $postreply = getSystemsListing($action, $uuid);
    return $postreply;
}

sub Monitors_action {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:id:
Enable, disable or acknowledge a monitor. Id is of the form serveruuid:service
END
    }
    my $monitor_action = "enable";
    $monitor_action = "disable" if ($action eq 'monitors_disable');
    $monitor_action = "acknowledge" if ($action eq 'monitors_acknowledge');
    my $log_action = uc $monitor_action;
    my $group;
    my $service;
    my $logline;
    if ($uuid =~ /(.+):(.+)/) {
        $group = $1;
        $service = $2;
    }
    if ($group && $service) {
        my $reguser = $domreg{$group}->{'user'};
        # Security check
        if ($user eq $reguser || index($privileges,"a")!=-1) {
            my $oplogfile = "/var/log/stabile/$year-$month:$group:$service";
            unless (-e $oplogfile) {
                `/usr/bin/touch "$oplogfile"`;
                `/bin/chown mon:mon "$oplogfile"`;
            }
            if ($monitor_action =~ /enable|disable/) {
                my $res = `/usr/bin/moncmd $monitor_action service $group $service`;
                chomp $res;
                $logline = "$current_time, $log_action, , $pretty_time";
            } elsif ($monitor_action eq "acknowledge") {
                my $ackcomment = $obj->{"ackcomment"};
                # my $ackcomment = backslash( $obj->{"ackcomment"} );
                #$ackcomment =~ s/ /\\\20/g;
                my $monc = new Mon::Client (
                    host => "127.0.0.1"
                );
                $ackcomment = ($ackcomment)?"$user, $ackcomment":$user;
                $monc->connect();
                $monc->ack($group, $service, $ackcomment);
                $monc->disconnect();
                $logline = "$current_time, ACKNOWLEDGE, $ackcomment, $pretty_time";
                my %emails;
                my @emaillist = split(/\n/, `/bin/cat /etc/mon/mon.cf`);
                my $emailuuid;
                foreach my $eline (@emaillist) {
                    my ($a, $b, $c, $d) = split(/ +/, $eline);
                    if ($a eq 'watch') {
                        if ($b =~ /\S+-\S+-\S+-\S+-\S+/) {$emailuuid = $b;}
                        else {$emailuuid = ''};
                    }
                    $emails{$emailuuid} = $d if ($emailuuid && $b eq 'alert' && $c eq 'stabile.alert');
                };
                my $email = $emails{$group};
                my $servername = $domreg{$group}->{'name'};
                my $serveruser = $domreg{$group}->{'user'};
                if ($email) {
                    my $mailtext = <<EOF;
Acknowledged by: $user
Server name: $servername
Server UUID: $group
System UUID: $sysuuid
Server user: $serveruser
Service: $service
EOF
                    ;

                    my $mailhtml = <<END;
<!DOCTYPE html
    PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
     "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en-US" xml:lang="en-US">
    <head>
        <title>Problems with $servername:$service are being handled</title>
        <meta http-equiv="Pragma" content="no-cache" />
		<link rel="stylesheet" type="text/css" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css" />
        <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
    </head>
    <body class="tundra">
        <div>
            <div class="well" style="margin:20px;">
                <h3 style="color: #2980b9!important; margin-bottom:30px;">Relax, the problems with your service are being handled!</h3>
                <div>The problems with the service <strong>$service</strong> on the server <strong>$servername</strong> running on <strong>$enginename</strong> have been acknowledged at $pretty_time and are being handled by <strong>$tktuser ($user)</strong>.</div>
                <br>
                <div>Thanks,<br>your friendly monitoring daemon</div>
            </div>
        </div>
    </body>
</html>
END
                    ;

                    my $xmpptext = "ACK: $servername:$service is being handled ($pretty_time)\n";
                    $xmpptext .= "Acknowledged by: $tktuser ($user)\n";

                    my $msg = MIME::Lite->new(
                        From     => 'monitoring',
                        To       => $email,
                        Type     => 'multipart/alternative',
                        Subject  => "ACK: $servername:$service is being handled ($pretty_time)",
                    );
                    $msg->add("sysuuid" => $sysuuid);

                    my $att_text = MIME::Lite->new(
                        Type     => 'text',
                        Data     => $mailtext,
                        Encoding => 'quoted-printable',
                    );
                    $att_text->attr('content-type'
                        => 'text/plain; charset=UTF-8');
                    $msg->attach($att_text);

                    my $att_html = MIME::Lite->new(
                        Type     => 'text',
                        Data     => $mailhtml,
                        Encoding => 'quoted-printable',
                    );
                    $att_html->attr('content-type'
                        => 'text/html; charset=UTF-8');
                    $msg->attach($att_html);

                    $msg->send;

                    if ($doxmpp) {
                        foreach my $to (split /, */, $email) {
                            my $xres = $main::xmppSend->($to, $xmpptext, $engineid, $sysuuid);
                        }
                        # Send alerts to Origo operators on duty
                        my $oponduty = 'operator@sa.origo.io';
                        $msg->replace('to', $oponduty);
                        $msg->send;
                        my $xres = $main::xmppSend->($oponduty, $xmpptext, $engineid, $sysuuid);
                    }
                }
            }
            `/bin/echo >> $oplogfile "$logline"`;
            $postreply .= "Status=OK OK $monitor_action"." $service service\n";
        }
    } else {
        $postreply = "Status=Error problem $monitor_action monitor $uuid\n";
    }
    return $postreply;
}

sub do_register {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,format:
Print software register for server or system of servers with given uuid. Format is html, csv or json (default).
END
    }

    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};
    my @domregvalues = values %domreg;
    my %reghash;
    foreach my $valref (@domregvalues) {
        if ($valref->{'user'} eq $user || $fulllist) {
            if (!$uuid || $uuid eq '*' || $uuid eq $valref->{'uuid'} || $uuid eq $valref->{'system'}) {
                my $os = $valref->{'os'} || 'unknown';
                my $domname = $valref->{'name'};
                utf8::decode($domname);
                if ($reghash{$os}) {
                    $reghash{ $os . '-' . $reghash{$os}->{'oscount'} } = {
                        os=>'',
                        sortos=>$os."*",
                        user=>$valref->{'user'},
                        name=>$domname,
                        hostname=>$valref->{'hostname'}
                    };
                    $reghash{$os}->{'oscount'}++;
                } else {
                    $reghash{$os} = {
                        os=>$os,
                        sortos=>$os,
                        user=>$valref->{'user'},
                        name=>$domname,
                        hostname=>$valref->{'hostname'},
                        oscount=>1
                    }
                }
            }
        }

    }
    untie %domreg;
    my @sorted_oslist = sort {$a->{'sortos'} cmp $b->{'sortos'}} values %reghash;
    if ($obj->{'format'} eq 'html') {
        my $res;
        $res .= qq[<tr><th>OS</th><th>Name</th><th>Hostname</th><th>Count</th></tr>];
        foreach my $valref (@sorted_oslist) {
            $res .= qq[<tr><td>$valref->{'os'}</td><td>$valref->{'name'}</td><td>$valref->{'hostname'}</td><td>$valref->{'oscount'}</td></tr>];
        }
        $postreply = header();
        $postreply .= qq[<table cellspacing="0" frame="void" rules="rows" class="systemTables">$res</table>];
    } elsif ($obj->{'format'} eq 'csv') {
        $postreply = header("text/plain");
        csv(in => \@sorted_oslist, out => \my $csvdata);
        $postreply .= $csvdata;
    } else {
        $postreply .= to_json(\@sorted_oslist);
    }
    return $postreply;

}

sub Monitors {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
Handling of monitors
END
    }
# We are dealing with a POST request, i.e. an action on a monitor
# or a PUT or DELETE request, i.e. creating/saving/deleting items
    if (($ENV{'REQUEST_METHOD'} eq 'DELETE' || $params{"PUTDATA"} || $ENV{'REQUEST_METHOD'} eq 'PUT' || $ENV{'REQUEST_METHOD'} eq 'POST') && !$isreadonly) {
        my @json_array;
        my %json_hash;
        my $delete;
        if ($ENV{'REQUEST_METHOD'} eq 'DELETE' && $uripath =~ /action=monitors\/(.+):(.+)/) {
            print header('text/json', '204 No Content') unless $console;
            %json_hash = ('serveruuid', $1, 'service', $2);
            @json_array = (\%json_hash);
            $delete = 1;
#            print Monitors_save(\%json_hash, $delete);
            print Monitors_save($uuid, "monitors_remove", $obj);
        } else {
            my $json_text = $params{"PUTDATA"} || $params{'keywords'};
            $json_text = encode('latin1', decode('utf8', $json_text));
            $json_text =~ s/\x/ /g;
            @json_array = from_json($json_text);
            $json_hash_ref = @json_array[0];
#            my $res = Monitors_save($json_hash_ref, $delete);
            my $res = Monitors_save($uuid, "monitors_save", $obj);
            if ($res =~ /^{/) {
                print header('text/json') unless $console;
                print $res;
            } else {
                print header('text/html', '400 Bad Request') unless $console;
                print qq|$res|;
            }
        }

# We are dealing with a regular GET request, i.e. a listing
    } else {
        my $selgroup;
        my $selservice;
        if ($uuid && $uuid ne '*') { # List all monitors for specific server
            $selgroup = $uuid;
            if ($uuid =~ /(.+):(.+)/){ # List specific monitor for specific server
                $selgroup = $1;
                $selservice = $2;
            }
        }
        my $usemoncmd = 0;
        my %opstatus = getOpstatus($selgroup, $selservice, $usemoncmd);
        my @monitors = values(%opstatus);
        my @sorted_monitors = sort {$a->{'opstatus'} cmp $b->{'opstatus'}} @monitors;
        my $json_text;
        if ($obj->{'listaction'} eq 'show' && scalar @monitors == 1) {
            $json_text = to_json($sorted_monitors[0], {pretty => 1});
        } else {
            $json_text = to_json(\@sorted_monitors, {pretty => 1});
        }
        utf8::decode($json_text);
        $postreply = $json_text;
        return $postreply;
    }

}

sub do_remove {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
DELETE:uuid:
Delete a system from database and make all member servers free agents.
END
    }
    if ($register{$uuid}) {
        unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};
        my @domregvalues = values %domreg;
        my @curregvalues;
        foreach my $valref (@domregvalues) {
            # Only include VM's belonging to current user (or all users if specified and user is admin)
            if ($user eq $valref->{'user'} || $fulllist) {
                my $system = $valref->{'system'};
                if ($system eq $uuid) {
                    $valref->{'system'} = '';
                    push(@curregvalues, $valref);
                }
            }
        }
        delete $register{$uuid};
        tied(%domreg)->commit;
        tied(%register)->commit;
        untie %domreg;
        if ($match) {
            $postreply = to_json(@curregvalues);
        } else {
            $postreply = header('text/plain', '204 No Content') unless $console;
        }
    }
    return $postreply;
}

sub Save {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
PUT:uuid, fullname, email, phone, opfullname, opemail, opphone, alertemail, services, recovery, networkuuids:
Save properties for a system. If no uuid is provided, a new stack is created.[networkuuids] is a comma-separated list of networks reserved to this stack for use not associated with specific servers.
[networkuuids] is a list of UUIDs of linked network connections, i.e. connections reserved for this system to handle

        Specify '--' to clear a value.
END
    }
    my $name = $obj->{"name"} || $register{$uuid}->{'name'};
    my $reguser;
    $reguser = $register{$uuid}->{'user'} if ($register{$uuid});
    $console = 1 if ($obj->{'console'});
    my $issystem = $obj->{'issystem'} || $register{$uuid};
    my $notes = $obj->{"notes"};
    my $email = $obj->{'email'};
    my $fullname = $obj->{'fullname'};
    my $phone = $obj->{'phone'};
    my $opemail = $obj->{'opemail'};
    my $opfullname = $obj->{'opfullname'};
    my $opphone = $obj->{'opphone'};
    my $alertemail = $obj->{'alertemail'};
    my $services = $obj->{'services'};
    my $recovery = $obj->{'recovery'};
    my $networkuuids = $obj->{'networkuuids'};
    my $autostart = $obj->{'autostart'};

    if ((!$uuid)) {
        my $ug = new Data::UUID;
        $uuid = $ug->create_str();
        $issystem = 1;
    };
    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Status=Error Unable to access domain register"};
    unless ($register{$uuid} || $domreg{$uuid}) {
        $obj->{'status'} = 'new';
        $issystem = 1;
    }
    $issystem = 1 if ($register{$uuid});
    unless (($uuid && length $uuid == 36)) {
        $postreply = "Status=Error Invalid UUID\n";
        return $postreply;
    }

    # Sanity checks
    if ($name && length $name > 255) {
        $postreply .= "Status=Error Bad data: $name " . (length $name) . "\n";
        return $postreply;
    };

    if ($issystem) { # We are dealing with a system
        # Security check
        if (($user eq $reguser || $isadmin) && $register{$uuid}) { # Existing system
            my @props = ('name','fullname','email','phone','opfullname','opemail','opphone','alertemail'
                ,'notes','services','recovery','autostart');
            my %oldvals;
            foreach my $prop (@props) {
                my $val = $obj->{$prop};
                if ($val) {
                    $val = '' if ($val eq '--');
                    $oldvals{$prop} = $register{$uuid}->{$prop} || $userreg{$user}->{$prop};
                    if ($val eq $userreg{$user}->{$prop}) {
                        $register{$uuid}->{$prop} = ''; # Same val as parent (user val), reset
                    } else {
                        $register{$uuid}->{$prop} = $val;
                    }
                    if ($prop eq 'autostart') {
                        $register{$uuid}->{$prop} = ($val)?'1':'';
                    }
                    if ($prop eq 'name') {
                        my $json_text = qq|{"uuid": "$uuid" , "name": "$val"}|;
                        $main::postAsyncToOrigo->($engineid, 'updateapps', "[$json_text]");
                    }
                }
            }
            my %childrenhash;
            my $alertmatch;
            foreach my $prop (@props) {
                my $val = $obj->{$prop};
                if ($val) {
                    $val = '' if ($val eq '--');
                    # Update children
                    foreach my $domvalref (values %domreg) {
                        if ($domvalref->{'user'} eq $user && $domvalref->{'system'} eq $uuid) {
                            my %domval = %{$domvalref};
                            $childrenhash{$domvalref->{'uuid'}} =\%domval unless ($childrenhash{$domvalref->{'uuid'}});
                            $childrenhash{$domvalref->{'uuid'}}->{$prop} = $val;
                            if ($prop eq 'autostart') {
                                $domvalref->{$prop} = ($val)?'1':''; # Always update child servers with autostart prop
                            } elsif (!$domvalref->{$prop} || $domvalref->{$prop} eq $oldvals{$prop}) {
                                $domvalref->{$prop} = '';
                                if ($prop eq 'alertemail') {
                                    if (change_monitor_email($domvalref->{'uuid'}, $val, $oldvals{$prop})) {
                                        $alertmatch = 1;
                                    }
                                }
                            }
                        }
                    }
                }
            }
            my @children = values %childrenhash;
            $obj->{'children'} = \@children if (@children);
            $postreply = getSystemsListing();
        } elsif ($obj->{'status'} eq 'new')  { # New system
            $register{$uuid} = {
                uuid=>$uuid,
                name=>$name,
                user=>$user,
                created=>$current_time
            };
            my $valref = $register{$uuid};
            my %val = %{$valref};
            $val{'issystem'} = 1;
            $val{'status'} = '--';
            $dojson = 1;
            $postreply = to_json(\%val, {pretty=>1});
        } else {
            $postreply .= "Status=Error Not enough privileges: $user\n";
        }
    } else { # We are dealing with a server
        my $valref = $domreg{$uuid};
        if (!$valref && $obj->{'uuid'}[0]) {$valref = $domreg{ $obj->{'uuid'}[0] }}; # We are dealing with a newly created server
        if ($valref && ($valref->{'user'} eq $user || $isadmin)) {
            my $system = $obj->{'system'};
            my $servername = $obj->{'name'};
            if ($servername && $servername ne $valref->{'name'}) {
                $valref->{'name'} = $servername;
                # Update status of images
                my @imgs = ($domreg{$uuid}->{image}, $domreg{$uuid}->{image2}, $domreg{$uuid}->{image3}, $domreg{$uuid}->{image4});
                my @imgkeys = ('image', 'image2', 'image3', 'image4');
                unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {return "Status=Error Unable to access image register"};
                for (my $i=0; $i<4; $i++) {
                    my $img = $imgs[$i];
                    my $k = $imgkeys[$i];
                    if ($img && $img ne '--') {
                        $imagereg{$img}->{'domains'} = $uuid;
                        $imagereg{$img}->{'domainnames'} = $servername;
                    }
                }
                untie %imagereg;
                my $json_text = qq|{"uuid": "$uuid" , "name": "$servername"}|;
                $main::postAsyncToOrigo->($engineid, 'updateapps', "[$json_text]");
            }
            $valref->{'system'} = ($system eq '--'?'':$system) if ($system);
            $valref->{'notes'} = (($notes eq '--')?'':$notes) if ($notes);
            $valref->{'email'} = ($email eq '--'?'':$email) if ($email);
            $valref->{'fullname'} = ($fullname eq '--'?'':$fullname) if ($fullname);
            $valref->{'phone'} = ($phone eq '--'?'':$phone) if ($phone);
            $valref->{'opemail'} = ($opemail eq '--'?'':$opemail) if ($opemail);
            $valref->{'opfullname'} = ($opfullname eq '--'?'':$opfullname) if ($opfullname);
            $valref->{'opphone'} = ($opphone eq '--'?'':$opphone) if ($opphone);
            $valref->{'services'} = ($services eq '--'?'':$services) if ($services);
            $valref->{'recovery'} = ($recovery eq '--'?'':$recovery) if ($recovery);
            $valref->{'autostart'} = ($autostart && $autostart ne '--'?'1':'');
            if ($alertemail) {
                $alertemail = '' if ($alertemail eq '--');
                if ($valref->{'alertemail'} ne $alertemail) {
                    # If alert email is changed, update monitor if it is configured with this email
                    if (change_monitor_email($valref->{'uuid'}, $alertemail, $valref->{'alertemail'})){
                        $alertmatch = 1;
                        #`/usr/bin/moncmd reset keepstate`;
                    }
                    $valref->{'alertemail'} = $alertemail;
                }
            }

            tied(%domreg)->commit;
            $postreply = getSystemsListing(); # Hard to see what else to do, than to send entire table
        }
    }
    if ($networkuuids && $networkuuids ne '--') { # link networks to this system
        my @networks = split(/, ?/, $networkuuids);
        my @newnetworks = ();
        my @newnetworknames = ();
        unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {return "Unable to access networks register"};
        foreach my $networkuuid (@networks) {
            next unless ($networkreg{$networkuuid});
            if (
                !$networkreg{$networkuuid}->{'domains'} # a network cannot both be linked and in active use
                    && (!$networkreg{$networkuuid}->{'systems'} ||  $networkreg{$networkuuid}->{'systems'} eq $uuid) # check if network is already linked to another system
            ) {
                $networkreg{$networkuuid}->{'systems'} = $uuid;
                $networkreg{$networkuuid}->{'systemnames'} = $name;
                push @newnetworks, $networkuuid;
                push @newnetworknames, $networkreg{$networkuuid}->{'name'};
            }
        }
        if ($issystem && $register{$uuid}) {
            $register{$uuid}->{'networkuuids'} = join(", ", @newnetworks);
            $register{$uuid}->{'networknames'} = join(", ", @newnetworknames);
        } elsif ($domreg{$uuid}) {
            $domreg{$uuid}->{'networkuuids'} = join(", ", @newnetworks);
            $domreg{$uuid}->{'networknames'} = join(", ", @newnetworknames);
        }
    }
    untie %domreg;
    return $postreply;
}

sub do_resettoaccountinfo {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Recursively reset contact data for all systems and servers
END
    }
    my @props = ('fullname','email','phone','opfullname','opemail','opphone','alertemail');
    my $alertmatch;
    foreach my $sysvalref (values %register) {
        if ($user eq $sysvalref->{'user'}) {
            my $sysuuid = $sysvalref->{'uuid'};
            foreach my $prop (@props) {
                # Does this system have a value?
                if ($sysvalref->{$prop}) {
                    $sysvalref->{$prop} = ''; # An empty val refers to parent (user) val
                }
            }
        }
    }
    # Update domains
    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {$posterror = "Unable to access domain register"; return;};
    foreach my $domvalref (values %domreg) {
        if ($domvalref->{'user'} eq $user) {
            foreach my $prop (@props) {
                if ($domvalref->{$prop}) {
                    $domvalref->{$prop} = '';
                }
                if ($prop eq 'alertemail') {
                    if (change_monitor_email($domvalref->{'uuid'}, $userreg{$user}->{$prop})) {
                        $alertmatch = 1;
                    }
                }
            }
        }
    }
    tied(%domreg)->commit;
    untie %domreg;
    #`/usr/bin/moncmd reset keepstate` if ($alertmatch);
    $postreply .= "Status=OK OK - reset systems and servers contacts to account values\n";
    return $postreply;
}

sub do_start_server {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
Start specific server.
END
    }
    $Stabile::Servers::console = 1;
    require "$Stabile::basedir/cgi/servers.cgi";
    $postreply .= Stabile::Servers::Start($uuid, 'start', { buildsystem => 0 });
}

sub systemAction {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
Suspend, resume, start, shutdown, destroy og backup individual servers or servers belonging to a system.
END
    }
    my $issystem = $obj->{'issystem'} || $register{$uuid};

    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};
    unless (tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access images register"}|; return $res;};

    if ($issystem) { # Existing system
        if (($user eq $reguser || $isadmin) && $register{$uuid}){ # Existing system
            my $domactions;
            my $imageactions;

            foreach my $domvalref (values %domreg) {
                if (($domvalref->{'system'} eq $uuid || $domvalref->{'uuid'} eq $uuid)
                    && ($domvalref->{'user'} eq $user || $isadmin)) {

                    my $domaction;
                    my $imageaction;
                    if ($domvalref->{'status'} eq 'paused' && ($action eq 'start' || $action eq 'resume')) {
                        $domaction = 'resume';
                    } elsif ($domvalref->{'status'} eq 'running' && $action eq 'suspend') {
                        $domaction = $action;
                    } elsif ($domvalref->{'status'} eq 'shutoff' && $action eq 'start') {
                        $domaction = $action;
                    } elsif ($domvalref->{'status'} eq 'inactive' && $action eq 'start') {
                        $domaction = $action;
                    } elsif ($domvalref->{'status'} eq 'running' && $action eq 'shutdown') {
                        $domaction = $action;
                    } elsif ($domvalref->{'status'} eq 'running' && $action eq 'destroy') {
                        $domaction = $action;
                    } elsif ($domvalref->{'status'} eq 'shuttingdown' && $action eq 'destroy') {
                        $domaction = $action;
                    } elsif ($domvalref->{'status'} eq 'destroying' && $action eq 'destroy') {
                        $domaction = $action;
                    } elsif ($domvalref->{'status'} eq 'starting' && $action eq 'destroy') {
                        $domaction = $action;
                    } elsif ($domvalref->{'status'} eq 'inactive' && $action eq 'destroy') {
                        $domaction = $action;
                    } elsif ($domvalref->{'status'} eq 'paused' && $action eq 'destroy') {
                        $domaction = $action;
                    } elsif ($action eq 'backup') {
                        $imageaction = $action;
                    }
                    if ($domaction) {
                        $domactions .= qq/{"uuid":"$domvalref->{'uuid'}","action":"$domaction"},/;
                    }
                    if ($imageaction) {
                        my $image = $domvalref->{'image'};
                        if ($imagereg{$image}->{'status'} =~ /used|active/) {
                            $imageactions .= qq/{"uuid":"$imagereg{$image}->{'uuid'}","action":"backup"},/;
                        }
                        my $image2 = $domvalref->{'image2'};
                        if ($image2 && $image2 ne '--' && $imagereg{$image2}->{'status'} =~ /used|active/) {
                            $imageactions .= qq/{"uuid":"$imagereg{$image2}->{'uuid'}","action":"backup"},/;
                        }
                        my $image3 = $domvalref->{'image3'};
                        if ($image3 && $image3 ne '--' && $imagereg{$image3}->{'status'} =~ /used|active/) {
                            $imageactions .= qq/{"uuid":"$imagereg{$image3}->{'uuid'}","action":"backup"},/;
                        }
                        my $image4 = $domvalref->{'image4'};
                        if ($image4 && $image4 ne '--' && $imagereg{$image4}->{'status'} =~ /used|active/) {
                            $imageactions .= qq/{"uuid":"$imagereg{$image4}->{'uuid'}","action":"backup"},/;
                        }
                    }
                }
            }

            if ($domactions) {
                $domactions = substr($domactions,0,-1);
                my $uri_action = qq/{"items":[$domactions]}/;
                $uri_action = URI::Escape::uri_escape($uri_action);
                $uri_action =~ /(.+)/; $uri_action = $1; #untaint
                $postreply .= `REMOTE_USER=$user $Stabile::basedir/cgi/servers.cgi -k $uri_action`;
            }
            if ($imageactions) {
                $imageactions = substr($imageactions,0,-1);
                my $uri_action = qq/{"items":[$imageactions]}/;
                $uri_action = URI::Escape::uri_escape($uri_action);
                $uri_action =~ /(.+)/; $uri_action = $1; #untaint
                $postreply .= `REMOTE_USER=$user $Stabile::basedir/cgi/images.cgi -k $uri_action`;
            }
            if (!$domactions && !$imageactions) {
                $postreply .= "Stream=ERROR $action";
            }
        }
    } else {
        if ($action eq 'backup') {
            my $image = $domreg{$uuid}->{'image'};
            my $imageactions;
            if ($imagereg{$image}->{'status'} =~ /used|active/) {
                $imageactions .= qq/{"uuid":"$imagereg{$image}->{'uuid'}","action":"gear_backup"},/;
            }
            my $image2 = $domreg{$uuid}->{'image2'};
            if ($image2 && $image2 ne '--' && $imagereg{$image2}->{'status'} =~ /used|active/) {
                $imageactions .= qq/{"uuid":"$imagereg{$image2}->{'uuid'}","action":"gear_backup"},/;
            }
            my $image3 = $domreg{$uuid}->{'image3'};
            if ($image3 && $image3 ne '--' && $imagereg{$image3}->{'status'} =~ /used|active/) {
                $imageactions .= qq/{"uuid":"$imagereg{$image3}->{'uuid'}","action":"gear_backup"},/;
            }
            my $image4 = $domreg{$uuid}->{'image4'};
            if ($image4 && $image4 ne '--' && $imagereg{$image4}->{'status'} =~ /used|active/) {
                $imageactions .= qq/{"uuid":"$imagereg{$image4}->{'uuid'}","action":"gear_backup"},/;
            }
            if ($imageactions) {
                $imageactions = substr($imageactions,0,-1);
                my $uri_action = qq/{"items":[$imageactions]}/;
                $uri_action = URI::Escape::uri_escape($uri_action);
                $uri_action = $1 if $uri_action =~ /(.+)/; #untaint
                $postreply .= `REQUEST_METHOD=POST REMOTE_USER=$user $Stabile::basedir/cgi/images.cgi -k "$uri_action"`;
            }
        } else {
            my $cmd = qq|REQUEST_METHOD=GET REMOTE_USER=$user $Stabile::basedir/cgi/servers.cgi -a $action -u $uuid|;
            $postreply = `$cmd`;
            #$postreply = $cmd;
            my $uistatus = $action."ing";
            $uistatus = "resuming" if ($action eq 'resume');
            $uistatus = "shuttingdown" if ($action eq 'shutdown');
            $main::updateUI->({ tab => 'servers',
                user                => $user,
                uuid                => $uuid,
                status              => $uistatus })

        }
    }
    untie %domreg;
    untie %imagereg;

    return $postreply;
}

sub Updateengineinfo {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
PUT:downloadmasters, externaliprangestart, externaliprangeend, proxyiprangestart, proxyiprangeend, proxygw, vmreadlimit, vmwritelimit, vmiopsreadlimit, vmiopswritelimit:
Save engine information.
END
    }
    unless ($isadmin) {
        $postreply = "Status=Error Not allowed\n";
        return $postreply;
    }
    my $msg = "Engine updated";
    my $dl = $obj->{'downloadmasters'};
    if ($dl eq '--' || $dl eq '0') {
        if ($downloadmasters) {
            $downloadmasters = '';
            `perl -pi -e 's/DOWNLOAD_MASTERS=.*/DOWNLOAD_MASTERS=0/;' /etc/stabile/config.cfg`;
        }
        $postreply .= "Status=OK Engine updated\n";
        my @ps = split("\n",  `pgrep pressurecontrol` ); `kill -HUP $ps[0]`;
    }
    elsif ($dl eq '1' || $dl eq '2') {
        if (!$downloadmasters || $dl eq '2') { # We use a value of 2 to force check for downloads
            $downloadmasters = 1;
            `perl -pi -e 's/DOWNLOAD_MASTERS=.*/DOWNLOAD_MASTERS=$dl/;' /etc/stabile/config.cfg`;
        }
        if ($dl eq '2') {
            $msg = "Checking for new or updated masters...";
        }
        $postreply .= "Status=OK Engine updated\n";
        my @ps = split("\n",  `pgrep pressurecontrol` );
        `kill -HUP $ps[0]`;
    }
    elsif ($obj->{'disablesnat'} eq '--' || $obj->{'disablesnat'} eq '0') {
        if ($disablesnat) {
            $disablesnat = '';
            `perl -pi -e 's/DISABLE_SNAT=.*/DISABLE_SNAT=0/;' /etc/stabile/config.cfg`;
        }
        $postreply .= "Status=OK Engine updated\n";
    }
    elsif ($obj->{'disablesnat'} eq '1') {
        unless ($disablesnat) {
            $disablesnat = 1;
            `perl -pi -e 's/DISABLE_SNAT=.*/DISABLE_SNAT=1/;' /etc/stabile/config.cfg`;
        }
        $postreply .= "Status=OK Engine updated\n";
    }
    elsif ($obj->{'externaliprangestart'}) {
        if ($obj->{'externaliprangestart'} =~ /\d+\.\d+\.\d+\.\d+/) {
            $extiprangestart = $obj->{'externaliprangestart'};
            $msg = "Setting external IP range start to $extiprangestart";
            `perl -pi -e 's/EXTERNAL_IP_RANGE_START=.*/EXTERNAL_IP_RANGE_START=$extiprangestart/;' /etc/stabile/config.cfg`;
            $postreply .= "Status=OK Engine updated\n";
        } else {
            $msg = "Not changing IP range - $obj->{'externaliprangestart'} is not valid";
        }
    }
    elsif ($obj->{'externaliprangeend'}) {
        if ($obj->{'externaliprangeend'} =~ /\d+\.\d+\.\d+\.\d+/) {
            $extiprangeend = $obj->{'externaliprangeend'};
            $msg = "Setting external IP range end to $extiprangeend";
            `perl -pi -e 's/EXTERNAL_IP_RANGE_END=.*/EXTERNAL_IP_RANGE_END=$extiprangeend/;' /etc/stabile/config.cfg`;
            $postreply .= "Status=OK Engine updated\n";
        } else {
            $msg = "Not changing IP range - $obj->{'externaliprangeend'} is not valid";
        }
    }
    elsif ($obj->{'proxyiprangestart'}) {
        if ($obj->{'proxyiprangestart'} =~ /\d+\.\d+\.\d+\.\d+/) {
            $extiprangestart = $obj->{'proxyiprangestart'};
            $msg = "Setting proxy IP range start to $extiprangestart";
            `perl -pi -e 's/PROXY_IP_RANGE_START=.*/PROXY_IP_RANGE_START=$extiprangestart/;' /etc/stabile/config.cfg`;
            $postreply .= "Status=OK Engine updated\n";
        } else {
            $msg = "Not changing IP range - $obj->{'proxyiprangestart'} is not valid";
        }
    }
    elsif ($obj->{'proxyiprangeend'}) {
        if ($obj->{'proxyiprangeend'} =~ /\d+\.\d+\.\d+\.\d+/) {
            $extiprangeend = $obj->{'proxyiprangeend'};
            $msg = "Setting proxy IP range end to $extiprangeend";
            `perl -pi -e 's/PROXY_IP_RANGE_END=.*/PROXY_IP_RANGE_END=$extiprangeend/;' /etc/stabile/config.cfg`;
            $postreply .= "Status=OK Engine updated\n";
        } else {
            $msg = "Not changing IP range - $obj->{'proxyiprangeend'} is not valid";
        }
    }
    elsif ($obj->{'proxygw'}) {
        if ($obj->{'proxygw'} =~ /\d+\.\d+\.\d+\.\d+/) {
            $proxygw = $obj->{'proxygw'};
            $msg = "Setting proxy gw to $proxygw";
            `perl -pi -e 's/PROXY_GW=.*/PROXY_GW=$proxygw/;' /etc/stabile/config.cfg`;
            $postreply .= "Status=OK Engine updated\n";
        } else {
            $msg = "Not changing IP range - $obj->{'proxygw'} is not valid";
        }
    }
    elsif ($obj->{'vmreadlimit'} || $obj->{'vmwritelimit'} || $obj->{'vmiopsreadlimit'} || $obj->{'vmiopswritelimit'}) {
        my $lim = 'vmreadlimit';
        my $uclim = 'VM_READ_LIMIT';
        if ($obj->{'vmwritelimit'}) {
            $lim = 'vmwritelimit';
            $uclim = 'VM_WRITE_LIMIT';
        } elsif ($obj->{'vmiopsreadlimit'}) {
            $lim = 'vmiopsreadlimit';
            $uclim = 'VM_IOPS_READ_LIMIT';
        } elsif ($obj->{'vmiopswritelimit'}) {
            $lim = 'vmiopswritelimit';
            $uclim = 'VM_IOPS_WRITE_LIMIT';
        }
        if ($obj->{$lim} >= 0 &&  $obj->{$lim} < 10000 *1024*1024) { #sanity checks
            unless ( tie(%idreg,'Tie::DBI', Hash::Merge::merge({table=>'nodeidentities',key=>'identity',CLOBBER=>3}, $Stabile::dbopts)) ) {return "Unable to access id register"};
            my @nodeconfigs;
            # Build hash of known node config files
            foreach my $valref (values %idreg) {
                my $nodeconfigfile = $valref->{'path'} . "/casper/filesystem.dir/etc/stabile/nodeconfig.cfg";
                next if ($nodeconfigs{$nodeconfigfile}); # Node identities may share basedir and node config file
                if (-e $nodeconfigfile) {
                    push @nodeconfigs, $nodeconfigfile;
                }
            }
            untie %idreg;
            push @nodeconfigs, "/etc/stabile/nodeconfig.cfg";
            my $limit = int $obj->{$lim};
            $msg = "Setting read limit to $limit";
            foreach my $nodeconfig (@nodeconfigs) {
                my $cfg = new Config::Simple($nodeconfig);
                $cfg->param($uclim, $limit);
                $cfg->save();
            }
            $Stabile::Nodes::console = 1;
            require "$Stabile::basedir/cgi/nodes.cgi";
            $postreply .= Stabile::Nodes::Configurecgroups();
            $postreply .= Stabile::Nodes::do_reloadall('','reloadall', {'nodeaction'=>'CGLOAD'});
            $postreply .= "Status=OK Engine and nodes updated: $lim set to $limit\n";
        } else {
            $msg = "Not changing limit - $obj->{$lim} is not valid";
        }
    }
    if (!$postreply) {
        $msg = "Engine not updated";
        $postreply = "Status=Error Engine not updated\n" ;
    }
    $main::updateUI->({tab=>'home', user=>$user, type=>'update', message=>$msg});
    return $postreply;
}

sub do_updateaccountinfo {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
PUT:fullname, email, phone, opfullname, opemail, opphone, alertemail, allowfrom, allowinternalapi:
Save user information.
END
    }
    my @props = ('fullname','email','phone','opfullname','opemail','opphone','alertemail', 'allowfrom', 'allowinternalapi');
    my %oldvals;
    if ($obj->{'allowfrom'} && $obj->{'allowfrom'} ne '--') {
        my @allows = split(/,\s*/, $obj->{'allowfrom'});
        $obj->{'allowfrom'} = '';
        foreach my $ip (@allows) {
            $obj->{'allowfrom'}  .= "$1$2, " if ($ip =~ /(\d+\.\d+\.\d+\.\d+)(\/\d+)?/);
        }
        $obj->{'allowfrom'} = substr($obj->{'allowfrom'},0,-2);
        unless ($obj->{'allowfrom'}) {
            $postreply .= "Status=Error Account not updated\n";
            return $postreply;
        }
    }

    foreach my $prop (@props) {
        if ($obj->{$prop}) {
            $obj->{$prop} = '' if ($obj->{$prop} eq '--');
            $oldvals{$prop} = $userreg{$user}->{$prop};
            $userreg{$user}->{$prop} = decode('utf8', $obj->{$prop});
        }
    }

    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};
    unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>1}, $Stabile::dbopts)) ) {return "Unable to access user register"};
    my $alertmatch;
    foreach my $sysvalref (values %register) {
        if ($user eq $sysvalref->{'user'}) {
            my $sysuuid = $sysvalref->{'uuid'};
            foreach my $prop (@props) {
                my $val = $obj->{$prop};
                if ($val) {
                    $val = '' if ($val eq '--');
                    # Does this system have the same value as the old user value or, equivalently, is it empty?
                    if (!$sysvalref->{$prop} || $sysvalref->{$prop} eq $oldvals{$prop}) {
                    #    $postreply .= "Resetting system prop $prop to $val\n";
                        $sysvalref->{$prop} = ''; # An empty val refers to parent (user) val
                    # Update children
                        foreach my $domvalref (values %domreg) {
                            if ($domvalref->{'user'} eq $user && ($domvalref->{'system'} eq $sysuuid || $domvalref->{'system'} eq '--' || !$domvalref->{'system'})) {
                                if (!$domvalref->{$prop} || $domvalref->{$prop} eq $oldvals{$prop}) {
                                    $domvalref->{$prop} = '';
                                    if ($prop eq 'alertemail') {
                                        if (change_monitor_email($domvalref->{'uuid'}, $val, $oldvals{$prop})) {
                                            $alertmatch = 1;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    #`/usr/bin/moncmd reset keepstate` if ($alertmatch);
    tied(%domreg)->commit;
    tied(%userreg)->commit;
    untie %domreg;
    untie %userreg;
    $postreply .= "Status=OK Account updated\n";
    # Send changes to origo.io
    $Stabile::Users::console = 1;
    require "$Stabile::basedir/cgi/users.cgi";
    $postreply .= Stabile::Users::sendEngineUser($user) if ($enginelinked);
    $main::updateUI->({tab=>'home', user=>$user, type=>'update', message=>"Account updated"});
    return $postreply;
}

sub do_listuptime {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:yearmonth,uuid,format:
List uptime for defined monitors. If uuid is supplied, only uptime for matching server or servers belonging to matching
system is shown. Format is either html or json.
END
    }
    my $format = $obj->{'format'};
    my $yearmonth = $obj->{'yearmonth'} || "$year-$month";
    my $pathid = $yearmonth . ':';
    my $name;

    my %sysdoms;
    if ($uuid && $register{$uuid}) {
        $name = $register{$uuid}->{'name'};
        foreach my $valref (values %domreg) {
            $sysdoms{$valref->{'uuid'}} = $uuid if ($valref->{system} eq $uuid);
        }
    } else {
        $pathid .= $uuid;
        $name = $domreg{$uuid}->{'name'} if ($domreg{$uuid});
    }
    my %uptimes;
    my $jtext = {};
    my @csvrows;

    unless ($pathid =~ /\// || $pathid =~ /\./) { # Security check
        my $path = "/var/log/stabile/$pathid*"; # trailing / is required. No $pathid lists all files in log dir.
        my $utext = '';
        my %numfiles;
        my %sumupp;
        ## loop through the files contained in the directory
        for my $eachFile (bsd_glob($path.'*')) {
            if (!(-d $eachFile) && $eachFile =~ /\/var\/log\/stabile\/(.+):(.+):(.+)/) {
                my $ymonth = $1;
                my $domuuid = $2;
                my $service = $3;
                next unless ($domreg{$domuuid});
                my $servername = $domreg{$domuuid}->{'name'};
                if ($domreg{$domuuid}->{'user'} eq $user) {
                    next if (%sysdoms && !$sysdoms{$domuuid}); # If we are listing a system, match system uuid
                    open(FILE, $eachFile) or {print("Unable to access $eachFile")};
                    @lines = <FILE>;
                    close(FILE);
                    my $starttime;
                    my $lastup;
                    my $firststamp; # First timestamp of measuring period
                    my $laststamp; # Last timestamp of measuring period
                    my $curstate = 'UNKNOWN';
                    my $dstate = 'UNKNOWN';
                    my ($y, $m) = split('-', $ymonth);
                    my $timespan = 0;
                    my $dtime = 0; # Time disabled
                    my $lastdtime = 0;
                    my $uptime = 0;
                    foreach my $line (@lines) {
                        my ($timestamp, $event, $summary, $ptime) = split(/, */,$line);
                        if (!$starttime) { # First line
                            $starttime = $timestamp;
                            # Find 00:00 of first day of month - http://www.perlmonks.org/?node_id=97120
                            $firststamp = POSIX::mktime(0,0,0,1,$m-1,$year-1900,0,0,-1);
                            # Round to month start if within 15 min
                            $starttime = $firststamp if ($starttime-$firststamp<15*60);
                            $lastup = $starttime if ($event eq 'STARTUP' || $event eq 'UP');
                            $curstate = 'UP'; # Assume up - down alerts are always triggered
                        }
                        if ($event eq 'UP') {
                            if ($curstate eq 'UP') {
                                $uptime += ($timestamp - $lastup) if ($lastup);
                            }
                            $lastup = $timestamp;
                            $curstate = 'UP';
                        } elsif ($event eq 'DOWN') {
                            if ($curstate eq 'UP' && $lastup!=$starttime) { # If down is immediately after startup - dont count uptime
                                $uptime += ($timestamp - $lastup) if ($lastup);
                                $lastup = $timestamp;
                            }
                            $curstate = 'DOWN';
                        } elsif ($event eq 'STARTUP') {
                        } elsif ($event eq 'DISABLE' && $curstate ne 'UNKNOWN') {
                            if ($curstate eq 'UP') {
                                $uptime += ($timestamp - $lastup) if ($lastup);
                                $lastup = $timestamp;
                            }
                            $lastdtime = $timestamp;
                            $dstate = $curstate;
                            $curstate = 'UNKNOWN';
                        } elsif ($event eq 'ENABLE') {
                            if ($dstate eq 'UP' && $curstate eq 'UNKNOWN') {
                                $lastup = $timestamp;
                            }
                            $curstate = 'UP';
                        }
                        # All non-disable events must mean monitor is enabled again
                        if ($event ne 'DISABLE') {
                            if ($lastdtime) {
                                $dtime += ($timestamp - $lastdtime);
                                $lastdtime = 0;
                            }
                        }

                    }
                    if ($ymonth ne "$year-$month") { # If not current month, assume monitoring to end of month
                        # Find 00:00 of first day of next month - http://www.perlmonks.org/?node_id=97120
                        $laststamp = POSIX::mktime(0,0,0,1,$m,$year-1900,0,0,-1);
                    } else {
                        $laststamp = $current_time;
                    }
                    if ($curstate eq 'UP' && !$lastdtime && $lastup) {
                        $uptime += ($laststamp - $lastup);
                    }
                    if ($lastdtime) {
                        $dtime += ($laststamp - $lastdtime);
                    }
                    $timespan = $laststamp - $starttime;
                    $uptimes{"$domuuid:$service"}->{'timespan'} = $timespan;
                    $uptimes{"$domuuid:$service"}->{'uptime'} = $uptime;
                    my $timespanh = int(0.5 + 100*$timespan/3600)/100;
                    my $dtimeh = int(0.5 + 100*$dtime/3600)/100;
                    my $uptimeh = int(0.5 + 100*$uptime/3600)/100;
                    my $upp = int(0.5+ 10000*$uptime/($timespan-$dtime) ) / 100;
                    $sumupp{$service} += $upp;
                    $numfiles{$service} += 1;

                    utf8::decode($servername);

                    $utext .= qq[<div class="uptime_header">$service on $servername:</div>\n];
                    my $color = ($upp<98)?'red':'green';
                    $utext .= qq[<span style="color: $color;">Uptime: $uptimeh hours ($upp%)</span>\n];
                    $utext .= qq{[timespan: $timespanh hours, \n};
                    $utext .= qq{disabled: $dtimeh hours]\n};

                    $jtext->{$domuuid}->{'servername'} = $servername;
                    $jtext->{$domuuid}->{$service}->{'uptime'} = $upp;
                    $jtext->{$domuuid}->{$service}->{'uptimeh'} = $uptimeh;
                    $jtext->{$domuuid}->{$service}->{'color'} = ($upp<98)?'red':'green';
                    $jtext->{$domuuid}->{$service}->{'disabledtimeh'} = $dtimeh;
                    $jtext->{$domuuid}->{$service}->{'timespanh'} = $timespanh;

                    push @csvrows, {serveruuid=>$domuuid, service=>$service, servername=>$servername, uptime=>$upp, uptimeh=>$uptimeh, color=>($upp<98)?'red':'green',disabledtimeh=>$dtimeh, timespanh=>$timespanh, yearmonth=>$yearmonth};
                }
            }
        }
        my @avgtxt;
        my $alertclass = "info";
        my $compcolor;
        $jtext->{'averages'} = {};
        $jtext->{'year-month'} = $yearmonth;
        foreach $svc (keys %sumupp) {
            my $avgupp = int(0.5 + 100*$sumupp{$svc}/$numfiles{$svc})/100;
            my $color = ($avgupp<98)?'red':'green';
            push @avgtxt, qq[<span style="color: $color;" class="uptime_header">$svc: $avgupp%</span>\n];
            $jtext->{'averages'}->{$svc}->{'uptime'} = $avgupp;
            $jtext->{'averages'}->{$svc}->{'color'} = $color;
            $compcolor = ($compcolor)? ( ($compcolor eq $color)? $color : 'info' ) : $color;
        }
        $alertclass = "warning" if ($compcolor eq 'red');
        $alertclass = "success" if ($compcolor eq 'green');
        $postreply = header();
        if ($name) {
            $postreply .= qq[<div class="alert alert-$alertclass uptime_alert"><h4 class="uptime_header">Average uptime for $name:</h4>\n<div style="margin-top:10px;">\n];
        } else {
            $postreply .= qq[<div class="alert alert-$alertclass uptime_alert"><h4 class="uptime_header">Average uptime report</h4>\n<div style="margin-top:10px;">\n];
        }
        $postreply .= join(", ", @avgtxt);
        my $uuidlink = "&uuid=$uuid" if ($uuid);
        $postreply .= qq[</div></div><hr class="uptime_line"><h5 class="uptime_header">Uptime details: (<span><a href="/stabile/systems?action=listuptime&format=csv$uuidlink&yearmonth=$yearmonth" target="blank" title="Download as CSV">csv</a></span>)</h5>\n];
        $postreply .= "<span class=\"uptime_text\">$utext</span>";
    }
    if ($params{'format'} eq 'csv') {
        $postreply = header("text/plain");
        csv(in => \@csvrows, out => \my $csvdata, key => "servername");
        $postreply .= $csvdata;
    } elsif ($format ne 'html') {
        $postreply = to_json($jtext, {pretty=>1});
    }
    return $postreply;
}

sub do_appstore {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:appid,callback:
Look up app info for app with given appid in appstore on origo.io. Data is returned as padded JSON (JSONP).
Optionally provide name of your JSONP callback function, which should parse the returned script data.
END
    }
    my $appid = $params{'appid'};
    my $callback = $params{'callback'};
    if ($appid) {
        $postreply = header("application/javascript");
        $postreply .= $main::postToOrigo->($engineid, 'engineappstore', $appid, 'appid', $callback);
    } else {
        $postreply = qq|Status=Error Please provide appid|;
    }
    return $postreply;
}

sub do_resetmonitoring {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Reset mon daemon while keeping states.
END
    }
    saveOpstatus();
    $postreply = "Status=OK " . `/usr/bin/moncmd reset keepstate`;
    return $postreply;
}

sub do_installsystem {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:installsystem,installaccount:
Helper function to initiate the installation of a new stack with system ID [installsystem] to account [installaccount] by redirecting with appropriate cookies set.
END
    }
    my $installsystem = $obj->{'installsystem'};
    my $installaccount = $obj->{'installaccount'};
    my $systemcookie;
    my $ia_cookie;
    my $sa_cookie;

    push(@INC, "$Stabile::basedir/auth");
    require Apache::AuthTkt;# 0.03;
    require AuthTktConfig;
    my $at = Apache::AuthTkt->new(conf => $ENV{MOD_AUTH_TKT_CONF});
    my ($server_name, $server_port) = split /:/, $ENV{HTTP_HOST} if $ENV{HTTP_HOST};
    $server_name ||= $ENV{SERVER_NAME} if $ENV{SERVER_NAME};
    $server_port ||= $ENV{SERVER_PORT} if $ENV{SERVER_PORT};
    my $AUTH_DOMAIN = $at->domain || $server_name;
    my @auth_domain = $AUTH_DOMAIN ? ( -domain => $AUTH_DOMAIN ) : ();

    if ($installsystem) {
        $systemcookie = CGI::Cookie->new(
            -name => 'installsystem',
            -value => "$installsystem",
            -path => '/',
            @auth_domain
        );
    };
    if ($installaccount) {
        $ia_cookie = CGI::Cookie->new(
            -name => 'installaccount',
            -value => "$installaccount",
            -path => '/',
            @auth_domain
        );
        $sa_cookie = CGI::Cookie->new(
            -name => 'steamaccount',
            -value => "$installaccount",
            -path => '/',
            @auth_domain
        );
    };

    $tktcookie = CGI::Cookie->new(
        -name => 'tktuser',
        -value => "$tktuser",
        -path => '/',
        @auth_domain
    );

    $postreply = redirect(
        -uri => '/stabile/mainvalve/',
        -cookie => [$tktcookie, $systemcookie, $ia_cookie, $sa_cookie]
    );
    return $postreply;
}

sub Changemonitoremail {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,email:
Change the email for all monitors belonging to server with given uuid. May be called with command line switches -u server uuid, -m old email, -k new email.
END
    }
    if ($isreadonly) {
        $postreply = "Status=Error Not permitted\n";
    } else {
        my $serveruuid = $options{u} || $uuid;
        my $email = $options{k} || $obj->{'email'};
        if (change_monitor_email($serveruuid, $email)) {
            $postreply = "Status=OK " . `/usr/bin/moncmd reset keepstate`;
        } else {
            $postreply = "Status=Error There was a problem changing monitor email for $serveruuid\n";
        }
    }
    return $postreply;
}

sub do_getmetrics {
    my ($suuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,metric,from,until,last,format:
Get performance and load metrics in JSON format from Graphite backend. [metric] is one of: cpuload, diskreads, diskwrites, networkactivityrx, networkactivitytx
From and until are Unix timestamps. Alternatively specify "last" number of seconds you want metrics for. Format is "json" (default) or "csv".
END
    }
    my $metric = $params{metric} || "cpuLoad";
    my $now = time();
    my $from = $params{"from"} || ($now-$params{"last"}) || ($now-300);
    my $until = $params{"until"} || $now;

    my @uuids;
    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};

    if ($domreg{$suuid}) { # We are dealing with a server
        push @uuids, $suuid;
    } else { # We are dealing with a system
        foreach my $valref (values %domreg) {
            my $sysuuid = $valref->{'system'};
            push @uuids, $valref->{'uuid'} if ($sysuuid eq $suuid)
        }
    }
    untie %domreg;

    my @datapoints;
    my @targets;
    my $all;
    my $jobj = [];
    foreach my $uuid (@uuids) {
        next unless (-e "/var/lib/graphite/whisper/domains/$uuid");
        my $url = "https://127.0.0.1/graphite/graphite.wsgi/render?format=json&from=$from&until=$until&target=domains.$uuid.$metric";
        my $jstats = `curl -k "$url"`;
        $jobj = from_json($jstats);
        push @targets, $jobj->[0]->{target};
        if ($jobj->[0]->{target}) {
            if (@datapoints) {
                my $j=0;
                foreach my $p ( @{$jobj->[0]->{datapoints}} ) {
#                    print "adding: ", $datapoints[$j]->[0], " + ", $p->[0];
                    $datapoints[$j]->[0] += $p->[0];
#                    print " = ", $datapoints[$j]->[0], " to ",$datapoints[$j]->[1],  "\n";
                    $j++;
                }
            } else {
                @datapoints = @{$jobj->[0]->{datapoints}};
            }
        }
    }
    pop @datapoints; # We discard the last datapoint because of possible clock drift
    $all = [{targets=>\@targets, datapoints=>\@datapoints, period=>{from=>$from, until=>$until, span=>$until-$from}}];
    if ($params{'format'} eq 'csv') {
        $postreply = header("text/plain");
        csv(in => \@datapoints, out => \my $csvdata);
        $postreply .= $csvdata;
    } else {
        $postreply = to_json($all);
    }
    return $postreply;
}

sub do_metrics {
    my ($suuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,metric,from,to:
Get performance and load metrics in JSON format from RRD backend. [metric] is one of: cpuload, diskreads, diskwrites, networkactivityrx, networkactivitytx
From and to are Unix timestamps.
END
    }

    my $from = $params{"from"};
    my $to = $params{"to"};
    my $dif = $to - $from;
    my $now = time();

    my @items;
    my %cpuLoad = ();
    my %networkActivityRX = ();
    my %networkActivityTX = ();
    my %diskReads = ();
    my %diskWrites = ();

    my $i = 0;
    my @uuids;
    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};

    if ($domreg{$suuid}) { # We are dealing with a server
        push @uuids, $suuid;
    } else { # We are dealing with a system
        foreach my $valref (values %domreg) {
            my $sysuuid = $valref->{'system'};
            push @uuids, $valref->{'uuid'} if ($sysuuid eq $suuid)
        }
    }
    untie %domreg;

    foreach my $uuid (@uuids) {
        next unless hasRRD($uuid);
        $i++;
        # Fetch data from RRD buckets...
        my $rrd = RRDTool::OO->new(file =>"/var/cache/rrdtool/".$uuid."_highres.rrd");
        my $last = $rrd->last();
        $rrd->fetch_start(start => $now-$dif, end=> $now);
        while(my($timestamp, @value) = $rrd->fetch_next()) {
            last if ($timestamp >= $last && $now-$last<20);
            my $domain_cpuTime = shift(@value);
            my $blk_hda_rdBytes = shift(@value);
            my $blk_hda_wrBytes = shift(@value);
            my $if_vnet0_rxBytes = shift(@value);
            my $if_vnet0_txBytes = shift(@value);

            # domain_cpuTime is avg. nanosecs spent pr. 1s
            # convert to value [0;1]
            $domain_cpuTime = $domain_cpuTime / 10**9 if ($domain_cpuTime);
            $cpuLoad{$timestamp} +=  $domain_cpuTime;

            $blk_hda_rdBytes = $blk_hda_rdBytes if ($blk_hda_rdBytes);
            $diskReads{$timestamp} += $blk_hda_rdBytes;

            $blk_hda_wrBytes = $blk_hda_wrBytes if ($blk_hda_wrBytes);
            $diskWrites{$timestamp} += $blk_hda_wrBytes;

            $networkActivityRX{$timestamp} += $if_vnet0_rxBytes;
            $networkActivityTX{$timestamp} += $if_vnet0_txBytes;
        }
    }
    my @t = ( $now-$dif, $now);
    my @a = (undef, undef);
    $i = $i || 1;

    my $item = ();
    $item->{"uuid"} = $suuid if ($suuid);
    my @tstamps = sort keys %cpuLoad;
    $item->{"timestamps"} = \@tstamps || \@t;

    if ($params{"metric"} eq "cpuload" || $params{'cpuload'}) {
        my @vals;
        my $load = int(100*$cpuLoad{$_})/100;
        $load = $i if  ($cpuLoad{$_} > $i);
        foreach(@tstamps) {push @vals, $load};
        $item->{"cpuload"} = \@vals || \@a;
    }
    elsif ($params{"metric"} eq "diskreads" || $params{'diskReads'}) {
        my @vals;
        foreach(@tstamps) {push @vals, int(100*$diskReads{$_})/100;};
        $item->{"diskReads"} = \@vals || \@a;
      }
    elsif ($params{"metric"} eq "diskwrites" || $params{'diskWrites'}) {
        my @vals;
        foreach(@tstamps) {push @vals, int(100*$diskWrites{$_})/100;};
        $item->{"diskWrites"} = \@vals || \@a;
    }
    elsif ($params{"metric"} eq "networkactivityrx" || $params{'networkactivityrx'}) {
        my @vals;
        foreach(@tstamps) {push @vals, int(100*$networkActivityRX{$_})/100;};
        $item->{"networkactivityrx"} = \@vals || \@a;
    }
    elsif ($params{"metric"} eq "networkactivitytx" || $params{'networkactivitytx'}) {
        my @vals;
        foreach(@tstamps) {push @vals, int(100*$networkActivityTX{$_})/100;};
        $item->{"networkactivitytx"} = \@vals || \@a;
    }
    push @items, $item;
    $postreply .= to_json(\@items, {pretty=>1});
    return $postreply;
}

sub hasRRD {
	my($uuid) = @_;
	my $rrd_file = "/var/cache/rrdtool/".$uuid."_highres.rrd";

	if ((not -e $rrd_file) and ($uuid)) {
		return(0);
	} else {
		return(1);
	}
}

sub do_packages_remove {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
DELETE:uuid:
Remove packages belonging to server or system with given uuid.
END
    }
    my $issystem = $obj->{"issystem"} || $register{$uuid};
    unless ( tie(%packreg,'Tie::DBI', Hash::Merge::merge({table=>'packages', key=>'id'}, $Stabile::dbopts)) ) {return "Unable to access package register"};
    my @domains;
    if ($issystem) {
        foreach my $valref (values %domreg) {
            if (($valref->{'system'} eq $uuid || $uuid eq '*')
                    && ($valref->{'user'} eq $user || $fulllist)) {
                push(@domains, $valref->{'uuid'});
            }
        }
    } else { # Allow if domain no longer exists or belongs to user
        push(@domains, $uuid) if (!$domreg{$uuid} || $domreg{$uuid}->{'user'} eq $user || $fulllist);
    }
    foreach my $domuuid (@domains) {
        foreach my $packref (values %packreg) {
            my $id = $packref->{'id'};
            if (substr($id, 0,36) eq $domuuid || ($uuid eq '*' && $packref->{'user'} eq $user)) {
                delete $packreg{$id};
            }
        }
    }
    tied(%packreg)->commit;# if (%packreg);
    if ($issystem && $register{$uuid}) {
        $postreply = "Status=OK Cleared packages for $register{$uuid}->{'name'}\n";
    } elsif ($domreg{$uuid}) {
        $postreply = "Status=OK Cleared packages for $domreg{$uuid}->{'name'}\n";
    } else {
        $postreply = "Status=OK Cleared packages. System not registered\n";
    }
    return $postreply;
}

sub Packages_load {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
POST:uuid:
Load list of installed software packages that are installed on the image. Image must contain a valid OS.
END
    }
    if (!$isreadonly) {
        unless ( tie(%packreg,'Tie::DBI', Hash::Merge::merge({table=>'packages', key=>'id'}, $Stabile::dbopts)) ) {return "Unable to access package register"};
        unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};
        my $curimg;
        my $apps;
        my @domains;
        my $issystem = $obj->{'issystem'};
        if ($issystem) {
            foreach my $valref (values %domreg) {
                if (($valref->{'system'} eq $uuid || $uuid eq '*')
                        && ($valref->{'user'} eq $user || $fulllist)) {
                    push(@domains, $valref->{'uuid'});
                }
            }
        } else {
            push(@domains, $uuid) if ($domreg{$uuid}->{'user'} eq $user || $fulllist);
        }

        foreach my $domuuid (@domains) {
            if ($domreg{$domuuid}) {
                $curimg = $domreg{$domuuid}->{'image'};
                $apps = getPackages($curimg);
                if ($apps) {
                    my @packages;
                    my @packages2;
                    open my $fh, '<', \$apps or die $!;
                    my $distro;
                    my $hostname;
                    my $i;
                    while (<$fh>) {
                        if (!$distro) {
                            $distro = $_;
                            chomp $distro;
                        } elsif (!$hostname) {
                            $hostname = $_;
                            chomp $hostname;
                        } elsif ($_ =~ /\[(\d+)\]/) {
                            push @packages2, $packages[$i];
                            $i = $1;
                        } elsif ($_ =~ /(\S+): (.+)/ && $2) {
                            $packages[$i]->{$1} = $2;
                        }
                    }
                    close $fh or die $!;
                    $domreg{$domuuid}->{'os'} = $distro;
                    $domreg{$domuuid}->{'hostname'} = $hostname;
                    foreach $package (@packages) {
                        my $id = "$domuuid-$package->{'app_name'}";
                        $packreg{$id} = $package;
                        $packreg{$id}->{'app_display_name'} = $packreg{$id}->{'app_name'} unless ($packreg{$id}->{'app_display_name'});
                        $packreg{$id}->{'domuuid'} = $domuuid;
                        $packreg{$id}->{'user'} = $user;
                    }
                    $postreply .= "Status=OK Updated packages for $domreg{$domuuid}->{'name'}\n";
                } else {
                    $domreg{$domuuid}->{'os'} = 'unknown';
                    $domreg{$domuuid}->{'hostname'} = 'unknown';
                    $postreply .= "Status=Error Could not update packages for $domreg{$domuuid}->{'name'}";
                }
            }
        }
        tied(%packreg)->commit;
        tied(%domreg)->commit;
        untie %domreg;
        untie %packreg;

    } else {
        $postreply .= "Status=Error Not allowed\n";
    }
    return $postreply;
}

sub do_packages {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
Handling of packages
END
    }

    unless ( tie(%packreg,'Tie::DBI', Hash::Merge::merge({table=>'packages', key=>'id'}, $Stabile::dbopts)) ) {return "Unable to access package register"};
    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};

    # List packages
    my @packregvalues = values %packreg;
    my @curregvalues;
    my %packhash;
    my %sysdoms; # Build list of members of system
    foreach $sysdom (values %domreg) {
        if ($sysdom->{'system'} eq $curuuid) {
            $sysdoms{$sysdom->{'uuid'}} = $curuuid;
        }
    }
    foreach my $valref (@packregvalues) {
        if ($valref->{'user'} eq $user || $fulllist) {
            if ((!$curuuid || $curuuid eq '*') # List packages from all servers
                || ($domreg{$curuuid} && $curuuid eq $valref->{'domuuid'}) # List packages from a single server
                || ($register{$curuuid} && $sysdoms{ $valref->{'domuuid'} }) # List packages from multiple servers - a system
            ) {
            #    push(@curregvalues, $valref);
                my $packid = "$valref->{'app_display_name'}:$valref->{'app_version'}";
                if ($packhash{$packid}) {
                    ($packhash{$packid}->{'app_count'})++;
                } else {
                    $packhash{$packid} = {
                        app_display_name=>$valref->{'app_display_name'},
                        app_name=>$valref->{'app_name'},
                        app_release=>$valref->{'app_release'},
                    #    app_publisher=>$valref->{'app_publisher'},
                        app_version=>$valref->{'app_version'},
                        app_count=>1
                    }
                }
            }
        }
    }
    my @sorted_packs = sort {$a->{'app_display_name'} cmp $b->{'app_display_name'}} values %packhash;
    if ($obj->{format} eq 'html') {
        my $res;
        $res .= qq[<tr><th>Name</th><th>Version</th><th>Count</th></tr>\n];
        foreach my $valref (@sorted_packs) {
            $res .= qq[<tr><td>$valref->{'app_display_name'}</td><td>$valref->{'app_version'}</td><td>$valref->{'app_count'}</td></tr>\n];
        }
        $postreply .= qq[<table cellspacing="0" frame="void" rules="rows" class="systemTables">\n$res</table>\n];
    } elsif ($obj->{'format'} eq 'csv') {
        $postreply = header("text/plain");
        csv(in => \@sorted_packs, out => \my $csvdata);
        $postreply .= $csvdata;
    } else {
        $postreply .= to_json(\@sorted_packs);
    }
    untie %domreg;
    untie %packreg;
    return $postreply;
}

sub Buildsystem {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:name, master, storagepool, system, instances, networkuuid, bschedule, networktype1, ports, memory, vcpu, diskbus, cdrom, boot, nicmodel1, nicmac1, networkuuid2, nicmac2, storagepool2, monitors, managementlink, start:
Build a complete system from cloned master image.
master is the only required parameter. Set [storagepool2] to -1 if you want data images to be put on node storage.
END
    }
    $curuuid = $uuid unless ($curuuid);
    $postreply = buildSystem(
        $obj->{name},
        $obj->{master},
        $obj->{storagepool},
        $obj->{system},
        $obj->{instances},
        $obj->{networkuuid1},
        $obj->{bschedule},
        $obj->{networktype1},
        $obj->{ports},
        $obj->{memory},
        $obj->{vcpu},
        $obj->{diskbus},
        $obj->{cdrom},
        $obj->{boot},
        $obj->{nicmodel1},
        $obj->{nicmac1},
        $obj->{networkuuid2},
        $obj->{nicmac2},
        $obj->{monitors},
        $obj->{managementlink},
        $obj->{start},
        $obj->{domuuid},
        $obj->{storagepool2}
    );
    
    return $postreply;
}

sub Upgradesystem {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,internalip:
Upgrades a system
END
    }
    my $internalip = $params{'internalip'};
    $postreply = upgradeSystem($internalip);
    return $postreply;
}

sub Removeusersystems {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Removes all systems belonging to a user, i.e. completely deletes all servers, images and networks belonging to an account.
Use with extreme care.
END
    }
    $postreply = removeusersystems($user);
    return $postreply;
}

sub Removesystem {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
Removes specified system, i.e. completely deletes all servers, images, networks and backups belonging to a system.
Use with care.
END
    }
    $postreply = remove($uuid, 0, 1);
    return $postreply;
}

1;

# Print list of available actions on objects
sub do_plainhelp {
    my $res;
    $res .= header('text/plain') unless $console;
    $res .= <<END
new [name="name"]
start
suspend
resume
shutdown
destroy
buildsystem [master, storagepool, system (uuid), instances, networkuuid1,bschedule,
networktype1, ports, memory, vcpu, diskbus, cdrom, boot, nicmodel1, nicmac1, networkuuid2,
nicmac2, monitors, start]
removesystem
updateaccountinfo
resettoaccountinfo

END
;
}

# Save current mon status to /etc/stabile/opstatus, in order to preserve state when reloading mon
sub saveOpstatus {
    my $deleteid = shift;
    my %opstatus = getSavedOpstatus();
    my @monarray = split("\n", `/usr/bin/moncmd list opstatus`);
    my $opfile = "/etc/stabile/opstatus";
    open(FILE, ">$opfile") or {throw Error::Simple("Unable to write $opfile")};
    foreach my $line (@monarray) {
        my @pairs = split(/ /,$line);
        my %h;
        my $ALERT;
        foreach my $pair (@pairs) {
            my ($key, $val) = split(/=/,$pair);
            $obj->{$key} = $val;
        }
        my $ops = $opstatus{"$group:$service"};
        my $group = $obj->{'group'};
        my $service = $obj->{'service'};
        my $curstatus = $ops->{'opstatus'};
        my $curack = $ops->{'ack'};
        my $curackcomment = $ops->{'ackcomment'};
        my $curline = $ops->{'line'};
        if ($deleteid && $deleteid eq "$group:$service") {
            ; # Don't write line for service we are deleting
        } elsif (($obj->{'opstatus'} eq '0' || $obj->{'opstatus'} eq '7') && $curack && $curstatus eq '0') {
            # A failure has been acknowledged and service is still down
            print FILE "$curline\n";
            $ALERT = ($obj->{'opstatus'}?'UP':'DOWN');
        } elsif (($obj->{'opstatus'} || $obj->{'opstatus'} eq '0') && $obj->{'opstatus'} ne '7') {
            print FILE "$line\n";
            $ALERT = ($obj->{'opstatus'}?'UP':'DOWN');
        } elsif (($curstatus || $curstatus eq '0') && $curstatus ne '7') {
            print FILE "$curline\n";
            $ALERT = ($obj->{'opstatus'}?'UP':'DOWN');
        } else {
            # Don't write anything if neither is different from 7
        }
    # Create empty log file if it does not exist
        my $oplogfile = "/var/log/stabile/$year-$month:$group:$service";
        unless (-s $oplogfile) {
            if ($group && $service && $ALERT) {
                `/usr/bin/touch "$oplogfile"`;
                `/bin/chown mon:mon "$oplogfile"`;
                my $logline = "$current_time, $ALERT, MARK, $pretty_time";
                `/bin/echo >> $oplogfile "$logline"`;
            }
        }
    }
    close (FILE);
    #if ((!-e $opfile) || ($current_time - (stat($opfile))[9] > 120) ) {
    #    `/usr/bin/moncmd list opstatus > $opfile`;
    #}
}

sub getSavedOpstatus {
    my $dounbackslash = shift;
    my $opfile = "/etc/stabile/opstatus";
    my @oparray;
    my %opstatus;
    # Build hash (%opstatus) with opstatus'es etc. to use for services that are in state unknown because of mon reload
    if (-e $opfile) {
        open(FILE, $opfile) or {throw Error::Simple("Unable to read $opfile")};
        @oparray = <FILE>;
        close(FILE);
        foreach my $line (@oparray) {
            my @pairs = split(/ /,$line);
            my %h;
            foreach my $pair (@pairs) {
                my ($key, $val) = split(/=/,$pair);
                if ($key eq 'last_result' || !$dounbackslash) {
                    $obj->{$key} = $val;
                } else {
                    $val =~ s/\\/\\x/g;
                    $obj->{$key} = unbackslash($val);
                }
            }
            $obj->{'line'} = $line;
            $opstatus{"$obj->{'group'}:$obj->{'service'}"} = \%h;
        }
    }
    return %opstatus;
}

sub getOpstatus {
    my ($selgroup, $selservice, $usemoncmd) = @_;
    my %opcodes = ("", "checking", "0", "down", "1", "ok", "3", "3", "4", "4", "5", "5", "6", "6", "7", "checking", "9", "disabled");
    my %s;
    my %opstatus;
    my %savedopstatus = getSavedOpstatus(1);
    my %sysdoms;

    my %disabled;
    my %desc;
    my @dislist = split(/\n/, `/usr/bin/moncmd list disabled`);
    foreach my $disline (@dislist) {
        my ($a, $b, $c, $d) = split(' ', $disline);
        $disabled{"$b" . ($d?":$d":'')} = 1;
    };
    my %emails;
    my @emaillist = split(/\n/, `/bin/cat /etc/mon/mon.cf`);
    my $emailuuid;
    foreach my $eline (@emaillist) {
        my ($a, $b, $c, $d) = split(/ +/, $eline, 4);
        if ($a eq 'watch') {
            if ($b =~ /\S+-\S+-\S+-\S+-\S+/) {$emailuuid = $b;}
            else {$emailuuid = ''};
        }
        $emails{$emailuuid} = $d if ($emailuuid && $b eq 'alert' && $c eq 'stabile.alert');
    };

    # We are dealing with a system group rather than a domain, build hash of domains in system
    if ($selgroup && !$domreg{$selgroup} && $register{$selgroup}) {
        foreach my $valref (values %domreg) {
            $sysdoms{$valref->{'uuid'}} = $selgroup if ($valref->{system} eq $selgroup);
        }
    }
    if ($usemoncmd) {
        my @oparray = split("\n", `/usr/bin/moncmd list opstatus`);
        foreach my $line (@oparray) {
            my @pairs = split(/ /,$line);
            my %h;
            foreach my $pair (@pairs) {
                my ($key, $val) = split(/=/,$pair);
                if ($key eq 'last_result') {
                    $obj->{$key} = $val;
                } else {
                    $val =~ s/\\/\\x/g;
                    $obj->{$key} = unbackslash($val);
                }
            }
            if (!$selgroup || $sysdoms{$obj->{'group'}}
                (!$selservice && $selgroup eq $obj->{'group'}) ||
                ($selgroup eq $obj->{'group'} && $selservice eq $obj->{'service'})
            )
            {
                #$obj->{'line'} = $line;
                #$opstatus{"$obj->{'group'}:$obj->{'service'}"} = \%h;
                $s{$obj->{'group'}}->{$obj->{'service'}} = \%h if($obj->{'group'});
            }
        }

    } else {
        my $monc;
        $monc = new Mon::Client (
            host => "127.0.0.1"
        );
        $monc->connect();
        %desc = $monc->list_descriptions; # Get descriptions
        #%disabled = $monc->list_disabled;
        $selgroup = '' if (%sysdoms);
        my @selection = [$selgroup, $selservice];
        if ($selgroup && $selservice) {%s = $monc->list_opstatus( @selection );}
        elsif ($selgroup) {%s = $monc->list_opstatus( (@selection) );}# List selection
        else {%s = $monc->list_opstatus;} # List all
        $monc->disconnect();
    }

    foreach my $group (keys %s) {
        if ($domreg{$group} && ($domreg{$group}->{'user'} eq $user || $fulllist)) {
            foreach my $service (values %{$s{$group}}) {

                next if (%sysdoms && !$sysdoms{$group});
                next unless ($service->{'monitor'});
                my $ostatus = $service->{'opstatus'};
                my $id = "$group:$service->{'service'}";
                if (%sysdoms) {
                    $service->{'system'} = $sysdoms{$group};
                }
                if ($ostatus == 7 && $savedopstatus{$id}) { # Get status etc. from %savedopstatus because mon has recently been reloaded
                    $service->{'opstatus'} = $savedopstatus{$id}->{'opstatus'};
                    $service->{'last_success'} = $savedopstatus{$id}->{'last_success'};
                    $service->{'last_check'} = $savedopstatus{$id}->{'last_check'};
                    $service->{'last_detail'} = $savedopstatus{$id}->{'last_detail'};
                    $service->{'checking'} = "1";
                }
#                if (($ostatus == 7 || $ostatus == 0) &&  $savedopstatus{$id}->{'ack'}) { # Get ack because mon has recently been reloaded
                if ($ostatus == 7 &&  $savedopstatus{$id}->{'ack'}) { # Get ack because mon has recently been reloaded
                    $service->{'ack'} = $savedopstatus{$id}->{'ack'};
                    $service->{'ackcomment'} = $savedopstatus{$id}->{'ackcomment'};
                    $service->{'first_failure'} = $savedopstatus{$id}->{'first_failure'};
                }
                $service->{'ackcomment'} = $1 if ($service->{'ackcomment'} =~ /^: *(.*)/);
                my $status = $opcodes{$service->{'opstatus'}};
                if ($disabled{$id} || $disabled{$group}){
                    $status = 'disabled';
                    $service->{'opstatus'} = "9";
                }
                $service->{'status'} = $status;
                $service->{'id'} = $id;
                $service->{'name'} = "$domreg{$group}->{'name'} : $service->{'service'}";
                $service->{'servername'} = $domreg{$group}->{'name'};
                $service->{'serveruuid'} = $domreg{$group}->{'uuid'};
                $service->{'serverstatus'} = $domreg{$group}->{'status'};

                $service->{'serverip'} = `cat /etc/mon/mon.cf |sed -n -e 's/^hostgroup $group //p'`;

                my $desc = $desc{$group}->{$service->{'service'}};
                $desc = '' if ($desc eq '--');
                $service->{'desc'} = $desc;
                $service->{'last_detail'} =~ s/-//g;
                $service->{'last_detail'} =~ s/^\n//;
                $service->{'last_detail'} =~ s/\n+/\n/g;

                my $monitor = $service->{'monitor'};

                $service->{'request'} = $service->{'okstring'} = $service->{'port'} = $service->{'email'} = '';
                #$monitor = URI::Escape::uri_unescape($monitor);
                #if ( $monitor =~ /stabile-diskspace\.monitor\s+(\S+)\s+(\S+)\s+(\S+)/ ) {
                if ( $monitor =~ /stabile-diskspace\.monitor\s+(\S+)\s+(\S+)/ ) {
                    $service->{'request'} = $2 if ( $monitor =~ /stabile-diskspace\.monitor\s+(\S+)\s+(\S+)/ );
                    $service->{'okstring'} = $3 if ( $monitor =~ /stabile-diskspace\.monitor\s+(\S+)\s+(\S+)\s+(\S+)/ );
                }

                $service->{'okstring'} = $1 if ( $monitor =~ /--okstring \"(.*)\"/ );
                $service->{'okstring'} = $1 if ( $monitor =~ /-l \"(.*)\"/ );
#                $service->{'request'} = $2 if ( $monitor =~ /http(s*):\/\/.+\/(.*)/ );
                $service->{'request'} = $2 if ( $monitor =~ /http(s*):\/\/[^\/]+\/(.*)/ );
                $service->{'port'} = $2 if ( $monitor =~ /http(s*):\/\/.+:(\d+)/ );
                $service->{'request'} = $1 if ( $monitor =~ /--from \"(\S*)\"/ );
                $service->{'okstring'} = $1 if ( $monitor =~ /--to \"(\S*)\"/ );
                $service->{'port'} = $1 if ( $monitor =~ /--port (\d+)/ );

                $service->{'email'} = $emails{$group};

                $opstatus{$id} = $service;
                #push @monitors, $service;
            }
        }
    }
    return %opstatus;
}

sub change_monitor_email {
    my $serveruuid = shift;
    my $email = shift;
    my $match;
    if ($email && $serveruuid) {
        unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};
        if ($domreg{$serveruuid}->{'user'} eq $user || $isadmin) {
            local($^I, @ARGV) = ('.bak', "/etc/mon/mon.cf"); # $^I is the in-place edit switch
            # undef $/; # This makes <> read in the entire file in one go
            my $uuidmatch;
            while (<>) {
                if (/^watch (\S+)/) {
                    if ($1 eq $serveruuid) {$uuidmatch = $serveruuid}
                    else {$uuidmatch = ''};
                };
                if ($uuidmatch) {
                    $match = 1 if (s/(stabile\.alert) (.*)/$1 $email/);
                }
                print;
                close ARGV if eof;
        #       $match = 1 if (s/(watch $serveruuid\n.+\n.+\n.+\n.+\n.+)$oldemail(\n.+)$oldemail(\n.+)$oldemail/$1$email$2$email$3$email/g);
            }
        #    $/ = "\n";
        }
    }
    return $match;
}

# Delete all monitors belonging to a server
sub deleteMonitors {
    my ($serveruuid) = @_;
    my $match;
    if ($serveruuid) {
        if ($domreg{$serveruuid}->{'user'} eq $user || $isadmin) {
            local($^I, @ARGV) = ('.bak', "/etc/mon/mon.cf");
            # undef $/; # This makes <> read in the entire file in one go
            my $uuidmatch;
            while (<>) {
                if (/^watch (\S+)/) {
                    if ($1 eq $serveruuid) {$uuidmatch = $serveruuid}
                    else {$uuidmatch = ''};
                };
                if ($uuidmatch) {
                    $match = 1;
                } else {
                    #chomp;
                    print unless (/^hostgroup $serveruuid/);
                }
                close ARGV if eof;
            }
            #$/ = "\n";
        }
        unlink glob "/var/log/stabile/*:$serveruuid:*";
    }
    `/usr/bin/moncmd reset keepstate` if ($match);
    return $match;
}

# Add a monitors to a server when building system
sub addSimpleMonitors {
    my ($serveruuid, $email, $monitors_ref) = @_;
    my @mons = @{$monitors_ref};

    my $match;
    my $hmatch1;
    my $hmatch2;
    my $hmatch3;
    if ($serveruuid && $domreg{$serveruuid}) {
        if ($domreg{$serveruuid}->{'user'} eq $user || $isadmin) {
            my $monitors = {
                ping=>"fping.monitor",
                diskspace=>"stabile-diskspace.monitor $serveruuid",
                http=>"http_tppnp.monitor",
                https=>"http_tppnp.monitor",
                smtp=>"smtp3.monitor",
                smtps=>"smtp3.monitor",
                imap=>"imap.monitor",
                imaps=>"imap-ssl.monitor",
                ldap=>"ldap.monitor",
                telnet=>"telnet.monitor"
            };

            if (!$email) {$email = $domreg{$serveruuid}->{'alertemail'}};
            if (!$email && $register{$domreg{$serveruuid}->{'system'}}) {$email = $register{$domreg{$serveruuid}->{'system'}}->{'alertemail'}};
            if (!$email) {$email = $userreg{$user}->{'alertemail'}};

            unless (tie %networkreg,'Tie::DBI', {
                db=>'mysql:steamregister',
                table=>'networks',
                key=>'uuid',
                autocommit=>0,
                CLOBBER=>3,
                user=>$dbiuser,
                password=>$dbipasswd}) {throw Error::Simple("Stroke=Error Register could not be accessed")};

            my $networkuuid1 = $domreg{$serveruuid}->{'networkuuid1'};
            my $networktype = $networkreg{$networkuuid1}->{'type'};
            my $ip = $networkreg{$networkuuid1}->{'internalip'};
            $ip = $networkreg{$networkuuid1}->{'externalip'} if ($networktype eq 'externalip');
            $ip = '127.0.0.1' if ($networktype eq 'gateway'); #Dummy IP - we only support diskspace checks
            untie %networkreg;

            local($^I, @ARGV) = ('.bak', "/etc/mon/mon.cf");
            my $uuidmatch;
            while (<>) {
                $hmatch1=1 if (/^hostgroup/);
                $hmatch2=1 if ($hmatch1 && !/^hostgroup/);
                if ($hmatch1 && $hmatch2 && !$hmatch3) {
                    print "hostgroup $serveruuid $ip\n";
                    $hmatch3 = 1;
                }
                print;
                if (eof) {
                    print "watch $serveruuid\n";
                    foreach $service (@mons) {
                        print <<END;
    service $service
        interval 1m
        monitor $monitors->{$service}
        description --
        period
            alert stabile.alert $email
            upalert stabile.alert $email
            startupalert stabile.alert $email
            numalerts 2
            no_comp_alerts
END
;
                        my $oplogfile = "/var/log/stabile/$year-$month:$serveruuid:$service";
                        unless (-e $oplogfile) {
                            `/usr/bin/touch "$oplogfile"`;
                            `/bin/chown mon:mon "$oplogfile"`;
                            my $logline = "$current_time, UP, STARTUP, $pretty_time";
                            `/bin/echo >> $oplogfile "$logline"`;
                        }
                    }
                    close ARGV;
                }
            }
        } else {
            return "Server $serveruuid not available";
        }
    } else {
        return "Invalid uuid $serveruuid";
    }
    return "OK";
}

sub Monitors_save {
    my ($id, $action, $obj) = @_;
    if ($help) {
        return <<END
PUT:id:
Enable, disable or acknowledge a monitor. Id is of the form serveruuid:service
END
    }

    my $delete = ($action eq 'monitors_remove'); # Delete an existing monitor
    $id = $obj->{'id'} || $id; # ID in params supersedes id in path
    my $update; # Update an existing monitor?
    my $postmsg;

    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};
    unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {return "Unable to access networks register"};
    foreign_require("mon", "mon-lib.pl");
    $conf = mon::get_mon_config();
#    my @ogroups = mon::find("hostgroup", $conf);
#    my @owatches = mon::find("watch", $conf);
    my $doreset;
    my $email;

    my $serveruuid;
    my $servicename;
    if ($id =~ /(.+):(.+)/){ # List specific monitor for specific server
        $serveruuid = $1;
        $servicename = $2;
    }
    $serveruuid = $serveruuid || $obj->{'serveruuid'};
    my $desc = $obj->{'desc'};
    my $okstring = $obj->{'okstring'};
    my $request = $obj->{'request'};
    my $port = $obj->{'port'};
    $servicename = $servicename || $obj->{'service'};
    my $interval = '1'; # Number of minutes between checks
    $interval = '20' if ($servicename eq 'diskspace');
    $email = $obj->{'alertemail'};
    my $serv = $domreg{$serveruuid};
    if (!$email) {$email = $serv->{'alertemail'}};
    if (!$email && $serv->{'system'}) {$email = $register{$serv->{'system'}}->{'alertemail'}};
    if (!$email) {$email = $userreg{$user}->{'alertemail'}};
    my $networkuuid1 = $serv->{'networkuuid1'};
    my $networktype = $networkreg{$networkuuid1}->{'type'};
    my $deleteid;
    
    if (!$serveruuid || !$servicename) {
        $postmsg = qq|No monitor specified|;
        $postreply = "Status=Error $postmsg\n";
        return $postreply;
    }

    if (!$delete && $networktype eq 'gateway' && $servicename ne 'diskspace'
            && (!$obj->{'serverip'} || !($obj->{'serverip'} =~ /^\d+\.\d+\.\d+\.\d+$/) )) {
        $postmsg = qq|Invalid IP address|;
    } elsif (!$domreg{$serveruuid}) {
        $postmsg = qq|Unknown server $serveruuid|;
# Security check
    } elsif ($domreg{$serveruuid}->{'user'} ne $user) {
        $postmsg = qq|Bad server|;
    } else {
        my $monitors = {
            ping=>"fping.monitor",
            diskspace=>"stabile-diskspace.monitor",
            http=>"http_tppnp.monitor",
            https=>"http_tppnp.monitor",
            smtp=>"smtp3.monitor",
            smtps=>"smtp3.monitor",
            imap=>"imap.monitor",
            imaps=>"imap-ssl.monitor",
            ldap=>"ldap.monitor",
            telnet=>"telnet.monitor"
        };
        my $args = '';
        my $ip = $networkreg{$networkuuid1}->{'internalip'};
        $ip = $networkreg{$networkuuid1}->{'externalip'} if ($networktype eq 'externalip');
        $ip = '127.0.0.1' if ($networktype eq 'gateway' && $servicename eq 'diskspace'); #Dummy IP - we only support diskspace checks
        if ($networktype eq 'gateway' && $servicename eq 'ping') {
            $ip = $obj->{'serverip'};
        # We can only check 10.x.x.x addresses on vlan because of routing
            if ($ip =~ /^10\./) {
                $monitors->{'ping'} = "stabile-arping.monitor";
                my $id = $networkreg{$networkuuid1}->{'id'};
                if ($id > 1) {
                    my $if = $datanic . "." . $id;
                    $args = " $if";
                } else {
                    $args = " $extnic";
                }
                $args .= " $ip";
            }
        }

        if ($servicename eq 'ping') {
            ;
        } elsif ($servicename eq 'diskspace'){
            #my $macip = $domreg{$serveruuid}->{'macip'};
            #my $image = URI::Escape::uri_escape($domreg{$serveruuid}->{'image'});
            #$args .= " $macip $image $serveruuid";
            $args .= " $serveruuid";
            $args .= ($request)?" $request":" 10"; #min free %
            $args .= " $okstring" if ($okstring); #Comma-separated partion list, e.g. 0,1
        } elsif ($servicename eq 'http'){
            $args .= " --okcodes \"200,403\" --debuglog -";
            $args .= " --okstring \"$okstring\"" if ($okstring);
            $args .= " http://$ip";
            $args .= ":$port" if ($port && $port>10 && $port<65535);
            $request = substr($request,1) if ($request =~ /^\//);
            $args .= "/$request" if ($request);
        } elsif ($servicename eq 'https'){
            $args .= " --okcodes \"200,403\" --debuglog -";
            $args .= " --okstring \"$okstring\"" if ($okstring);
            $args .= " https://$ip";
            $args .= ":$port" if ($port && $port>10 && $port<65535);
            $request = substr($request,1) if ($request =~ /^\//);
            $args .= "/$request" if ($request);
        } elsif ($servicename eq 'smtp'){
            $args .= " --from \"$request\"" if ($request);
            $args .= " --to \"$okstring\"" if ($okstring);
            $args .= " --port $port" if ($port && $port>10 && $port<65535);
        } elsif ($servicename eq 'smtps'){
            $args .= " --requiretls";
            $args .= " --from \"$request\"" if ($request);
            $args .= " --to \"$okstring\"" if ($okstring);
            $args .= " --port $port" if ($port && $port>10 && $port<65535);
        } elsif ($servicename eq 'imap'){
            $args .= " -p $port" if ($port && $port>10 && $port<65535);
        } elsif ($servicename eq 'imaps'){
            $args .= " -p $port" if ($port && $port>10 && $port<65535);
        } elsif ($servicename eq 'ldap'){
            $args .= " --port $port" if ($port && $port>10 && $port<65535);
            $args .= " --basedn \"$request\"" if ($request);
            $args .= " --attribute \"$okstring\"" if ($okstring);
        } elsif ($servicename eq 'telnet'){
            $args .= " -l \"$okstring\"" if ($okstring);
            $args .= " -p $port" if ($port && $port>10 && $port<65535);
        }

        my @ogroups = mon::find("hostgroup", $conf);
        my @owatches = mon::find("watch", $conf);

        $group = { 'name' => 'hostgroup', 'values' => [ $serveruuid, $ip ] };
        my $ogroup = undef;
        my $i;
        for($i=0; $i<scalar @ogroups; $i++) {
            if ($ogroups[$i]->{'values'}[0] eq  $serveruuid) {
                $ogroup = $ogroups[$i];
                last;
            }
        }
        mon::save_directive($conf, $ogroup, $group); #Update host hostgroup

        $watch = { 'name' => 'watch','values' => [ $serveruuid ], 'members' => [ ] };
        my $owatch = undef;
        my $oservice = undef;
        my $widx = undef;
        for($i=0; $i<scalar @owatches; $i++) { # Run through all watches and locate match
            if ($owatches[$i]->{'values'}[0] eq  $serveruuid) {
                $owatch = $watch = $owatches[$i];
                $widx = $owatch->{'index'};
                my @oservices = mon::find("service", $watch->{'members'});
                for($j=0; $j<@oservices; $j++) { # Run through all services for watch and locate match
                    if ($oservices[$j]->{'values'}[0] eq $servicename) {
                        $oservice = $oservices[$j];
                        my $newmonargs = "$monitors->{$servicename}$args";
                        $newmonargs =~ s/\s+$//; # Remove trailing spaces
                        my $oldmonargs = "$oservices[$j]->{'members'}[2]->{'values'}[0] $oservices[$j]->{'members'}[2]->{'values'}[1]";
                        $oldmonargs =~ s/\s+$//; # Remove trailing spaces
                        if ($newmonargs ne $oldmonargs) {
                            $update = 1; #We are changing an existing service definition
                        };
                        last;
                    }
                }
                last;
            }
        }
        my $in = {
            args=>undef,
            desc=>"$desc",
            idx=>$widx,
            interval=>$interval,
            interval_u=>'m',
            monitor=>$monitors->{$servicename} . $args,
            monitor_def=>1,
            name=>$servicename,
            other=>undef,
            sidx=>undef,
            delete=>$delete,
            email=>$email
        };

        if ($update || $delete) {
            unlink glob "/var/log/stabile/*:$serveruuid:$servicename";
        } else {
            my $oplogfile = "/var/log/stabile/$year-$month:$serveruuid:$servicename";
            unless (-e $oplogfile) {
                `/usr/bin/touch "$oplogfile"`;
                `/bin/chown mon:mon "$oplogfile"`;
                my $logline = "$current_time, UP, STARTUP, $pretty_time";
                `/bin/echo >> $oplogfile "$logline"`;
            }
        }
        $deleteid = (($delete || $update)?"$serveruuid:$servicename":'');
        save_service($in, $owatch, $oservice);
        $doreset = 1;
        $obj->{'last_check'} = '--';
        $obj->{'opstatus'} = '7';
        $obj->{'status'} = 'checking';
        $obj->{'alertemail'} = $email;
        mon::flush_file_lines();
        $main::syslogit->($user, 'info', "updating monitor $serveruuid:$servicename" .  (($delete)?" delete":""));
        saveOpstatus($deleteid);
        `/usr/bin/moncmd reset keepstate`;
    }

    untie %networkreg;
    untie %domreg;

    $postreply = to_json(\%h, {pretty => 1});
    $postmsg = "OK" unless ($postmsg);
    return $postreply;
}

## Copied from save_service.cgi (from webmin) and slightly modified - well heavily perhaps

sub save_service {
    my $sin = shift;
    my $owatch = shift;
    my $oservice = shift;
    my %in = %{$sin};
    my $oldservice = undef;
    my $service;
    if ($oservice) {
        # $oldservice = $service = $watch->{'members'}->[$in{'sidx'}];
        $oldservice = $service = $oservice;
    } else {
        $service = { 'name' => 'service',
                 'indent' => '    ',
                 'members' => [ ] };
    }

    if ($in{'delete'}) {
        # Delete this service from the watch
        mon::save_directive($watch->{'members'}, $service, undef) if ($oservice);
        my @rservices = mon::find("service", $watch->{'members'});
        # Delete watch and hostgroup if no services left
        if (@rservices==0) {
            mon::save_directive($conf, $watch, undef);
            mon::save_directive($conf, $group, undef);
        }
    } else {
        # Validate and store service inputs
        $in{'name'} =~ /^\S+$/ || {$in{'name'} = 'ping'};
        $service->{'values'} = [ $in{'name'} ];
        $in{'interval'} =~ /^\d+$/ || {$in{'interval'} = 1};

        &set_directive($service->{'members'}, "interval", $in{'interval'}.$in{'interval_u'});

        if ($in{'monitor_def'}) {
            &set_directive($service->{'members'}, "monitor", $in{'monitor'}.' '.$in{'args'});
        }
        else {
            $in{'other'} =~ /^\S+$/ || return "No other monitor specified";
            &set_directive($service->{'members'}, "monitor", $in{'other'}.' '.$in{'args'});
        }

        # Save the description
        if ($in{'desc'}) {
            my $desc = $in{'desc'};
            $desc =~ tr/\n/ /;
            &set_directive($service->{'members'}, "description", $in{'desc'});
        }
        else {
            &set_directive($service->{'members'}, "description", '--');
        }

        my $period = { 'name' => 'period', 'members' => [ ] };
        my @alert;
        my @v = ( "stabile.alert", $in{'email'} );
        my @num = (2); # The number of alerts to send
        push(@alert, { 'name' => 'alert', 'values' => \@v });
		&set_directive($period->{'members'}, "alert", @alert);
        my @upalert;
        push(@upalert, { 'name' => 'upalert', 'values' => \@v });
		&set_directive($period->{'members'}, "upalert", @upalert);
        my @startupalert;
        push(@startupalert, { 'name' => 'startupalert', 'values' => \@v });
		&set_directive($period->{'members'}, "startupalert", @startupalert);
        my @numalerts;
        push(@numalerts, { 'name' => 'numalerts', 'values' => \@num });
		&set_directive($period->{'members'}, "numalerts", @numalerts);
        my @no_comp_alerts;
        push(@no_comp_alerts, { 'name' => 'no_comp_alerts', 'values' => 0 });
		&set_directive($period->{'members'}, "no_comp_alerts", @no_comp_alerts);

        push(@period, $period);

    	&set_directive($service->{'members'}, "period", @period);

        if ($owatch) {
            # Store the service in existing watch in the config file
            mon::save_directive($watch->{'members'}, $oldservice, $service);
        } else {
            # Create new watch
            push(@service, $service);
            &set_directive($watch->{'members'}, "service", @service);
            mon::save_directive($conf, undef, $watch);
        }
    }
}

# set_directive(&config, name, value, value, ..)
sub set_directive
{
local @o = mon::find($_[1], $_[0]);
local @n = @_[2 .. @_-1];
local $i;
for($i=0; $i<@o || $i<@n; $i++) {
	local $idx = &indexof($o[$i], @{$_[0]}) if ($o[$i]);
	local $nv = ref($n[$i]) ? $n[$i] : { 'name' => $_[1],
					     'values' => [ $n[$i] ] }
						if (defined($n[$i]));
	if ($o[$i] && defined($n[$i])) {
		$_[0]->[$idx] = $nv;
		}
	elsif ($o[$i]) {
		splice(@{$_[0]}, $idx, 1);
		}
	else {
		push(@{$_[0]}, $nv);
		}
	}
}

sub getSystemsListing {
    my ($action, $curuuid, $username) = @_;
    $username = $user unless ($username);
    my @domregvalues = values %domreg;
    my @curregvalues;
    my %curreg;

    $userfullname = $userreg{$username}->{'fullname'};
    $useremail = $userreg{$username}->{'email'};
    $userphone = $userreg{$username}->{'phone'};
    $useropfullname = $userreg{$username}->{'opfullname'};
    $useropemail = $userreg{$username}->{'opemail'};
    $useropphone = $userreg{$username}->{'opphone'};
    $useralertemail = $userreg{$username}->{'alertemail'};

    unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {$postreply = "Unable to access image register"; return;};
    unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {return "Unable to access networks register"};

    # Collect systems from domains and include domains as children
    if ($action ne 'flatlist') { # Dont include children in select
        my @imagenames = qw(image image2 image3 image4);
        foreach my $valref (@domregvalues) {
        # Only include VM's belonging to current user (or all users if specified and user is admin)
            if ($username eq $valref->{'user'} || $fulllist) {
                next unless (!$curuuid || ($valref->{'uuid'} eq $curuuid || $valref->{'system'} eq $curuuid));

                my %val = %{$valref}; # Deference and assign to new ass array, effectively cloning object
                my $sysuuid = $val{'system'};
                my $dbobj = $register{$sysuuid};
                $val{'memory'} += 0;
                $val{'vcpu'} += 0;
                $val{'nodetype'} = 'child';
                $val{'fullname'} = $val{'fullname'} || $dbobj->{'fullname'} || $userfullname;
                $val{'email'} = $val{'email'} || $dbobj->{'email'} || $useremail;
                $val{'phone'} = $val{'phone'} || $dbobj->{'phone'} || $userphone;
                $val{'opfullname'} = $val{'opfullname'} || $dbobj->{'opfullname'} || $useropfullname;
                $val{'opemail'} = $val{'opemail'} || $dbobj->{'opemail'} || $useropemail;
                $val{'opphone'} = $val{'opphone'} || $dbobj->{'opphone'} || $useropphone;
                $val{'alertemail'} = $val{'alertemail'} || $dbobj->{'alertemail'} || $useralertemail;
                $val{'autostart'} = ($val{'autostart'})?'1':'';

                foreach my $img (@imagenames) {
                    if ($imagereg{$val{$img}} && $imagereg{$val{$img}}->{'storagepool'} == -1) {
                        $val{'nodestorage'} += $imagereg{$val{$img}}->{'virtualsize'};
                    } else {
                        $val{'storage'} += $imagereg{$val{$img}}->{'virtualsize'} if ($imagereg{$val{$img}});
                    }
                }
                $val{'externalips'} += 1 if ($networkreg{$val{'networkuuid1'}} && $networkreg{$val{'networkuuid1'}}->{'type'} =~ /externalip|ipmapping/);
                $val{'externalips'} += 1 if ($networkreg{$val{'networkuuid2'}} && $networkreg{$val{'networkuuid2'}}->{'type'} =~ /externalip|ipmapping/);
                $val{'externalips'} += 1 if ($networkreg{$val{'networkuuid3'}} && $networkreg{$val{'networkuuid3'}}->{'type'} =~ /externalip|ipmapping/);
                $val{'networktype1'} = $networkreg{$val{'networkuuid1'}}->{'type'} if ($networkreg{$val{'networkuuid1'}});
                $val{'imageuuid'} = $imagereg{$val{'image'}}->{'uuid'} if ($imagereg{$val{'image'}});
                $val{'imageuuid2'} = $imagereg{$val{'image2'}}->{'uuid'} if ($imagereg{$val{'image2'}} && $val{'image2'} && $val{'image2'} ne '--');

                my $networkuuid1; # needed for generating management url
                if ($sysuuid && $sysuuid ne '--') { # We are dealing with a server that's part of a system
                    if (!$register{$sysuuid}) { #System does not exist - create it
                        $sysname = $val{'name'};
                        $sysname = $1 if ($sysname =~ /(.+)\..*/);
                        $sysname =~ s/server/System/i;
                        $register{$sysuuid} = {
                            uuid => $sysuuid,
                            name => $sysname,
                            user => $username,
                            created => $current_time
                        };
                    }

                    my %pval = %{$register{$sysuuid}};
                    $pval{'status'} = '--';
                    $pval{'issystem'} = 1;
                    $pval{'fullname'} = $pval{'fullname'} || $userfullname;
                    $pval{'email'} = $pval{'email'} || $useremail;
                    $pval{'phone'} = $pval{'phone'} || $userphone;
                    $pval{'opfullname'} = $pval{'opfullname'} || $useropfullname;
                    $pval{'opemail'} = $pval{'opemail'} || $useropemail;
                    $pval{'opphone'} = $pval{'opphone'} || $useropphone;
                    $pval{'alertemail'} = $pval{'alertemail'} || $useralertemail;
                    $pval{'autostart'} = ($pval{'autostart'})?'1':'';

                    my @children;
                    if ($curreg{$sysuuid}->{'children'}) {
                        @children = @{$curreg{$sysuuid}->{'children'}};
                    }
                    # If system has an admin image, update networkuuid1 with the image's server's info
                    if ($pval{'image'} && $pval{'image'} ne '--') {
                        my $dbimg = $imagereg{$pval{'image'}};
                        $networkuuid1 = $domreg{$dbimg->{'domains'}}->{'networkuuid1'} if ($domreg{$dbimg->{'domains'}});
                        my $externalip = $networkreg{$networkuuid1}->{'externalip'} if ($networkreg{$networkuuid1});
                        $register{$sysuuid}->{'networkuuid1'} = $networkuuid1;
                        $register{$sysuuid}->{'internalip'} = $networkreg{$networkuuid1}->{'internalip'} if ($networkreg{$networkuuid1});
                        $pval{'master'} = $dbimg->{'master'};
                        $pval{'appid'} = $dbimg->{'appid'};
                        $pval{'version'} = $dbimg->{'version'};
                        my $managementurl;
                        $managementurl = $dbimg->{'managementlink'};
                        $managementurl =~ s/\{uuid\}/$networkuuid1/;
                        $managementurl =~ s/\{externalip\}/$externalip/;
                        $pval{'managementurl'} = $managementurl;
                        my $upgradeurl;
                        $upgradeurl = $dbimg->{'upgradelink'};
                        $upgradeurl =~ s/\{uuid\}/$networkuuid1/;
                        $pval{'upgradeurl'} = $upgradeurl;
                        my $terminalurl;
                        $terminalurl = $dbimg->{'terminallink'};
                        $terminalurl =~ s/\{uuid\}/$networkuuid1/;
                        $pval{'terminalurl'} = $terminalurl;
                        $pval{'externalip'} = $externalip;
                        $pval{'imageuuid'} = $dbimg->{'uuid'};
                        $pval{'imageuuid2'} = $imagereg{$pval{'image2'}}->{'uuid'} if ($pval{'image2'} && $pval{'image2'} ne '--');
                    }
                    push @children,\%val;
                    $pval{'children'} = \@children;
                    $curreg{$sysuuid} = \%pval;
                } else { # This server is not part of a system
                    $sysuuid = $val{'uuid'};
                    my $dbimg = $imagereg{$val{'image'}};
                    $networkuuid1 = $domreg{$dbimg->{'domains'}}->{'networkuuid1'} if ($domreg{$dbimg->{'domains'}});
                    my $externalip;
                    $externalip = $networkreg{$networkuuid1}->{'externalip'} if ($networkreg{$networkuuid1});
                    $val{'networkuuid1'} = $networkuuid1;
                    $val{'internalip'} = $networkreg{$networkuuid1}->{'internalip'} if ($networkreg{$networkuuid1});
                    $val{'master'} = $dbimg->{'master'};
                    $val{'appid'} = $dbimg->{'appid'};
                    $val{'version'} = $dbimg->{'version'};
                    $val{'imageuuid'} = $dbimg->{'uuid'};
                    $val{'imageuuid2'} = $imagereg{$val{'image2'}}->{'uuid'} if ($val{'image2'} && $val{'image2'} ne '--' && $imagereg{$val{'image2'}});

                    my $managementurl = $dbimg->{'managementlink'};
                    $managementurl =~ s/\{uuid\}/$networkuuid1/;
                    $managementurl =~ s/\{externalip\}/$externalip/;
                    $val{'managementurl'} = $managementurl;
                    my $upgradeurl;
                    $upgradeurl = $dbimg->{'upgradelink'};
                    $upgradeurl =~ s/\{uuid\}/$networkuuid1/;
                    $val{'upgradeurl'} = $upgradeurl;
                    my $terminalurl;
                    $terminalurl = $dbimg->{'terminallink'};
                    $terminalurl =~ s/\{uuid\}/$networkuuid1/;
                    $val{'terminalurl'} = $terminalurl;
                    $val{'externalip'} = $externalip;
                    $val{'system'} = '--';

                    $curreg{$sysuuid} = \%val;
                }
            }
        }
        tied(%register)->commit;
    }
    untie %imagereg;

    my @regvalues = values %register;
    # Go through systems register, add empty systems and update statuses
    foreach my $valref (@regvalues) {
    # Only include items belonging to current user (or all users if specified and user is admin)
        if ($username eq $valref->{'user'} || $fulllist) {
            next unless (!$curuuid || $valref->{'uuid'} eq $curuuid);

            my %val = %{$valref};
            # add empty system (must be empty since not included from going through servers
            if (!($curreg{$val{'uuid'}})) {
                $val{'issystem'} = 1;
                $val{'status'} = 'inactive';
                $curreg{$val{'uuid'}} = \%val;
            } else {
            # Update status
                my $status = 'running';
                my $externalips = 0;
                foreach my $child (@{$curreg{$val{'uuid'}}-> {'children'}}) {
                    $status = $child->{'status'} unless ($child->{'status'} eq $status);
                    $externalips += $child->{'externalips'} unless ($child->{'externalips'} eq '');
                }
                $status = 'degraded' unless ($status eq 'running' || $status eq 'shutoff');
                $curreg{$val{'uuid'}}->{'status'} = $status;
                $curreg{$val{'uuid'}}->{'externalips'} = $externalips;
                # $networkreg{$domreg{$curdomuuid}->{'networkuuid1'}}->{'internalip'};
                if ($curuuid && !$curreg{$val{'uuid'}}->{'internalip'}) { # Add calling server's own internalip if it's part of an ad-hoc assembled system
                    $curreg{$val{'uuid'}}->{'internalip'} = $networkreg{$domreg{$curdomuuid}->{'networkuuid1'}}->{'internalip'};
                }
            }
        }
    }
    untie %networkreg;

    @curregvalues = values %curreg;
    my @sorted_systems = sort {$a->{'name'} cmp $b->{'name'}} @curregvalues;
    @sorted_systems = sort {$a->{'status'} cmp $b->{'status'}} @sorted_systems;

    if ($action eq 'tablelist') {
        my $t2 = Text::SimpleTable->new(40,24,14);

        $t2->row('uuid', 'name', 'user');
        $t2->hr;
        my $pattern = $options{m};
        foreach $rowref (@sorted_systems){
            if ($pattern) {
                my $rowtext = $rowref->{'uuid'} . " " . $rowref->{'name'} . " " . $rowref->{'user'};
                next unless ($rowtext =~ /$pattern/i);
            }
            $t2->row($rowref->{'uuid'}, $rowref->{'name'}||'--', $rowref->{'user'}||'--');
        }
        return $t2->draw;
    } elsif ($action eq 'removeusersystems') {
        return @sorted_systems;
    } elsif ($action eq 'arraylist') {
        return @sorted_systems;
    } elsif ($console) {
        return Dumper(\@sorted_systems);
    } else {
        my %it = ('uuid','--','name','--', 'issystem', 1);
        push(@sorted_systems, \%it) if ($action eq 'flatlist');
        my $json_text = to_json(\@sorted_systems, {pretty => 1});
        $json_text =~ s/"false"/false/g;
        $json_text =~ s/"true"/true/g;
#        $json_text =~ s/""/"--"/g;
        $json_text =~ s/null/"--"/g;
        $json_text =~ s/\x/ /g;
        if ($action eq 'flatlist') {
            return qq|{"identifier": "uuid", "label": "name", "items": $json_text}|;
        } else {
            return $json_text;
        }
    }
}

# Build a complete system around cloned image
sub buildSystem {
    my ($name, $hmaster, $hstoragepool, $hsystem, $hinstances,
        $hnetworkuuid1, $hbschedule, $hnetworktype1, $hports, $hmemory, $hvcpu, $hdiskbus,
        $hcdrom, $hboot, $hnicmodel1, $hnicmac1, $hnetworkuuid2, $hnicmac2, $hmonitors,
        $hmanagementlink, $hstart, $duuid, $hstoragepool2 ) = @_;

    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {$postreply = "Unable to access domain register"; return $postreply;};
    unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {$postreply = "Unable to access image register"; return $postreply;};

    my $master = $hmaster;

    if ($curuuid && !$domreg{$curuuid} && $duuid) { # curuuid is a system uuid
        $curuuid = $duuid;
    }

    if (!$master && $curuuid && $domreg{$curuuid} && $imagereg{$domreg{$curuuid}->{image}}) {
        $master = $imagereg{$domreg{$curuuid}->{image}}->{master};
    }
    my $cdrom = $hcdrom;
    my $storagepool = $hstoragepool;
    my $storagepool2 = $hstoragepool2 || '0';
    my $image2;
    $hinstances = 1 unless ($hinstances);
    my $ioffset = 0;
    if (!$name && $curuuid) {
        $ioffset = 1; # Looks like we are called from an existing server - bump
        $name = $domreg{$curuuid}->{'name'};
        $name = $1 if ($name =~ /(.+)\.\d+$/);
        foreach my $dom (values %domreg) { # Sequential naming of related systems
            if ($dom->{'user'} eq $user && $dom->{'name'} =~ /$name\.(\d+)$/) {
                $ioffset = $1+1 if ($1 >= $ioffset);
            }
        }
    }
    if ($master && !$imagereg{"$master"}) {
    # Try to look up master based on file name
        my @spoolpaths = $cfg->param('STORAGE_POOLS_LOCAL_PATHS');
        my @users = ('common', $user);
        foreach my $u (@accounts) {push @users,$u;};
        # Include my sponsors master images
        my $billto = $userreg{$user}->{'billto'};
        push @users, $billto if ($billto);
        # Also include my subusers' master images
        my @userregkeys = (tied %userreg)->select_where("billto = '$user'");
        push @users, @userregkeys if (@userregkeys);

        my $match;
        foreach my $u (@users) {
            foreach $sp (@spoolpaths) {
                if ($imagereg{"$sp/$u/$master"}) {
                    $master = "$sp/$u/$master";
                    $match = 1;
                    last;
                }
            }
            last if ($match),
        }
    }

    if (!$imagereg{$master} && length $master == 36) {
    # Try to look up master by uuid
        unless ( tie(%imagereg2,'Tie::DBI', Hash::Merge::merge({table=>'images', CLOBBER=>1}, $Stabile::dbopts)) ) {$postreply = "Unable to access image register"; return $postreply;};
        $master = $imagereg2{$master}->{'path'} if ($imagereg2{$master});
        untie %imagereg2;
    }

    if (!$master && $curuuid) {
        $master = $imagereg{$domreg{$curuuid}->{'image'}}->{'master'};
    }

    unless ($imagereg{$master}) {$postreply = "Status=Error Invalid master $master"; return $postreply;};
    my $masterimage2 = $imagereg{"$master"}->{'image2'};
    my $sysuuid = $hsystem;

    if ($cdrom && $cdrom ne '--' && !$imagereg{"$cdrom"}) {
    # Try to look up cdrom based on file name
        my @spoolpaths = $cfg->param('STORAGE_POOLS_LOCAL_PATHS');
        my @users = ('common', $user);
        foreach my $u (@accounts) {push @users,$u;};
        my $match;
        foreach my $u (@users) {
            foreach $sp (@spoolpaths) {
                if ($imagereg{"$sp/$u/$cdrom"}) {
                    $cdrom = "$sp/$u/$cdrom";
                    $match = 1;
                    last;
                }
            }
            last if ($match),
        }
    }

    #open OUTPUT, '>', "/dev/null"; select OUTPUT;
    $Stabile::Images::console = 1;
    require "$Stabile::basedir/cgi/images.cgi";
    $Stabile::Networks::console = 1;
    require "$Stabile::basedir/cgi/networks.cgi";
    $Stabile::Servers::console = 1;
    require "$Stabile::basedir/cgi/servers.cgi";

    #close(OUTPUT); select STDOUT;
    # reset stdout to be the default file handle
    my $oipath; # This var stores admin servers image, if only one server initially
    if ($sysuuid eq 'new') {
        $sysuuid = '';
    } elsif ($sysuuid eq 'auto' || (!$sysuuid && $curuuid)) { # $curuuid means request is coming from a running vm
        my $domuuid = $curuuid || Stabile::Networks::ip2domain( $ENV{'REMOTE_ADDR'} );
        if ($domuuid && $domreg{$domuuid}) {
            if ($domreg{$domuuid}->{'system'}) {
                $sysuuid = $domreg{$domuuid}->{'system'};
            } else {
                my $ug = new Data::UUID;
                $sysuuid = $ug->create_str();
                #$sysuuid = $domuuid; # Make sysuuid same as primary domains uuid
                $domreg{$domuuid}->{'system'} = $sysuuid;
                $oipath = $domreg{$domuuid}->{'image'};
            }
        } else {
            $sysuuid = '';
        }
    }

    # Check if images should be moved to node storage
    if ($storagepool eq "-1") {
        if (index($privileges, 'n')==-1 && !$isadmin) {
            $storagepool = '';
        } else {
            $storagepool = -1;
            # %nodereg is needed in order to increment reservedvcpus for nodes
            unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac'}, $Stabile::dbopts)) ) {$postreply = "Unable to access node register"; return $postreply;};
        }
    }

    my @domains;
    my $systemuuid;
    for (my $i=$ioffset; $i<$hinstances+$ioffset; $i++) {
        my $ipath;
        my $mac;
        my $res;
        my $istr = ".$i";
        $istr = '' if ($hinstances==1 && $i==0);

    # Clone image
        my $imagename = $name;
        $imagename =~ s/system/Image/i;
        $res = Stabile::Images::Clone($master, 'clone', '', $storagepool, '', "$imagename$istr", $hbschedule, 1, $hmanagementlink, $appid, 1, $hvcpu, $hmemory);
        $postreply .= $res;
        if ($res =~ /path: (.+)/) {
            $ipath = $1;
        } else {
            next;
        }
        $mac = $1 if ($res =~ /mac: (.+)/);
        Stabile::Images::updateBilling();

        # Secondary image - clone it
        if ($masterimage2 && $masterimage2 ne '--' && $masterimage2 =~ /\.master\.qcow2$/) {
            $res = Stabile::Images::Clone($masterimage2, 'clone', '', $storagepool2, $mac, "$imagename$istr-data", $hbschedule, 1, '', '', 1);
            $postreply .= $res;
            $image2 = $1 if ($res =~ /path: (.+)/);
        }

    # Create network
        my $networkuuid1;
        if ($hnetworkuuid1) { # An existing network was specified
            $networkuuid1 = $hnetworkuuid1;
        } else { # Create new network
            my $networkname = $name;
            $networkname =~ s/system/Connection/i;
            my $type = ($i==0)?$hnetworktype1 : '';
            if (!$type) {
                if ($curuuid && $i==0) { # This should never be true, leaving for now...
                    unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {$postreply = "Unable to access networks register"; return $postreply;};
                    $type = $networkreg{$domreg{$curuuid}->{'networkuuid1'}}->{'type'};
                    untie %networkreg;
                } else {
                    $type = 'internalip';
                }
            }
            $main::syslogit->($user, 'info', "saving network $networkname$istr");
            $res = Stabile::Networks::save('', '', "$networkname$istr", 'new', $type, '','',$hports,1,$user);
            $postreply .= $res;
            if ($res =~ /uuid: (.+)/) {
                $networkuuid1 = $1;
            } else {
                next;
            }
        }

    # Create server
        my $servername = $name;
        $servername =~ s/system/Server/i;
        if ($curuuid) {
            $hmemory = $hmemory || $domreg{$curuuid}->{'memory'};
            $hvcpu = $hvcpu || $domreg{$curuuid}->{'vcpu'};
            $hdiskbus = $hdiskbus || $domreg{$curuuid}->{'diskbus'};
            $cdrom = $cdrom || $domreg{$curuuid}->{'cdrom'};
            $hboot = $hboot || $domreg{$curuuid}->{'boot'};
            $hnicmodel1 = $hnicmodel1 || $domreg{$curuuid}->{'nicmodel1'};
        }

        $main::syslogit->($user, 'info', "saving server $servername$istr");
        $res =  Stabile::Servers::Save('', '', {
                 uuid => '',
                 name => "$servername$istr",
                 memory => $hmemory,
                 vcpu => $hvcpu,
                 image => $ipath,
                 imagename => '',
                 image2 => $image2,
                 image2name => '',
                 diskbus => $hdiskbus,
                 cdrom => $cdrom,
                 boot => $hboot,
                 networkuuid1 => $networkuuid1,
                 networkid1 => '',
                 networkname1 => '',
                 nicmodel1 => $hnicmodel1,
                 nicmac1 => $hnicmac1,
                 nicmac2 => $hnicmac2,
                 status => 'new',
                 notes => $notes,
                 system => $sysuuid,
                 newsystem => ($hinstances>1 && !$sysuuid),
                 buildsystem => 1,
                 console => 1
             });

        $postreply .= "$res\n";
        $sysuuid = $1 if ($res =~ /sysuuid: (\S+)/);
        my $serveruuid;
        $serveruuid = $1 if ($res =~ /uuid: (\S+)/);
        my $sys = $register{$sysuuid};
        if ($sysuuid && $i==$ioffset) {
            $register{$sysuuid} = {
                uuid => $sysuuid,
                name => $sys->{'name'} || $servername, #Don't rename existing system
                user => $user,
                image => $sys->{'image'} || $oipath || $ipath, #Don't update admin image for existing system
                created => $current_time
            };
        }

    # Create monitors
        my @monitors = split(",", $hmonitors);
        if (@monitors) {
            $res = addSimpleMonitors($serveruuid, $alertemail, \@monitors);
            if ( $res eq 'OK' ) {
                `/usr/bin/moncmd reset keepstate &`;
                $postreply .= "Status=OK Saved monitors @monitors\n";
            } else {
                $postreply .= "Status=OK Not saving monitors: $res\n";
            }

        }

        if ($serveruuid) {
            unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {$postreply = "Unable to access networks register"; return $postreply;};
            $networkreg{$networkuuid1}->{'domains'} = $serveruuid;
            tied(%networkreg)->commit;
            untie %networkreg;

            push @domains, $serveruuid;
            $imagereg{$ipath}->{'domains'} = $serveruuid;
            $imagereg{$ipath}->{'domainnames'} = "$servername$istr";
            if ($storagepool == -1) {
                # my $mac = $imagereg{$ipath}->{'mac'};
                # Increment reserved vcpus in order for location of target node to spread out
                $postreply .= "Status=OK Cloned image to node $mac: $nodereg{$mac}->{'reservedvcpus'}";
                $nodereg{$mac}->{'reservedvcpus'} += $hvcpu;
                $postreply .= ":$nodereg{$mac}->{'reservedvcpus'}\n";
                tied(%nodereg)->commit;
                if (!$hstart) { # If we are not starting servers, wake up node anyway to perform clone operation
                    if ($nodereg{$mac}->{'status'} eq 'asleep') {
                        require "$Stabile::basedir/cgi/nodes.cgi";
                        $Stabile::Nodes::console = 1;
                        Stabile::Nodes::wake($mac);
                    }
                }
            }
        }
        $systemuuid = (($sysuuid)? $sysuuid : $serveruuid) unless ($systemuuid);
    }
    if ($storagepool == -1) {
        untie %nodereg;
    }

    $postreply .= "Status=OK sysuuid: $systemuuid\n" if ($systemuuid);
    if ($hstart) {
        foreach my $serveruuid (@domains) {
            $postreply .= Stabile::Servers::Start($serveruuid, 'start',{buildsystem=>1});
        }
    } else {
        $main::updateUI->({tab=>'servers', user=>$user, uuid=>$serveruuid, status=>'shutoff'});
    }
    untie %imagereg;
    #if (@domains) {
    #    return to_json(\@domains, {pretty=>1});
    #} else {
        return $postreply;
    #}
}

sub upgradeSystem {
    my $internalip = shift;

    unless (tie %imagereg,'Tie::DBI', { # Needed for ValidateItem
        db=>'mysql:steamregister',
        table=>'images',
        key=>'path',
        autocommit=>0,
        CLOBBER=>3,
        user=>$dbiuser,
        password=>$dbipasswd}) {throw Error::Simple("Stroke=ERROR Image register could not be accessed")};

    my $appid;
    my $appversion;
    my $appname;
    my $master;
    my $progress;
    my $currentversion;

# Locate the system we should upgrade
    if ($internalip) {
        foreach my $network (values %networkreg) {
            if ($internalip =~ /^10\.\d+\.\d+\.\d+/
                && $network->{'internalip'} eq $internalip
                && $network->{'user'} eq $user
            ) {
                $curuuid = $domreg{$network->{'domains'}}->{'uuid'};
                $cursysuuid = $domreg{$curuuid}->{'system'};
                $master = $imagereg{$domreg{$curuuid}->{'image'}}->{'master'};
                $appid = $imagereg{$master}->{'appid'};
                $appversion = $imagereg{$master}->{'version'};
                $appname = $imagereg{$master}->{'name'};
                last;
            }
        }
    }
# Locate the newest version of master image
    my $currentmaster;
    foreach my $imgref (values %imagereg) {
        if ($imgref->{'path'} =~ /\.master\.qcow2$/
            && $imgref->{'path'} !~ /-data\.master\.qcow2$/
            && $imgref->{'appid'} eq $appid
        ) {
            if ($imgref->{'version'} > $currentversion) {
                $currentmaster = $imgref;
                $currentversion = $imgref->{'version'};
            }
        }
    }
# Build list of system members
    my @doms;
    if ($cursysuuid && $register{$cursysuuid}) {
        $register{$cursysuuid}->{'status'} = 'upgrading';
        foreach my $domref (values %domreg) {
            push( @doms, $domref ) if ($domref->{'system'} eq $cursysuuid && $domref->{'user'} eq $user);
        }
    } else {
        push( @doms, $domreg{$curuuid} ) if ($domreg{$curuuid}->{'user'} eq $user);
    }
    $membs = int @doms;

    my $problem = 0;
    foreach my $dom (@doms) {
        if ($dom->{'status'} ne 'running') {
            $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user,
            status=>qq|Server $dom->{name} is not running. All member servers must be running when upgrading an app.|});
            $problem = 1;
            last;
        }
    }
# First dump each servers data to nfs
    unless ($problem) {
        $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, status=>"Already newest version, reinstalling version $currentversion!", title=>'Reinstalling, hold on...'});
        $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, status=>'Beginning data dump!'});

        my $browser = LWP::UserAgent->new;
        $browser->agent('movepiston/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );

        foreach my $dom (@doms) {
            my $upgradelink = $imagereg{$dom->{'image'}}->{'upgradelink'};
            if ($upgradelink) {
                my $res;
                my $networkuuid1 = $dom->{'networkuuid1'};
                my $ip = $networkreg{$networkuuid1}->{'internalip'};
                $upgradelink = "http://internalip$upgradelink" unless ($upgradelink =~ s/\{internalip\}/$ip/);
                $domreg{$dom->{'uuid'}}->{'status'} = 'upgrading';
                $main::updateUI->({tab=>'servers', user=>$user, uuid=>$dom->{'uuid'}, status=>'upgrading'});
                my $content = $browser->get($upgradelink)->content();
                if ($content =~ /^\{/) { # Looks like json
                    $jres = from_json($content);
                    $res = $jres->{'message'};
                    unless (lc $jres->{'status'} eq 'ok') {
                        $problem = 2;
                    }
                } else { # no json returned, assume things went hayward
                    $res = $content;
                    $res =~ s/</&lt;/g;
                    $res =~ s/>/&gt;/g;
                    $problem = "Data dump failed ($upgradelink)";
                }
                $res =~ s/\n/ /;
                $progress += 10;
                $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, status=>"$ip: $res", progress=>$progress});
            }
        }
    }
    tied(%domreg)->commit;

# Shut down all servers
    unless ($problem) {
        $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, status=>'Beginning shutdown of servers!'});
        require "$Stabile::basedir/cgi/servers.cgi";
        $Stabile::Servers::console = 1;
        foreach my $dom (@doms) {
            $progress += 10;
            my $networkuuid1 = $dom->{'networkuuid1'};
            my $ip = $networkreg{$networkuuid1}->{'internalip'};
            $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, status=>"$ip: Shutting down...", progress=>$progress});
            if ($dom->{'status'} eq 'shutoff' || $dom->{'status'} eq 'inactive') {
                next;
            } else {
                my $res = Stabile::Servers::destroyUserServers($user, 1, $dom->{'uuid'});
                if ($dom->{'status'} ne 'shutoff' && $dom->{'status'} ne 'inactive') {
                    $problem = "ERROR $res"; # We could not shut down a server, fail...
                    last;
                }
            }
        }
    }
# Then replace each image with new version
    unless ($problem) {
        $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, status=>'Attaching new images!'});
        require "$Stabile::basedir/cgi/images.cgi";
        $Stabile::Images::console = 1;
        foreach my $dom (@doms) {
            $progress += 10;
            my $networkuuid1 = $dom->{'networkuuid1'};
            my $ip = $networkreg{$networkuuid1}->{'internalip'};
            $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, status=>"$ip: Attaching image...", progress=>$progress});
            my $image = $imagereg{$dom->{'image'}};
            my $ipath;
            # Clone image
            my $imagename = $image->{'name'};
            my $res = Stabile::Images::Clone($currentmaster->{'path'}, 'clone', '', $image->{'storagepool'}, '', $imagename, $image->{'bschedule'}, 1, $currentmaster->{'managementlink'}, $appid, 1);
            $postreply .= $res;
            if ($res =~ /path: (.+)/) {
                $ipath = $1;
            } else {
                $problem = 5;
            }

            if ($ipath =~ /\.qcow2$/) {
                Stabile::Images::updateBilling();
                # Attach new image to server
                $main::syslogit->($user, 'info', "attaching new image to server $dom->{'name'} ($dom->{'uuid'})");
                $res =  Stabile::Servers::Save({
                         uuid => $dom->{'uuid'},
                         image => $ipath,
                         imagename => $imagename,
                     });
                # Update systems admin image
                $register{$cursysuuid}->{'image'} = $ipath if ($register{$cursysuuid} && $dom->{'uuid'} eq $curuuid);
                # Update image properties
                $imagereg{$ipath}->{'domains'} = $dom->{'uuid'};
                $imagereg{$ipath}->{'domainnames'} = $dom->{'name'};
            } else {
                $problem = 6;
            }
        }
    }

# Finally start all servers with new image
    unless ($problem) {
        $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, status=>'Starting servers!'});
        require "$Stabile::basedir/cgi/servers.cgi";
        $Stabile::Servers::console = 1;
        foreach my $dom (@doms) {
            $progress += 10;
            my $networkuuid1 = $dom->{'networkuuid1'};
            my $ip = $networkreg{$networkuuid1}->{'internalip'};
            $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, status=>"$ip: Starting...", progress=>$progress});
            if ($dom->{'status'} eq 'shutoff' || $dom->{'status'} eq 'inactive') {
                Stabile::Servers::Start($dom->{'uuid'}, 'start', {uistatus=>'upgrading'});
                $main::updateUI->({ tab=>'servers',
                                    user=>$user,
                                    uuid=>$dom->{'uuid'},
                                    status=>'upgrading'})
            }
        }
    } else {
        foreach my $dom (@doms) {
            $dom->{'status'} = 'inactive'; # Prevent servers from being stuck in upgrading status
        }
    }

    my $nlink = $imagereg{$doms[0]->{'image'}}->{'managementlink'}; # There might be a new managementlink for image
    my $nuuid = $doms[0]->{'networkuuid1'};
    $nlink =~ s/\{uuid\}/$nuuid/;

    unless ($problem) {
# All servers successfully upgraded
        my $status = qq|Your $appname app has exported its data and new images have been attached to your servers. Now, your app will start again and import your data.|;
        $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, progress=>100, status=>$status, managementlink=>$nlink, message=>"All done!"});
    } else {
        my $status = qq|Problem: $problem encountered. Your $appname could not be upgraded to the version $appversion. You can try again, or contact the app developer if this fails.|;
        $main::updateUI->({tab=>'upgrade', type=>'update', user=>$user, progress=>100, status=>$status, managementlink=>$nlink, message=>"Something went wrong :("});
    }
    untie %imagereg;

    my $reply = qq|{"message": "Upgrading $domreg{$curuuid}->{name} with $membs members"}|;
    return "$reply\n";
}

sub removeusersystems {
    my $username = shift;
    return unless (($isadmin || $user eq $username) && !$isreadonly);
    $user = $username;
    my @allsystems = getSystemsListing('removeusersystems');
    foreach my $sys (@allsystems) {
        next unless $sys->{'uuid'};
        remove($sys->{'uuid'}, $sys->{'issystem'}, 1);
        #$postreply .= "Status=OK Removing system $sys->{'name'} ($sys->{'uuid'})\n";
    }
    return $postreply || "[]";
}


# Remove every trace of a system including servers, images, etc.
sub remove {
    my ($uuid, $issystem, $destroy) = @_;
    my $sysuuid = $uuid;
    my $reguser = $register{$uuid}->{'user'} if ($register{$uuid});
    $reguser = $domreg{$uuid}->{'user'} if (!$reguser && $domreg{$uuid});

    $Stabile::Images::user = $user;
    require "$Stabile::basedir/cgi/images.cgi";
    $Stabile::Images::console = 1;

    $Stabile::Networks::user = $user;
    require "$Stabile::basedir/cgi/networks.cgi";
    $Stabile::Networks::console = 1;

    $Stabile::Servers::user = $user;
    require "$Stabile::basedir/cgi/servers.cgi";
    $Stabile::Servers::console = 1;

    $issystem = 1 if ($register{$uuid});
    my @domains;
    my $res;

    if ($issystem) {
    # Delete child servers
        if (($user eq $reguser || $isadmin) && $register{$uuid}){ # Existing system
        # First delete any linked networks
            if ($register{$uuid}->{'networkuuids'} && $register{$uuid}->{'networkuuids'} ne '--') {
                my @lnetworks = split /, ?/, $register{$uuid}->{'networkuuids'};
                foreach my $networkuuid (@lnetworks) {
                    if ($networkuuid) {
                        Stabile::Networks::Deactivate($networkuuid);
                        $res .= Stabile::Networks::Remove($networkuuid, 'remove', {force=>1});
                    }
                }
            }
            foreach my $domvalref (values %domreg) {
                if ($domvalref->{'system'} eq $uuid && ($domvalref->{'user'} eq $user || $isadmin)) {
                    if ($domvalref->{'status'} eq 'shutoff' || $domvalref->{'status'} eq 'inactive') {
                        push @domains, $domvalref->{'uuid'};
                    } elsif ($destroy) {
                        Stabile::Servers::destroyUserServers($reguser, 1, $domvalref->{'uuid'});
                        push @domains, $domvalref->{'uuid'} if ($domvalref->{'status'} eq 'shutoff' || $domvalref->{'status'} eq 'inactive');
                    }
                }
            }
        }
        $postreply .= "Status=removing OK Removing system $register{$uuid}->{'name'} ($uuid)\n";
        delete $register{$uuid};
        tied(%register)->commit;
    } elsif ($domreg{$uuid} && $domreg{$uuid}->{uuid}) {
    # Delete single server
        if ($domreg{$uuid}->{'status'} eq 'shutoff' || $domreg{$uuid}->{'status'} eq 'inactive') {
            push @domains, $uuid;
        } elsif ($destroy) {
            Stabile::Servers::destroyUserServers($user, 1, $uuid);
            push @domains, $uuid if ($domreg{$uuid}->{'status'} eq 'shutoff' || $domreg{$uuid}->{'status'} eq 'inactive');
        }
     #   $postreply .= "Status=OK Removing server $domreg{$uuid}->{'name'} ($uuid)\n";
    } else {
        $postreply .= "Status=Error System $uuid not found\n";
        return $postreply;
    }
    my $duuid;
    foreach my $domuuid (@domains) {
        if ($domreg{$domuuid}->{'status'} ne 'shutoff' && $domreg{$domuuid}->{'status'} ne 'inactive' ) {
            $postreply .= "Status=ERROR Cannot delete server (active)\n";
        } else {
            my $imagepath = $domreg{$domuuid}->{'image'};
            my $image2path = $domreg{$domuuid}->{'image2'};
            my $networkuuid1 = $domreg{$domuuid}->{'networkuuid1'};
            my $networkuuid2 = $domreg{$domuuid}->{'networkuuid2'};

            # Delete packages from software register
        #    $postreply .= deletePackages($domuuid);
            # Delete monitors
        #    $postreply .= deleteMonitors($domuuid)?"Stream=OK Deleted monitors for $domreg{$domuuid}->{'name'}\n":"Stream=OK No monitors to delete for $domreg{$domuuid}->{'name'}\n";
            # Delete server
            $res .= Stabile::Servers::Remove($domuuid);

            # Delete images
            $res .= Stabile::Images::Remove($imagepath);
            if ($image2path && $image2path ne '--') {
                $res .= Stabile::Images::Remove($image2path);
            }
            # Delete networks
            if ($networkuuid1 && $networkuuid1 ne '--' && $networkuuid1 ne '0' && $networkuuid1 ne '1') {
                Stabile::Networks::Deactivate($networkuuid1);
                $res .= Stabile::Networks::Remove($networkuuid1);
            }
            if ($networkuuid2 && $networkuuid2 ne '--' && $networkuuid2 ne '0' && $networkuuid2 ne '1') {
                Stabile::Networks::Deactivate($networkuuid2);
                $res .= Stabile::Networks::Remove($networkuuid2);
            }
        }
        $duuid = $domuuid;
    }
    if (@domains) {
        if ($register{$uuid}) {
            delete $register{$uuid};
            tied(%register)->commit;
        }
        $main::updateUI->(
                        {tab=>'servers',
                        user=>$user,
                        type=>'update',
                        message=>((scalar @domains==1)?"Server has been removed":"Stack has been removed!")
                        },
                        {tab=>'images',
                        user=>$user
                        },
                        {tab=>'networks',
                        user=>$user
                        },
                        {tab=>'home',
                        user=>$user,
                        type=>'removal',
                        uuid=>$uuid,
                        domuuid=>$duuid
                        }
                    );
    } else {
        $main::updateUI->(
                        {tab=>'servers',
                        user=>$user,
                        type=>'update',
                        message=>"Nothing to remove!"
                        }
                    );
    }
    if ($engineid && $enginelinked) {
        # Remove domain from origo.io
        my $json_text = qq|{"uuid": "$sysuuid" , "status": "delete"}|;
        $main::postAsyncToOrigo->($engineid, 'updateapps', "[$json_text]");
    }
    return $postreply;
}

sub getPackages {
    my $curimg = shift;

    unless (tie %imagereg,'Tie::DBI', { # Needed for ValidateItem
        db=>'mysql:steamregister',
        table=>'images',
        key=>'path',
        autocommit=>0,
        CLOBBER=>0,
        user=>$dbiuser,
        password=>$dbipasswd}) {throw Error::Simple("Stroke=ERROR Image register could not be accessed")};

    my $mac = $imagereg{$curimg}->{'mac'};
    untie %imagereg;

    my $macip;
    if ($mac && $mac ne '--') {
        unless (tie %nodereg,'Tie::DBI', {
            db=>'mysql:steamregister',
            table=>'nodes',
            key=>'mac',
            autocommit=>0,
            CLOBBER=>1,
            user=>$dbiuser,
            password=>$dbipasswd}) {return 0};
        $macip = $nodereg{$mac}->{'ip'};
        untie %nodereg;
    }
    $curimg =~ /(.+)/; $curimg = $1;
    my $sshcmd;
    if ($macip && $macip ne '--') {
        $sshcmd = "/usr/bin/ssh -q -l irigo -i /var/www/.ssh/id_rsa_www -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no $macip";
    }
    my $apps;

    if ($sshcmd) {
        my $cmd = qq[eval \$(/usr/bin/guestfish --ro -a "$curimg" --i --listen); ]; # sets $GUESTFISH_PID shell var
        $cmd .= qq[root="\$(/usr/bin/guestfish --remote inspect-get-roots)"; ];
        $cmd .= qq[guestfish --remote inspect-get-product-name "\$root"; ];
        $cmd .= qq[guestfish --remote inspect-get-hostname "\$root"; ];
        $cmd .= qq[guestfish --remote inspect-list-applications "\$root"; ];
        $cmd .= qq[guestfish --remote exit];
        $cmd = "$sshcmd '$cmd'";
        $apps = `$cmd`;
    } else {
        my $cmd;
#        my $pid = open my $cmdpipe, "-|",qq[/usr/bin/guestfish --ro -a "$curimg" --i --listen];
            $cmd .= qq[eval \$(/usr/bin/guestfish --ro -a "$curimg" --i --listen); ];
        # Start listening guestfish
        my $daemon = Proc::Daemon->new(
                work_dir => '/usr/local/bin',
                setuid => 'www-data',
                exec_command => $cmd
            ) or do {$posterror .= "Stream=ERROR $@\n";};
        my $pid = $daemon->Init();
        while ($daemon->Status($pid)) {
            sleep 1;
        }
        # Find pid of the listening guestfish
        my $pid2;
        my $t = new Proc::ProcessTable;
        foreach $p ( @{$t->table} ){
            my $pcmd = $p->cmndline;
            if ($pcmd =~ /guestfish.+$curimg/) {
                $pid2 = $p->pid;
                last;
            }
        }
        my $cmd2;
        if ($pid2) {
            $cmd2 .= qq[root="\$(/usr/bin/guestfish --remote=$pid2 inspect-get-roots)"; ];
            $cmd2 .= qq[guestfish --remote=$pid2 inspect-get-product-name "\$root"; ];
            $cmd2 .= qq[guestfish --remote=$pid2 inspect-get-hostname "\$root"; ];
            $cmd2 .= qq[guestfish --remote=$pid2 inspect-list-applications "\$root"; ];
            $cmd2 .= qq[guestfish --remote=$pid2 exit];
        }
        $apps = `$cmd2`;
        $apps .= $cmd2;
    }
    return $apps;
}
