#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.stabile.io/info/stabiledocs/licensing/stabile-open-source-license

package Stabile::Users;

use Error qw(:try);
use Time::Local;
# use Time::HiRes qw( time );
use Config::Simple;
use Text::CSV_XS qw( csv );
use Proc::Daemon;
use MIME::Lite;
use File::Basename;
use Data::Password qw(:all);
use lib dirname (__FILE__);
use Stabile;

$engineid = $Stabile::config->get('ENGINEID') || "";
$enginename = $Stabile::config->get('ENGINENAME') || "";
#$enginelinked = $Stabile::config->get('ENGINE_LINKED') || "";
$showcost = $Stabile::config->get('SHOW_COST') || "";
$cur = $Stabile::config->get('CURRENCY') || "USD";
$engineuser = $Stabile::config->get('ENGINEUSER') || "";
$externaliprangestart = $Stabile::config->get('EXTERNAL_IP_RANGE_START') || "";
$externaliprangeend = $Stabile::config->get('EXTERNAL_IP_RANGE_END') || "";
$proxyiprangestart = $Stabile::config->get('PROXY_IP_RANGE_START') || "";
$proxyiprangeend = $Stabile::config->get('PROXY_IP_RANGE_END') || "";
$proxygw = $Stabile::config->get('PROXY_GW') || "";

$uiuuid;
$uistatus;
$help = 0; # If this is set, functions output help

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
        print "Got error: ", $ex->{-text}, " on line ", $ex->{-line}, "\n";
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
    my $username = $h{"username"} || $h{"uuid"};
    my $obj;
    $action = $action || $h{'action'};
    if ($action=~ /engine$|updateclientui$|updateui$/) {
        $obj = \%h;
        $obj->{pwd} = $obj->{password} if ($obj->{password});
    } else {
        $obj = $register{$username};
        my %hobj = %{$register{$username}};
        $obj = \%hobj; # We do this to get around a weird problem with freeze...
        my @props = qw ( restorefile engineid enginename engineurl username user password pwd fullname email
            opemail alertemail phone opphone opfullname allowfrom allowinternalapi privileges accounts accountsprivileges
            storagepools memoryquota storagequota nodestoragequota vcpuquota externalipquota rxquota txquota billto );
        foreach my $prop (@props) {
            if (defined $h{$prop}) {
                $obj->{$prop} = $h{$prop};
            }
        }
    }
    return $obj;
}

sub Init {
    # Tie database tables to hashes
    unless ( tie(%register,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username'}, $Stabile::dbopts)) ) {return "Unable to access users register"};

    # simplify globals initialized in Stabile.pm
    $tktuser = $tktuser || $Stabile::tktuser;
    $user = $user || $Stabile::user;

    $fullname = $register{$user}->{'fullname'};
    $email = $register{$user}->{'email'};
    $opemail = $register{$user}->{'opemail'};
    $alertemail = $register{$user}->{'alertemail'};
    $phone = $register{$user}->{'phone'};
    $opphone = $register{$user}->{'opphone'};
    $opfullname = $register{$user}->{'opfullname'};
    $allowfrom = $register{$user}->{'allowfrom'};
    $allowinternalapi = $register{$user}->{'allowinternalapi'};
    $lastlogin = $register{$user}->{'lastlogin'};
    $lastloginfrom = $register{$user}->{'lastloginfrom'};

#    if ($register{$user}->{'lastlogin'} ne $tkt) {
#        $register{$user}->{'lastlogin'} = time;
#        $register{$user}->{'lastloginfrom'} = $ENV{'REMOTE_ADDR'};
#        $register{$user}->{'lasttkt'} = $tkt;
#    }

    $Stabile::userstoragequota = 0+ $register{$user}->{'storagequota'};
    $Stabile::usernodestoragequota = 0+ $register{$user}->{'nodestoragequota'};
    $usermemoryquota = 0+ $register{$user}->{'memoryquota'};
    $uservcpuquota = 0+ $register{$user}->{'vcpuquota'};
    $userexternalipquota = 0+ $register{$user}->{'externalipquota'};
    $userrxquota = 0+ $register{$user}->{'rxquota'};
    $usertxquota = 0+ $register{$user}->{'txquota'};

    $storagequota = $Stabile::userstoragequota || $defaultstoragequota;
    $nodestoragequota = $Stabile::usernodestoragequota || $defaultnodestoragequota;
    $memoryquota = $usermemoryquota || $defaultmemoryquota;
    $vcpuquota = $uservcpuquota || $defaultvcpuquota;
    $externalipquota = $userexternalipquota || $defaultexternalipquota;
    $rxquota = $userrxquota || $defaultrxquota;
    $txquota = $usertxquota || $defaulttxquota;

    # Create aliases of functions
    *header = \&CGI::header;

    *Unlinkengine = \&Linkengine;
    *Updateengine = \&Linkengine;
    *Saveengine = \&Linkengine;
    *Syncusers = \&Linkengine;

    *do_help = \&action;
    *do_show = \&do_uuidshow;
    *do_delete = \&do_remove;
    *do_tablelist = \&do_list;
    *do_billingstatus = \&do_billing;
    *do_usage = \&do_billing;
    *do_usagestatus = \&do_billing;
    *do_billingavgstatus = \&do_billing;
    *do_usageavgstatus = \&do_billing;
    *do_upgradeengine = \&privileged_action;
    *do_gear_upgradeengine = \&do_gear_action;
    *do_backupengine = \&privileged_action;
    *do_gear_backupengine = \&do_gear_action;
    *do_restoreengine = \&privileged_action;
    *do_gear_restoreengine = \&do_gear_action;
    *do_releasepressure = \&privileged_action_async;
    *do_gear_releasepressure = \&do_gear_action;

    *do_linkengine = \&privileged_action;
    *do_gear_linkengine = \&do_gear_action;
    *do_saveengine = \&privileged_action_async;
    *do_gear_saveengine = \&do_gear_action;
    *do_unlinkengine = \&privileged_action;
    *do_gear_unlinkengine = \&do_gear_action;
    *do_updateengine = \&privileged_action;
    *do_syncusers = \&privileged_action;
    *do_gear_updateengine = \&do_gear_action;
    *do_gear_syncusers = \&do_gear_action;
    *do_deleteentirely = \&privileged_action;
    *do_gear_deleteentirely = \&do_gear_action;
    *do_vent = \&privileged_action;
    *do_gear_vent = \&do_gear_action;
    *do_updateui = \&privileged_action;
    *do_gear_updateui = \&do_gear_action;
}

sub do_listaccounts {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:common:
List other user accounts current user has access to use and switch to. This is an internal method which includes html
specifically for use with Dojo.
END
    }
    my $common = $params{'common'};
    my %bhash;
    my @accounts = split(/,\s*/, $register{$tktuser}->{'accounts'});
    my @accountsprivs = split(/,\s*/, $register{$tktuser}->{'accountsprivileges'});
    for my $i (0 .. $#accounts) {
        $bhash{$accounts[$i]} = {
            id=>$accounts[$i],
            privileges=>$accountsprivs[$i] || 'r'
        } if ($register{$accounts[$i]}); # Only include accounts that exist on this engine
    };
    $bhash{$tktuser} = {id=>$tktuser, privileges=>$privileges};
    delete $bhash{$user};
    $bhash{'common'} = {id=>'common', privileges=>'--'} if ($common);
    my @bvalues = values %bhash;
    unshift(@bvalues, {id=>$user, privileges=>$privileges});
    my $logout = {privileges=>'', id=>'<span class="glyphicon glyphicon-log-out" aria-hidden="true" style="font-size:15px;color:#3c3c3c; vertical-align:top; margin-top:8px;"></span> Log out '};
    push(@bvalues, $logout) unless ($common);
    $postreply = "{\"identifier\": \"id\",\"label\": \"id\", \"items\":" . JSON::to_json(\@bvalues, {pretty=>1}) . "}";
    return $postreply;
}

sub do_listids {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
List other user accounts current user has read access to. Call with flat=1 if you want a flat array.
END
    }
    require "$Stabile::basedir/cgi/images.cgi";
    my $backupdevice = Stabile::Images::Getbackupdevice('', 'getbackupdevice');
    my $imagesdevice = Stabile::Images::Getimagesdevice('', 'getimagesdevice');
    my $mounts = `cat /proc/mounts | grep zfs`;
    my %engine_h;
    my $zbackupavailable = ( (($mounts =~ /$backupdevice\/backup (\S+) zfs/) && ($mounts =~ /$imagesdevice\/images (\S+) zfs/) )?1:'');
    my $jsontext = qq|{"identifier": "id","label": "id", "items":[| .
              qq|{"id": "$user", "privileges": "$privileges", "userprivileges": "$dbprivileges", "tktuser": "$tktuser", |.
              qq|"storagequota": $storagequota, "nodestoragequota": $nodestoragequota, "memoryquota": $memoryquota, "vcpuquota": $vcpuquota, |.
              qq|"fullname": "$fullname", "email": "$email", "opemail": "$opemail", "alertemail": "$alertemail", |.
              qq|"phone": "$phone", "opphone": "$opphone", "opfullname": "$opfullname", "appstoreurl": "$appstoreurl", |.
              qq|"allowfrom": "$allowfrom", "lastlogin": "$lastlogin", "lastloginfrom": "$lastloginfrom", "allowinternalapi": "$allowinternalapi", "billto": "$billto", |;

    if ($isadmin && $engineid) {
        $engine_h{"engineid"} = $engineid;
        $engine_h{"engineuser"} = $engineuser;
        $engine_h{"externaliprangestart"} = $externaliprangestart;
        $engine_h{"externaliprangeend"} = $externaliprangeend;
        $engine_h{"proxyiprangestart"} = $proxyiprangestart;
        $engine_h{"proxyiprangeend"} = $proxyiprangeend;
        $engine_h{"proxygw"} = $proxygw;

        $engine_h{"disablesnat"} = $disablesnat;
        $engine_h{"imagesdevice"} = $imagesdevice;
        $engine_h{"backupdevice"} = $backupdevice;

        my $nodecfg = new Config::Simple("/etc/stabile/nodeconfig.cfg");
        my $readlimit = $nodecfg->param('VM_READ_LIMIT'); # e.g. 125829120 = 120 * 1024 * 1024 = 120 MB / s
        my $writelimit = $nodecfg->param('VM_WRITE_LIMIT');
        my $iopsreadlimit = $nodecfg->param('VM_IOPS_READ_LIMIT'); # e.g. 1000 IOPS
        my $iopswritelimit = $nodecfg->param('VM_IOPS_WRITE_LIMIT');
        $engine_h{"vmreadlimit"} = $readlimit;
        $engine_h{"vmwritelimit"} = $writelimit;
        $engine_h{"vmiopsreadlimit"} = $iopsreadlimit;
        $engine_h{"vmiopswritelimit"} = $iopswritelimit;

        $engine_h{"zfsavailable"} = $zbackupavailable;
        $engine_h{"downloadmasters"} = $downloadmasters;
    }
    if (-e "/var/www/stabile/static/img/logo-icon-" . $ENV{HTTP_HOST} . ".png") {
        $jsontext .= qq|"favicon": "/stabile/static/img/logo-icon-$ENV{HTTP_HOST}.png", |;
    }
    $engine_h{"enginename"} = $enginename;
    $engine_h{"enginelinked"} = $enginelinked;
    $jsontext .= "\"showcost\": \"$showcost\", ";
    $jsontext .= "\"externalipquota\": $externalipquota, \"rxquota\": $rxquota, \"txquota\": $txquota, ";
    $jsontext .= qq|"defaultstoragequota": $defaultstoragequota, "defaultnodestoragequota": $defaultnodestoragequota, "defaultmemoryquota": $defaultmemoryquota, "defaultvcpuquota": $defaultvcpuquota, |;
    $jsontext .= "\"defaultexternalipquota\": $defaultexternalipquota, \"defaultrxquota\": $defaultrxquota, \"defaulttxquota\": $defaulttxquota, ";
    $jsontext .= qq|"engine": | . to_json(\%engine_h);
    $jsontext .= "},  ";

    $jsontext .= "{\"id\": \"common\", \"privileges\": \"--\"," .
      "\"fullname\": \"--\", \"email\": \"--\"," .
      "\"storagequota\": 0, \"memoryquota\": 0, \"vcpuquota\": 0, \"externalipquota\": 0," .
      "\"rxquota\": 0, \"txquota\": 0}";

    $jsontext .= ", {\"id\": \"$billto\"}" if ($billto && $billto ne '--');

    foreach my $aid (keys %ahash) {
        my $privs = $ahash{$aid};
        $jsontext .= qq|, {"id": "$aid", "privileges": "$privs"}| unless ($aid eq $user || $aid eq $billto);
    }

    $jsontext .= "]}";
    # Create ui_update link in case we are logging in with a remotely generated ticket, i.e. not passing through login.cgi
    `/bin/ln -s ../ui_update.cgi ../cgi/ui_update/$user~ui_update.cgi` unless (-e "../cgi/ui_update/$user~ui_update.cgi");
    $postreply = to_json(from_json($jsontext), {pretty=>1});
    return $postreply;
}


sub do_listengines{
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
List other engines user has access to
END
    }
    if ($enginelinked) {
        require LWP::Simple;
        my $browser = LWP::UserAgent->new;
        $browser->agent('stabile/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );

        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';

        $postreq->{'engineid'} = $engineid;
#        $postreq->{'user'} = $tktuser;
        $postreq->{'user'} = $user;
        $postreq->{'enginetkthash'} = Digest::SHA::sha512_hex($tktkey);

        my $content = $browser->post("https://www.stabile.io/irigo/engine.cgi?action=listengines", $postreq)->content();
        if ($content =~ /ERROR:(.+)"/) {
            $postreply = qq|{"identifier": "url", "label": "name", "items": [{"url": "# $1", "name": "$enginename"}]}|;
        } else {
            $postreply = qq|{"identifier": "url", "label": "name", "items": $content}|;
        }
    } else {
        $postreply = qq|{"identifier": "url", "label": "name", "items": [{"url": "#", "name": "$enginename"}]}|;
    }
    return $postreply;
}

sub do_billing {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,username,month,startmonth,endmonth,format:
List usage data, optionally for specific server/system [uuid] or user [username]. May be called as usage, usagestatus or usageavgstatus.
When called as "usage", format may be csv, in which case startmonth and endmonth may be specified.
END
    }
    my $buser = $params{'user'} || $params{'username'} || $user;
    my $bmonth = $params{'month'} || $month;
    $bmonth = substr("0$bmonth", -2);
    my $byear = $params{'year'} || $year;
    my $vcpu=0, $memory=0, $virtualsize=0, $nodevirtualsize=0, $backupsize=0, $externalip=0;
    my $rx = 0;
    my $tx = 0;
    my $vcpuavg = 0;
    my $externalipavg = 0;
    $uuid = '' if ($register{$uuid}); # check if $uuid was set to $user because no actual uuid passed

    if ($user eq $buser || index($privileges,"a")!=-1) {
         my %stats = collectBillingData( $uuid, $buser, $bmonth, $byear, $showcost );
         my $memoryquotagb = int(0.5 + 100*$memoryquota/1024)/100;
         my $storagequotagb = int(0.5 + 100*$storagequota/1024)/100;
         my $nodestoragequotagb = int(0.5 + 100*$nodestoragequota/1024)/100;
         my $irigo_cost = ($showcost?"showcost":"hidecost");

         if ($action eq "billing" || $action eq "usage") {
             if ($params{'format'} eq 'csv') {
                 $postreply = header("text/plain");
                 my $startmonth = $params{'startmonth'} || 1;
                 my $endmonth = $params{'endmonth'} || $bmonth;
                 my @vals;
                 for (my $i=$startmonth; $i<=$endmonth; $i++) {
                     my $m = substr("0$i", -2);
                     my %mstats = collectBillingData( $uuid, $buser, $m, $byear, $showcost );
                     push @vals, \%mstats;
                 }
                 csv(in => \@vals, out => \my $csvdata);
                 $postreply .= $csvdata;
             } else {
                 my $json_text = JSON::to_json(\%stats, {pretty => 1});
                 $postreply = "$json_text";
             }

         } elsif ($action eq "billingstatus" || $action eq "usagestatus") {
             my $virtualsizegb = $stats{'virtualsize'};
             my $backupsizegb = $stats{'backupsize'};
             my $externalip = $stats{'externalip'};
             my $memorygb = $stats{'memory'};
             my $nodevirtualsizegb = $stats{'nodevirtualsize'};
             $rx = $stats{'rx'};
             $tx = $stats{'tx'};
             $vcpu = $stats{'vcpu'};

             my $res;
             if ($params{'format'} eq 'html') {
                 $postreply .= header("text/html");
                 $res .= qq[<tr><th>Ressource</th><th>Quantity</th><th class="$irigo_cost">Cost/month</th><th>Quota</th></tr>];
                 $res .= qq[<tr><td>vCPU's:</td><td align="right">$vcpu</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$vcpu*$vcpuprice) . qq[</td><td align="right">$vcpuquota</td></tr>];
                 $res .= qq[<tr><td>Memory:</td><td align="right">$memorygb GB</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$memorygb*$memoryprice) . qq[</td><td align="right">$memoryquotagb GB</td></tr>];
                 $res .= qq[<tr><td>Shared storage:</td><td align="right">$virtualsizegb GB</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$virtualsizegb*$storageprice) . qq[</td><td align="right">$storagequotagb GB</td></tr>];
                 $res .= qq[<tr><td>Node storage:</td><td align="right">$nodevirtualsizegb GB</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$nodevirtualsizegb*$nodestorageprice) . qq[</td><td align="right">$nodestoragequotagb GB</td></tr>];
                 $res .= qq[<tr><td>Backup storage (est.):</td><td align="right">$backupsizegb GB</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$backupsizegb*$storageprice) . qq[</td><td align="right">&infin;</td></tr>];
                 $res .= qq[<tr><td>External IP addresses:</td><td align="right">$externalip</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$externalip*$externalipprice) . qq[</td><td align="right">$externalipquota</td></tr>];
                 if (!$uuid) {
                     $res .= qq[<tr><td>Network traffic out:</td><td align="right">] . $rx . qq[ GB</td><td align="right" class="$irigo_cost">$cur 0</td><td align="right">] . int(0.5 + $rxquota/1024/1024) . qq[ GB</td></tr>];
                     $res .= qq[<tr><td>Network traffic in:</td><td align="right">] . $tx . qq[ GB</td><td align="right" class="$irigo_cost">$cur 0</td><td align="right">] . int(0.5 + $txquota/1024/1024) . qq[ GB</td></tr>];
                 }

                 $res =~ s/-1/&infin;/g;
                 $res =~ s/>0 .B<\/td><\/tr>/>&infin;<\/td><\/tr>/g;
                 $postreply .= qq[<table cellspacing="0" noframe="void" norules="rows" class="systemTables">$res</table>];
             } else {
                 my $bill = {
                     vcpus => {quantity => $vcpu, quota => $vcpuquota},
                     memory => {quantity => $memorygb, unit => 'GB', quota => $memoryquotagb},
                     shared_storage => {quantity => $virtualsizegb, unit => 'GB', quota => $storagequotagb},
                     node_storage => {quantity => $nodevirtualsizegb, unit => 'GB', quota => $nodestoragequotagb},
                     backup_storage => {quantity => $backupsizegb, unit => 'GB'},
                     external_ips => {quantity => $externalip, quota => $externalipquota},
                     network_traffic_out => {quantity => $rx, unit => 'GB', quota => int(0.5 + $rxquota/1024/1024)},
                     network_traffic_in => {quantity => $tx, unit => 'GB', quota => int(0.5 + $txquota/1024/1024)}
                 };
                 if ($showcost) {
                     $bill->{vcpus}->{cost} = int(0.5+$vcpu*$vcpuprice);
                     $bill->{memory}->{cost} = int(0.5+$memorygb*$memoryprice);
                     $bill->{shared_storage}->{cost} = int(0.5+$virtualsizegb*$storageprice);
                     $bill->{node_storage}->{cost} = int(0.5+$nodevirtualsizegb*$nodestorageprice);
                     $bill->{backup_storage}->{cost} = int(0.5+$backupsizegb*$storageprice);
                     $bill->{external_ips}->{cost} = int(0.5+$externalip*$externalipprice);
                     $bill->{currency} = $cur;
                     $bill->{username} = $buser;
                 }
                 $postreply .= to_json($bill, {pretty=>1});
             }
         } elsif ($action eq "billingavgstatus" || $action eq "usageavgstatus") {
             my $virtualsizeavggb = $stats{'virtualsizeavg'};
             my $backupsizeavggb = $stats{'backupsizeavg'};
             my $memoryavggb = $stats{'memoryavg'};
             my $nodevirtualsizeavggb = $stats{'nodevirtualsizeavg'};
             $vcpuavg = $stats{'vcpuavg'};
             $externalipavg = $stats{'externalipavg'};
             $rx = $stats{'rx'};
             $tx = $stats{'tx'};
             if ($params{'format'} eq 'html') {
                 $postreply .= header("text/html");
                 my $res;
                 $res .= qq[<tr><th>Ressource</th><th>Quantity</th><th class="$irigo_cost">Cost/month</th><th>Quota</th></tr>];
                 $res .= qq[<tr><td>vCPU's:</td><td align="right">] . int(0.5+100*$vcpuavg)/100 . qq[</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$vcpuavg*$vcpuprice) . qq[</td><td align="right">$vcpuquota</td></tr>];
                 $res .= qq[<tr><td>Memory:</td><td align="right">$memoryavggb GB</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$memoryavggb*$memoryprice) . qq[</td><td align="right">$memoryquotagb GB</td></tr>];
                 $res .= qq[<tr><td>Shared storage:</td><td align="right">$virtualsizeavggb GB</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$virtualsizeavggb*$storageprice) . qq[</td><td align="right">$storagequotagb GB</td></tr>];
                 $res .= qq[<tr><td>Node storage:</td><td align="right">$nodevirtualsizeavggb GB</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$nodevirtualsizeavggb*$nodestorageprice) . qq[</td><td align="right">$nodestoragequotagb GB</td></tr>];
                 $res .= qq[<tr><td>Backup storage (est.):</td><td align="right">$backupsizeavggb GB</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$backupsizeavggb*$storageprice) . qq[</td><td align="right">&infin;</td></tr>];
                 $res .= qq[<tr><td>External IP addresses:</td><td align="right">] . int(0.5+100*$externalipavg)/100 . qq[</td><td align="right" class="$irigo_cost">$cur ] . int(0.5+$externalipavg*$externalipprice) . qq[</td><td align="right">$externalipquota</td></tr>];
                 $res .= qq[<tr><td>Network traffic in:</td><td align="right">] . int(0.5 + $rx) . qq[ GB</td><td align="right" class="$irigo_cost">$cur 0</td><td align="right">] . int(0.5 + $rxquota/1024/1024) . qq[ GB</td></tr>];
                 $res .= qq[<tr><td>Network traffic out:</td><td align="right">] . int(0.5 + $tx) . qq[ GB</td><td align="right" class="$irigo_cost">$cur 0</td><td align="right">] . int(0.5 + $txquota/1024/1024) . qq[ GB</td></tr>];

                 $res =~ s/-1/&infin;/g;
                 $res =~ s/>0 .B<\/td><\/tr>/>&infin;<\/td><\/tr>/g;
                 $postreply .= qq[<table cellspacing="0" noframe="void" norules="rows" class="systemTables">$res</table>];
             } else {
                 my $bill = {
                     vcpus => {quantity => $vcpuavg, quota => $vcpuquota},
                     memory => {quantity => $memoryavggb, unit => 'GB', quota => $memoryquotagb},
                     shared_storage => {quantity => $virtualsizeavggb, unit => 'GB', quota => $storagequotagb},
                     node_storage => {quantity => $nodevirtualsizeavggb, unit => 'GB', quota => $nodestoragequotagb},
                     backup_storage => {quantity => $backupsizeavggb, unit => 'GB'},
                     external_ips => {quantity => $externalipavg, quota => $externalipquota},
                     network_traffic_out => {quantity => int(0.5 + $rx), unit => 'GB', quota => int(0.5 + $rxquota/1024/1024)},
                     network_traffic_in => {quantity => int(0.5 + $tx), unit => 'GB', quota => int(0.5 + $txquota/1024/1024)}
                 };
                 if ($showcost) {
                     $bill->{vcpus}->{cost} = int(0.5+$vcpuavg*$vcpuprice);
                     $bill->{memory}->{cost} = int(0.5+$memoryavggb*$memoryprice);
                     $bill->{shared_storage}->{cost} = int(0.5+$virtualsizeavggb*$storageprice);
                     $bill->{node_storage}->{cost} = int(0.5+$nodevirtualsizeavggb*$nodestorageprice);
                     $bill->{backup_storage}->{cost} = int(0.5+$backupsizeavggb*$storageprice);
                     $bill->{external_ips}->{cost} = int(0.5+$externalipavg*$externalipprice);
                     $bill->{currency} = $cur;
                     $bill->{username} = $buser;
                 }
                 $postreply .= to_json($bill, {pretty=>1});
             }
        }
    } else {
        $postreply .= "Status=ERROR no privileges!!\n";
    }
    return $postreply;
}

sub do_listenginebackups {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
List the backups of this engine's configuration in the registry.
END
    }
    if ($enginelinked) {
        require LWP::Simple;
        my $browser = LWP::UserAgent->new;
        $browser->agent('stabile/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );

        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';

        $postreq->{'engineid'} = $engineid;
        $postreq->{'enginetkthash'} = Digest::SHA::sha512_hex($tktkey);

        my $content = $browser->post("https://www.stabile.io/irigo/engine.cgi?action=listbackups", $postreq)->content();
        if ($content =~ /\[\]/) {
            $postreply = qq|{"identifier": "path", "label": "name", "items": [{"path": "#", "name": "No backups"}]}|;
        } else {
            $postreply = qq|{"identifier": "path", "label": "name", "items": $content}|;
        }
    } else {
        $postreply = qq|{"identifier": "path", "label": "name", "items": [{"path": "#", "name": "Engine not linked"}]}|;
    }
    return $postreply;
}

sub Backupengine {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Backup this engine's configuration to the registry.
END
    }
    my $backupname = "$enginename.$engineid.$pretty_time";
    $backupname =~ tr/:/-/; # tar has a problem with colons in filenames
    if (-e "/tmp/$backupname.tgz") {
        $postreply .= "Status=ERROR Engine is already being backed up";
    } else {
        $res .= `mysqldump --ignore-table=steamregister.nodeidentities steamregister > /etc/stabile/steamregister.sql`;
        $res .= `cp /etc/apache2/conf-available/auth_tkt_cgi.conf /etc/stabile`;
        $res .= `cp /etc/apache2/ssl/*.crt /etc/stabile`;
        $res .= `cp /etc/apache2/ssl/*.pem /etc/stabile`;
        $res .= `cp /etc/apache2/ssl/*.key /etc/stabile`;
        $res .= `cp /etc/hosts.allow /etc/stabile`;
        $res .= `cp /etc/mon/mon.cf /etc/stabile`;

        # copy default node configuration to /etc/stabile
        unless ( tie(%register,'Tie::DBI', Hash::Merge::merge({table=>'nodeidentities', key=>'identity'}, $Stabile::dbopts)) ) {return "Unable to access identity register"};

        my $defaultpath = $idreg{'default'}->{'path'} . "/casper/filesystem.dir/etc/stabile/nodeconfig.cfg";
        $res .= `cp $defaultpath /etc/stabile`;

        # Make tarball
        my $cmd = qq[(cd /etc/stabile; /bin/tar -czf "/tmp/$backupname.tgz" * 2>/dev/null)];
        $res .= `$cmd`;

        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
        my $enginetkthash = Digest::SHA::sha512_hex($tktkey);

        my $res = `/usr/bin/curl -k -F engineid=$engineid -F enginetkthash=$enginetkthash -F filedata=@"/tmp/$backupname.tgz" https://www.stabile.io/irigo/engine.cgi?action=backup`;
        if ($res =~ /OK: $backupname.tgz received/) {
            $postreply .= "Status=OK Engine configuration saved to the registry";
            $main::syslogit->($user, "info", "Engine configuration saved to the registry");
            unlink("/tmp/$backupname.tgz");
        } else {
            $postreply .= "Status=ERROR Problem backing configuration up to the registry\n$res\n";
        }
    }
    return $postreply;
}

sub Upgradeengine {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Try to upgrade this engine to latest release from the registry
END
    }
    $postreply = "Status=OK Requesting upgrade of Steamgine\n";
    `echo "UPGRADE=1" >> /etc/stabile/config.cfg` unless ( `grep ^UPGRADE=1 /etc/stabile/config.cfg`);
    `/usr/bin/pkill pressurecontrol`;
    #`service pressurecontrol stop`, "\n";
    #print `service pressurecontrol start`, "\n";
}

sub do_billengine {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Submit billing data for this engine to the registry.
END
    }
    require LWP::Simple;
    my $browser = LWP::UserAgent->new;
    $browser->agent('stabile/1.0b');
    $browser->protocols_allowed( [ 'http','https'] );

    my $bmonth = $params{'month'} || $month;
    $bmonth = substr("0$bmonth", -2);
    my $byear = $params{'year'} || $year;
    $showcost = 1;

    my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
    my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
    my $tkthash = Digest::SHA::sha512_hex($tktkey);

    my $postreq = ();
    my %bill;
    my @regvalues = values %register; # Sort by id
    foreach my $valref (@regvalues) {
        my $cuser = $valref->{'username'};
        my %stats = collectBillingData( '', $cuser, $bmonth, $byear, $showcost );
        $bill{"$cuser-$byear-$bmonth"} = \%stats;
    }
    $postreq->{'engineid'} = $engineid;
    $postreq->{'enginetkthash'} = $tkthash;
    $postreq->{'keywords'} = JSON::to_json(\%bill, {pretty=>1});
    my $url = "https://www.stabile.io/irigo/engine.cgi";
    $content = $browser->post($url, $postreq)->content();
    $postreply = "Status=OK Billed this engine ($engineid)\n";
    $postreply .= "$postreq->{'keywords'}\n$content";
    return $postreply;
}

sub Linkengine {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
PUT:username,password,engineid,enginename,engineurl:
Links engine to the registry
END
    }
    return "Status=Error Not allowed\n" unless ($isadmin || ($user eq $engineuser));
    my $linkaction = 'update';
    $linkaction = 'link' if ($action eq 'linkengine');
    $linkaction = 'unlink' if ($action eq 'unlinkengine');
    $linkaction = 'update' if ($action eq 'updateengine');
    $linkaction = 'update' if ($action eq 'syncusers');

    require LWP::Simple;
    my $browser = LWP::UserAgent->new;
    $browser->agent('stabile/1.0b');
    $browser->protocols_allowed( [ 'http','https'] );

    my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
    my $tktkey = $tktcfg->get('TKTAuthSecret') || '';

    my $postreq = ();
    $postreq->{'user'} = $user || $obj->{'username'};
    $postreq->{'engineid'} = $obj->{'engineid'} || $engineid;
    $postreq->{'pwd'} = $obj->{'pwd'} if ($obj->{'pwd'});
    $postreq->{'enginename'} = $obj->{'enginename'} if ($obj->{'enginename'});
    $postreq->{'engineurl'} = $obj->{'engineurl'} if ($obj->{'engineurl'});
    if ($tktkey) {
        if ($action eq 'linkengine') {
            $main::syslogit->($user, "info", "Linking engine with the registry");
            $postreq->{'enginetktkey'} = $tktkey;
        } else {
            $postreq->{'enginetkthash'} = Digest::SHA::sha512_hex($tktkey);
        }
    }
    if ($action eq "saveengine") { # Save request from the registry - don't post back
        # Pressurecontrol reads new configuration data from the registry, simply reload it
        my $pressureon = !(`systemctl is-active pressurecontrol` =~ /inactive/);
        $postreply = ($pressureon)? "Status=OK Engine updating...\n":"Status=OK Engine not updating because pressurecontrol not active\n";
        $postreply .= `systemctl restart pressurecontrol` if ($pressureon);
    } else {
        my $res;
        my $cfg = new Config::Simple("/etc/stabile/config.cfg");
        if ($action eq 'linkengine' || $action eq 'syncusers') {
            # Send engine users to the registry
            my @vals = values %register;
            my $json = JSON::to_json(\@vals);
            $json =~ s/null/""/g;
            $json = URI::Escape::uri_escape($json);
            $postreq->{'POSTDATA'} = $json;
        }
        if ($action eq 'linkengine' || $action eq 'updateengine') {
            # Update name in config file
            if ($postreq->{'enginename'} && $cfg->param("ENGINENAME") ne $postreq->{'enginename'}) {
                $cfg->param("ENGINENAME", $postreq->{'enginename'});
                $cfg->save();
            }
            # Send entire engine config file to the registry
            my %cfghash = $cfg->vars();
            foreach my $param (keys %cfghash) {
                $param =~ /default\.(.+)/; # Get rid of default. prefix
                if ($1) {
                    my $k = $1;
                    my @cvals = $cfg->param($param);
                    my $cval = join(", ", @cvals);
                    $postreq->{$k} = URI::Escape::uri_escape($cval);
                }
            }
            # Send entire engine piston config file to the registry
            my $nodeconfigfile = "/mnt/stabile/tftp/bionic/casper/filesystem.dir/etc/stabile/nodeconfig.cfg";
            if (-e $nodeconfigfile) {
                my $pistoncfg = new Config::Simple($nodeconfigfile);
                %cfghash = $pistoncfg->vars();
                foreach my $param (keys %cfghash) {
                    $param =~ /default\.(.+)/; # Get rid of default. prefix
                    if ($1) {
                        my $k = $1;
                        my @cvals = $pistoncfg->param($param);
                        my $cval = join(", ", @cvals);
                        $postreq->{$k} = URI::Escape::uri_escape($cval);
                    }
                }
            }
        }
        if ($linkaction eq 'link' || $enginelinked) {
            my $content = $browser->post("https://www.stabile.io/irigo/engine.cgi?action=$linkaction", $postreq)->content();
            if ($content =~ /(Engine linked|Engine not linked|Engine unlinked|Engine updated|Unknown engine|Invalid credentials .+\.)/i) {
                $res = "Status=OK $1";
                my $linked = 1;
                $linked = 0 unless ($content =~ /Engine linked/i || $content =~ /Engine updated/i);
                $cfg->param("ENGINE_LINKED", $linked);
                $cfg->save();
            } elsif ($action eq 'syncusers' || $action eq 'linkengine') { # If we send user list to the registry we get merged list back
                if ($content =~ /^\[/) { # Sanity check to see if we got json back
                    $res .= "Status=OK Engine linked\n" if ($action eq 'linkengine');
                    # Update engine users with users from the registry
                    $res .= updateEngineUsers($content);
                    $res .= "Status=OK Users synced with registry\n";
                    $main::updateUI->({ tab => 'users', type=>'update', user=>$user});
                }
                $res .= "$content" unless ($res =~ /Status=OK/); # Only add if there are problems
            }
            $postreply = $res;
            $content =~ s/\n/ - /;
            $res =~ s/\n/ - /;
            $main::syslogit->($user, "info", "$content");
        } else {
            $postreply .= "Status=OK Engine not linked, saving name\n";
        }
    }
    return $postreply;
}

sub Releasepressure {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Restarts pressurecontrol.
END
    }
    my $res;
    unless (`systemctl is-active pressurecontrol` =~ /inactive/) {
        my $daemon = Proc::Daemon->new(
            work_dir => '/usr/local/bin',
            exec_command => "systemctl restart pressurecontrol"
        ) or do {$postreply .= "Status=ERROR $@\n";};
        my $pid = $daemon->Init();
#        $res = `systemctl restart pressurecontrol`;
        return "Status=OK Venting...\n";
    } else {
        return "Status=OK Not venting\n";
    }
}

sub do_enable {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:username:
Enable a user.
END
    }
    my $username = $obj->{'username'};
    if ($isadmin || ($user eq $engineuser)) {
        my $uprivileges = $register{$username}->{'privileges'};
        $uprivileges =~ s/d//;
        $uprivileges .= 'n' unless ($uprivileges =~ /n/);# These are constant sources of problems - enable by default when enabling users to alleviate situation
        $register{$username}->{'privileges'} = $uprivileges;
        $register{$username}->{'allowinternalapi'} = 1;
        $postreply .= "Status=OK User $username enabled\n";
    } else {
        $postreply .= "Status=ERROR Not allowed\n";
    }
    $uiuuid = $username;
    return $postreply;
}

sub do_disable {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:username:
Disable a user.
END
    }
    my $username = $obj->{'username'};
    if ($isadmin || ($user eq $engineuser)) {
        my $uprivileges = $register{$username}->{'privileges'};
        $uprivileges .= 'd' unless ($uprivileges =~ /d/);
        $register{$username}->{'privileges'} = $uprivileges;
        $postreply .= "Stream=OK User $username disabled, halting servers...\n";
        require "$Stabile::basedir/cgi/servers.cgi";
        $Stabile::Servers::console = 1;
        $postreply .= Stabile::Servers::destroyUserServers($username,1);
        `/bin/rm /tmp/$username~*.tasks`;
    } else {
        $postreply .= "Status=ERROR Not allowed\n";
    }
    $uiuuid = $username;
    return $postreply;
}

sub Updateui {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:username,message,tab:
Update the UI for given user if logged into UI.
END
    }
    my $username = $obj->{'username'} || $user;
    my $message = $obj->{'message'};
    my $tab = $obj->{'tab'} || 'home';
    if ($isadmin || ($username eq $user) || ($user eq $engineuser)) {
        $postreply = $main::updateUI->({ tab => $tab, user => $username, message =>$message, type=>'update'});
    } else {
        $postreply = "Status=ERROR Not allowed\n";
    }
}

sub do_updateclientui {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:username,message,tab,type:
Update the UI for given user if logged into UI.
END
    }
    my $username = $obj->{'username'} || $user;
    my $message = $obj->{'message'};
    my $tab = $obj->{'tab'} || 'home';
    my $type= $obj->{'type'} || 'update';
    if ($isadmin || ($username eq $user) || ($user eq $engineuser)) {
        $postreply = $main::updateUI->({ tab => $tab, user => $username, message =>$message, type=>$type});
    } else {
        $postreply = "Status=ERROR Not allowed\n";
    }
}

sub Vent {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Restart pressurecontrol.
END
    }
    `systemctl restart pressurecontrol`;
    $postreply = "Status=OK Restarting pressurecontrol\n";
    return $postreply;
}

sub Deleteentirely {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:username:
Deletes a user and all the user's servers, images, networks etc. Warning: This destroys data
END
    }
    my $username = $obj->{'username'};
    my $reply = "Status=OK Removed $username\n";
    if (($isadmin || ($user eq $engineuser)) && $register{$username} && !($register{$username}->{'privileges'} =~ /a/) && !($username eq $engineuser)) {
        #Never delete admins
        my @dusers = ($username);
        # Add list of subusers - does not look like a good idea
        # foreach my $u (values %register) {
        #     push @dusers, $u->{'username'} if ($u->{'billto'} && $u->{'billto'} eq $username);
        # };

        foreach my $uname (@dusers) {
            next if ($register{$uname}->{privileges} =~ /a/); #Never delete admins
            $main::updateUI->({ tab => 'users', type=>'update', user=>$user, username=>$username, status=>'deleting'});

            $postreply .= "Stream=OK Deleting user $uname and all associated data!!!\n";

            require "$Stabile::basedir/cgi/servers.cgi";
            $Stabile::Servers::console = 1;

            require "$Stabile::basedir/cgi/systems.cgi";
            $Stabile::Systems::console = 1;
            Stabile::Systems::removeusersystems($uname);
            Stabile::Servers::removeUserServers($uname);

            require "$Stabile::basedir/cgi/images.cgi";
            $Stabile::Images::console = 1;
            $postreply .= Stabile::Images::removeUserImages($uname);

            require "$Stabile::basedir/cgi/networks.cgi";
            $Stabile::Networks::console = 1;
            Stabile::Networks::Removeusernetworks($uname);

            remove($uname);
            $reply = "$reply\n$postreply";

            # Also remove billing data, so next user with same username does not get old billing data
            `echo "delete from billing_domains where usernodetime like '$uname-%';" | mysql steamregister`;
            `echo "delete from billing_images where userstoragepooltime like '$uname-%';" | mysql steamregister`;
            `echo "delete from billing_networks where useridtime like '$uname-%';" | mysql steamregister`;
        }
        $main::updateUI->({tab => 'users', type=>'update', user=>$user});

    } else {
        $postreply .= "Stream=ERROR Cannot delete user $username - you cannot delete administrators!\n";
        $reply = $postreply;
    }
    return $reply;
}

sub do_save {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
POST:username, fullname, email, opemail, alertemail, phone, opphone, opfullname, allowfrom, allowinternalapi, accounts, accountsprivileges, storagepools, memoryquota, storagequota, nodestoragequota, vcpuquota, externalipquota, rxquota, txquota, billto:
Saves a user. If [username] does not exist, it is created if privileges allow this.
END
    }
    my $username = $obj->{"username"};
    unless ($username && (($user eq $username) || $isadmin || ($user eq $engineuser))) {
        $postreply = "Status=ERROR Please provide a valid username\n";
        return $postreply;
    }
    my $password = '';
    my $reguser = $register{$username};
    if ($obj->{"password"} && $obj->{"password"} ne '--') {
        if (length $obj->{'password'} == 86) {
            $password = $obj->{"password"}; # This is already encoded
        } else {
            $password = $obj->{"password"};
            $MAXLEN = 20;
            my $msg = IsBadPassword($password);
            if ($msg) {
                $postreply = "Status=Error $msg - please choose a stronger password\n";
                $postmsg = "$msg - please choose a stronger password";
                return $postreply;
            } else {
                $password = Digest::SHA::sha512_base64($password);
            }
        }
    } else {
        $password = $reguser->{'password'};
    }
    my $fullname = $obj->{"fullname"} || $reguser->{'fullname'};
    my $email = $obj->{"email"} || $reguser->{'email'};
    my $opemail = $obj->{"opemail"} || $reguser->{'opemail'};
    my $alertemail = $obj->{"alertemail"} || $reguser->{'alertemail'};
    my $phone = $obj->{"phone"} || $reguser->{'phone'};
    my $opphone = $obj->{"opphone"} || $reguser->{'opphone'};
    my $opfullname = $obj->{"opfullname"} || $reguser->{'opfullname'};
    my $allowfrom = $obj->{"allowfrom"} || $reguser->{'allowfrom'};
    my $allowinternalapi = $obj->{"allowinternalapi"} || $reguser->{'allowinternalapi'};

    if ($allowfrom) {
        my @allows = split(/(,\s*|\s+)/, $allowfrom);
        $allowfrom = '';
        foreach my $ip (@allows) {
            $allowfrom  .= "$1$2, " if ($ip =~ /(\d+\.\d+\.\d+\.\d+)(\/\d+)?/);
        }
        $allowfrom = substr($allowfrom,0,-2);
    }

    my $uprivileges = $reguser->{'privileges'};
    my $uaccounts = $reguser->{'accounts'};
    my $uaccountsprivileges = $reguser->{'accountsprivileges'};
    my $storagepools = $reguser->{'storagepools'};
    my $memoryquota = $reguser->{'memoryquota'};
    my $storagequota = $reguser->{'storagequota'};
    my $nodestoragequota = $reguser->{'nodestoragequota'};
    my $vcpuquota = $reguser->{'vcpuquota'};
    my $externalipquota = $reguser->{'externalipquota'};
    my $rxquota = $reguser->{'rxquota'};
    my $txquota = $reguser->{'txquota'};
    my $tasks = $reguser->{'tasks'};
    my $ubillto = $reguser->{'billto'};
    my $created = $reguser->{'created'} || $current_time; # set created timestamp for new users

    # Only allow admins to change user privileges and quotas
    if ($isadmin || $user eq $engineuser) {
        $uprivileges = $obj->{"privileges"} || $reguser->{'privileges'};
        $uprivileges = '' if ($uprivileges eq '--');
        $uprivileges = 'n' if (!$reguser->{'username'} && !$uprivileges); # Allow new users to use node storage unless explicitly disallowed
        $uprivileges =~ tr/adnrpu//cd; # filter out non-valid privileges
        $uprivileges =~ s/(.)(?=.*?\1)//g; # filter out duplicates using positive lookahead
        $storagepools = ($obj->{"storagepools"} || $obj->{"storagepools"} eq '0')?$obj->{"storagepools"} : $reguser->{'storagepools'};
        $memoryquota = (defined $obj->{"memoryquota"}) ? $obj->{"memoryquota"} : $reguser->{'memoryquota'};
        $storagequota = (defined $obj->{"storagequota"}) ? $obj->{"storagequota"} : $reguser->{'storagequota'};
        $nodestoragequota = (defined $obj->{"nodestoragequota"}) ? $obj->{"nodestoragequota"} : $reguser->{'nodestoragequota'};
        $vcpuquota = (defined $obj->{"vcpuquota"}) ? $obj->{"vcpuquota"} : $reguser->{'vcpuquota'};
        $externalipquota = (defined $obj->{"externalipquota"}) ? $obj->{"externalipquota"} : $reguser->{'externalipquota'};
        $rxquota = (defined $obj->{"rxquota"}) ? $obj->{"rxquota"} : $reguser->{'rxquota'};
        $txquota = (defined $obj->{"txquota"}) ? $obj->{"txquota"} : $reguser->{'txquota'};
        $tasks = $obj->{"tasks"} || $reguser->{'tasks'};
        $ubillto = $obj->{"billto"} || $reguser->{'billto'};
        $uaccounts = $obj->{"accounts"} || $reguser->{'accounts'};
        $uaccountsprivileges = $obj->{"accountsprivileges"} || $reguser->{'accountsprivileges'};
        my @ua = split(/,? /, $uaccounts);
        my @up = split(/,? /, $uaccountsprivileges);
        my @ua2 = ();
        my @up2 = ();
        my $i = 0;
        foreach my $u (@ua) {
            if ($register{$u} && ($u ne $username)) {
                push @ua2, $u;
                my $uprivs = $up[$i] || 'u';
                $uprivs =~ tr/adnrpu//cd; # filter out non-valid privileges
                $uprivs =~ s/(.)(?=.*?\1)//g; # filter out duplicates using positive lookahead
                push @up2, $uprivs;
            }
            $i++;
        }
        $uaccounts = join(", ", @ua2);
        $uaccountsprivileges = join(", ", @up2);
    }

    # Sanity checks
    if (
        ($fullname && length $fullname > 255)
            || ($password && length $password > 255)
    ) {
        $postreply .= "Status=ERROR Bad data: $username\n";
        return  $postreply;
    }
    # Only allow new users to be created by admins, i.e. no auto-registration
    if ($reguser->{'username'} || $isadmin) {
        $register{$username} = {
            password           => $password,
            fullname           => $fullname,
            email              => $email,
            opemail            => $opemail,
            alertemail         => $alertemail,
            phone              => $phone,
            opphone            => $opphone,
            opfullname         => $opfullname,
            allowfrom          => $allowfrom,
            privileges         => $uprivileges,
            accounts           => $uaccounts,
            accountsprivileges => $uaccountsprivileges,
            storagepools       => $storagepools,
            memoryquota        => $memoryquota+0,
            storagequota       => $storagequota+0,
            nodestoragequota   => $nodestoragequota+0,
            vcpuquota          => $vcpuquota+0,
            externalipquota    => $externalipquota+0,
            rxquota            => $rxquota+0,
            txquota            => $txquota+0,
            tasks              => $tasks,
            allowinternalapi   => $allowinternalapi || 1, # specify '--' to explicitly disallow
            billto             => $ubillto,
            created           => $created,
            modified           => $current_time,
            action             => ""
        };
        my %uref = %{$register{$username}};
        $uref{result} = "OK";
        $uref{password} = "";
        $uref{status} = ($uprivileges =~ /d/)?'disabled':'enabled';
        $postreply = JSON::to_json(\%uref, { pretty => 1 });
#        $postreply =~ s/""/"--"/g;
        $postreply =~ s/null/""/g;
#        $postreply =~ s/\x/ /g;
    }
    return $postreply;
}

sub do_list {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
List users registered on this engine.
END
    }
    my $userfilter;
    my $usermatch;
    my $propmatch;
    if ($uripath =~ /users(\.cgi)?\/(\?|)(me|this)/) {
        $usermatch = $user;
        $propmatch = $4 if ($uripath =~ /users(\.cgi)?\/(\?|)(me|this)\/(.+)/);
    } elsif ($uripath =~ /users(\.cgi)?\/(\?|)(username)/) {
        $userfilter = $3 if ($uripath =~ /users(\.cgi)?\/\??username(:|=)(.+)/);
        $userfilter = $1 if ($userfilter =~ /(.*)\*/);
    } elsif ($uripath =~ /users(\.cgi)?\/(\S+)/) {
        $usermatch = $2;
        $propmatch = $4 if ($uripath =~ /users(\.cgi)?\/(\S+)\/(.+)/);
    }

    my @regvalues = (sort {$a->{'id'} <=> $b->{'id'}} values %register); # Sort by id
    my @curregvalues;

    foreach my $valref (@regvalues) {
        my $reguser = $valref->{'username'};
        if ($user eq $reguser || $isadmin) {
            next if ($reguser eq 'irigo' || $reguser eq 'guest');
            my %val = %{$valref}; # Deference and assign to new ass array, effectively cloning object
                $val{'password'} = '';
                $val{'status'} = ($val{'privileges'} =~ /d/)?'disabled':'enabled';
                push @curregvalues,\%val if ((!$userfilter && !$usermatch) || $reguser =~ /$userfilter/ || $reguser eq $usermatch);
        }
    }
    if ($action eq 'tablelist') {
        my $t2 = Text::SimpleTable->new(14,32,24,10);

        $t2->row('username', 'fullname', 'lastlogin', 'privileges');
        $t2->hr;
        my $pattern = $options{m};
        foreach $rowref (@curregvalues){
            if ($pattern) {
                my $rowtext = $rowref->{'username'} . " " . $rowref->{'fullname'} . " " . $rowref->{'lastlogin'}
                               . " " .  $rowref->{'privileges'};
                $rowtext .= " " . $rowref->{'mac'} if ($isadmin);
                next unless ($rowtext =~ /$pattern/i);
            }
            $t2->row($rowref->{'username'}, $rowref->{'fullname'}||'--', localtime($rowref->{'lastlogin'})||'--',
            $rowref->{'privileges'}||'--');
        }
        #$t2->row('common', '--', '--', '--');
        #$t2->row('all', '--', '--', '--') if (index($privileges,"a")!=-1);
        $postreply .= $t2->draw;
    } elsif ($console) {
        $postreply = Dumper(\@curregvalues);
    } else {
        my $json_text;
        if ($propmatch) {
            $json_text = JSON::to_json($curregvalues[0]->{$propmatch}, {allow_nonref=>1});
        } else {
            $json_text = JSON::to_json(\@curregvalues, {pretty=>1});
        }
        $json_text =~ s/"--"/""/g;
        $json_text =~ s/null/""/g;
#        $json_text =~ s/\x/ /g;
        $postreply = qq|{"identifier": "username", "label": "username", "items": | unless ($usermatch || $action ne 'listusers');
        $postreply .= $json_text;
        $postreply .= "}\n" unless ($usermatch || $action ne 'listusers');
    }
    return $postreply;
}

sub do_uuidlookup {
    if ($help) {
        return <<END
GET:uuid:
Simple action for looking up a username (uuid) or part of a username and returning the complete username.
END
    }
    my $u = $options{u};
    $u = $params{'uuid'} unless ($u || $u eq '0');
    if ($u || $u eq '0') {
        foreach my $uuid (keys %register) {
            if ($uuid =~ /^$u/) {
                return "$uuid\n" if ($uuid eq $user || index($privileges,"a")!=-1);
            }
        }
    }
}

sub do_uuidshow {
    if ($help) {
        return <<END
GET:uuid:
Simple action for showing a single user. Pass username as uuid.
END
    }
    my $u = $options{u};
    $u = $params{'uuid'} unless ($u || $u eq '0');
    if ($u eq $user || index($privileges,"a")!=-1) {
        foreach my $uuid (keys %register) {
            if ($uuid =~ /^$u/) {
                my %hash = %{$register{$uuid}};
                delete $hash{'action'};
                my $dump = to_json(\%hash, {pretty=>1});
                $dump =~ s/undef/"--"/g;
                return $dump;
            }
        }
    }
}

sub Restoreengine {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:restorefile:
Restores this engine's configuration from "restorefile", which must be one of the paths listed in listenginebackups
END
    }
    if (!$isadmin) {
        $postreply = "Status=ERROR You must be an administrator in order to restore this engine";
    } else {
        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
        my $enginetkthash = Digest::SHA::sha512_hex($tktkey);

        my $restoredir = "/etc";
        my $dbname = "steamregister";
        my $restorefile = $obj->{'restorefile'};

        if ($restorefile && !($restorefile =~ /\//)) {
            my $urifile = URI::Escape::uri_escape($restorefile);
            my $uri = "https://www.stabile.io/irigo/engine.cgi";
            my $cmd = qq|/usr/bin/curl -f --cookie -O -L -F action=getbackup -F restorefile=$urifile -F engineid=$engineid -F enginetkthash=$enginetkthash "$uri" > "/tmp/$restorefile"|;
            my $res = `$cmd`;
            if (-s "/tmp/$restorefile") {
                $res .= `(mkdir $restoredir/stabile; cd $restoredir/stabile; /bin/tar -zxf "/tmp/$restorefile")`;
                $res .= `/usr/bin/mysql -e "create database $dbname;"`;
                $res .= `/usr/bin/mysql $dbname < $restoredir/stabile/steamregister.sql`;
                $res .= `cp -b $restoredir/stabile/hosts.allow /etc/hosts.allow`;
                $res .= `cp -b $restoredir/stabile/auth_tkt_cgi.conf /etc/apache2/conf.d/`;
                $res .= `cp -b $restoredir/stabile/*.crt /etc/apache2/ssl/`;
                $res .= `cp -b $restoredir/stabile/*.key /etc/apache2/ssl/`;
                $res .= `cp -b $restoredir/stabile/mon.cf /etc/mon/`;
                $res .= `service apache2 reload`;

                # Restore default node configuration
                unless ( tie(%idreg,'Tie::DBI', Hash::Merge::merge({table=>'nodeidentities', key=>'identity'}, $Stabile::dbopts)) ) {return "Unable to access identity register"};
                my $defaultpath = $idreg{'default'}->{'path'} . "/casper/filesystem.dir/etc/stabile/nodeconfig.cfg";
                untie %idreg;
                $res .=  `cp $restoredir/stabile/nodeconfig.cfg $defaultpath`;
                $main::syslogit->($user, "info", "Engine configuration $restorefile restored from the registry");
                $postreply .= "Status=OK Engine configuration $restorefile restored from the registry - reloading UI\n";
            } else {
                $postreply .= "Status=ERROR Restore failed, $restorefile not found...\n";
            }
        } else {
            $postreply .= "Status=ERROR You must select a restore file\n";
        }
    }
    return $postreply;
}

# Print list of available actions on objects
sub do_plainhelp {
    my $res;
    $res .= header('text/plain') unless $console;
    $res .= <<END
new [username="name", password="password"]
* enable: Enables a disabled user
* disable: Disables a user, disallowing login
* remove: Deletes a user, leaving servers, images, networks etc. untouched
* deleteentirely: Deletes a user and all the user's servers, images, networks etc. Warning: This destroys data

END
;
}

sub do_cleanbillingdata {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:year,dryrun,cleanup:
Deletes billing from [year]. Default is current year-2. Set dryrun to do a test run. Set cleanup to remove invalid entries.
END
    }
    return "Status=Error Not allowed\n" unless ($isadmin);

    my $y = $params{'year'} || ($year-2);
    my $dryrun = $params{'dryrun'};
    my $cleanup = $params{'cleanup'};
    my $pattern = qq|like '%-$y-__'|;
    if ($cleanup) {
        $pattern = qq|not like '%-____-__'|;
        $y = '';
    }

    unless ( tie(%bnetworksreg,'Tie::DBI', Hash::Merge::merge({table=>'billing_networks', key=>'useridtime'}, $Stabile::dbopts)) ) {return "Status=Error Unable to access billing register"};
    my @bkeys = (tied %bnetworksreg)->select_where("useridtime $pattern");
    $postreply .= "Status=OK -- this is only a test run ---\n" if ($dryrun);
    $postreply .= "Status=OK Cleaning " . scalar @bkeys . " $y network rows\n";
    foreach my $bkey (@bkeys) {
        $postreply .= "Status=OK removing $bnetworksreg{$bkey}->{useridtime}\n";
        delete($bnetworksreg{$bkey}) unless ($dryrun);
    }
    untie(%bnetworksreg);

    unless ( tie(%bimagesreg,'Tie::DBI', Hash::Merge::merge({table=>'billing_images', key=>'userstoragepooltime'}, $Stabile::dbopts)) ) {return "Status=Error Unable to access billing register"};
    my @bkeys = (tied %bimagesreg)->select_where("userstoragepooltime $pattern");
    $postreply .= "Status=OK Cleaning " . scalar @bkeys . " $y image rows\n";
    foreach my $bkey (@bkeys) {
        $postreply .= "Status=OK removing $bimagesreg{$bkey}->{userstoragepooltime}\n";
        delete($bimagesreg{$bkey}) unless ($dryrun);
    }
    untie(%bimagesreg);

    unless ( tie(%bserversreg,'Tie::DBI', Hash::Merge::merge({table=>'billing_domains', key=>'usernodetime'}, $Stabile::dbopts)) ) {return "Status=Error Unable to access billing register"};
    my @bkeys = (tied %bserversreg)->select_where("usernodetime $pattern");
    $postreply .= "Status=OK Cleaning " . scalar @bkeys . " $y server rows\n";
    foreach my $bkey (@bkeys) {
        $postreply .= "Status=OK removing $bserversreg{$bkey}->{usernodetime}\n";
        delete($bserversreg{$bkey}) unless ($dryrun);
    }
    untie(%bserversreg);

    return $postreply;

}

sub collectBillingData {
    my ( $curuuid, $buser, $bmonth, $byear, $showcost ) = @_;

    my $vcpu=0;
    my $rx = 0;
    my $tx = 0;
    my $vcpuavg = 0;
    my $memory = 0;
    my $memoryavg = 0;
    my $backupsize = 0;
    my $backupsizeavg = 0;
    my $nodevirtualsize = 0;
    my $nodevirtualsizeavg = 0;
    my $virtualsize = 0;
    my $virtualsizeavg = 0;
    my $externalip = 0;
    my $externalipavg = 0;

    my $prevmonth = $bmonth-1;
    my $prevyear = $byear;
    if ($prevmonth == 0) {$prevmonth=12; $prevyear--;};
    $prevmonth = substr("0" . $prevmonth, -2);
    my $prev_rx = 0;
    my $prev_tx = 0;
    # List pricing for a single system/server
    if ($curuuid) {
        unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domains register"};
        unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images',key=>'path'}, $Stabile::dbopts)) ) {return "Unable to access images register"};
        unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {return "Unable to access networks register"};

        my @domains;
        my $isserver = 1 if ($domreg{$curuuid});
        if ($isserver) {
            @domains = $domreg{$curuuid};
        } else {
            @domains = values %domreg;
        }
        foreach my $valref (@domains) {
            if ($valref->{'system'} eq $curuuid || $isserver) {
                $memory += $valref->{'memory'};
                $vcpu += $valref->{'vcpu'};
                my $image = $valref->{'image'};
                my $storagepool;
                if ($imagereg{$image}) {
                    $storagepool = $imagereg{$image}->{'storagepool'};
                    if ($storagepool == -1) {
                        $nodevirtualsize += $imagereg{$image}->{'virtualsize'};
                    } else {
                        $virtualsize += $imagereg{$image}->{'virtualsize'};
                    }
                    $backupsize += $imagereg{$image}->{'backupsize'};
                }
                $image = $valref->{'image2'};
                if ($imagereg{$image}) {
                    $storagepool = $imagereg{$image}->{'storagepool'};
                    if ($storagepool == -1) {
                        $nodevirtualsize += $imagereg{$image}->{'virtualsize'};
                    } else {
                        $virtualsize += $imagereg{$image}->{'virtualsize'};
                    }
                    $backupsize += $imagereg{$image}->{'backupsize'};
                }
                my $networkuuid = $valref->{'networkuuid1'};
                my $networktype = $networkreg{$networkuuid}->{'type'};
                $externalip++ if ($networktype eq 'externalip'|| $networktype eq 'ipmapping');
                $networkuuid = $valref->{'networkuuid2'};
                if ($networkreg{$networkuuid}) {
                    $networktype = $networkreg{$networkuuid}->{'type'};
                    $externalip++ if ($networktype eq 'externalip'|| $networktype eq 'ipmapping');
                }
            }
        }
        untie %domreg;
        untie %imagereg;
        untie %networkreg;

    # List pricing for all servers
    } else {
        # Network billing
        unless ( tie(%bnetworksreg,'Tie::DBI', Hash::Merge::merge({table=>'billing_networks', key=>'useridtime'}, $Stabile::dbopts)) ) {return "Unable to access billing register"};
        unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {return "Unable to access networks register"};

        # Build list of the user's network id's
        my %usernetworks;
        my @nkeys = (tied %networkreg)->select_where("user = '$buser'");
        foreach $network (@nkeys) {
            my $id = $networkreg{$network}->{'id'};
            $usernetworks{$id} = $id unless ($usernetworks{$id} || $id==0 || $id==1);
        }
        untie %networkreg;

        foreach $id (keys %usernetworks) {
            my $networkobj = $bnetworksreg{"$buser-$id-$byear-$bmonth"};
            my $prevnetworkobj = $bnetworksreg{"$buser-$id-$prevyear-$prevmonth"};
            $externalip += $networkobj->{'externalip'};
            $externalipavg += $networkobj->{'externalipavg'};
            $rx += $networkobj->{'rx'};
            $tx += $networkobj->{'tx'};
            $prev_rx += $prevnetworkobj->{'rx'};
            $prev_tx += $prevnetworkobj->{'tx'};
        }
        untie %bnetworksreg;

    # Image billing

        unless ( tie(%bimagesreg,'Tie::DBI', Hash::Merge::merge({table=>'billing_images', key=>'userstoragepooltime'}, $Stabile::dbopts)) ) {return "Unable to access billing register"};

        # Build list of the users storage pools
        my $storagepools = $Stabile::config->get('STORAGE_POOLS_DEFAULTS') || "0";
        my $upools = $register{$buser}->{'storagepools'}; # Prioritized list of users storage pools as numbers, e.g. "0,2,1"
        $storagepools = $upools if ($upools && $upools ne '--');
        my @spl = split(/,\s*/, $storagepools);
        my $bimageobj = $bimagesreg{"$buser--1-$byear-$bmonth"};
        $backupsize = $bimageobj->{'backupsize'}+0;
        $nodevirtualsize = $bimageobj->{'virtualsize'}+0;
        $backupsizeavg = $bimageobj->{'backupsizeavg'}+0;
        $nodevirtualsizeavg = $bimageobj->{'virtualsizeavg'}+0;
        foreach $pool (@spl) {
            $bimageobj = $bimagesreg{"$buser-$pool-$byear-$bmonth"};
            $virtualsize += $bimageobj->{'virtualsize'};
            $backupsize += $bimageobj->{'backupsize'};
            $virtualsizeavg += $bimageobj->{'virtualsizeavg'};
            $backupsizeavg += $bimageobj->{'backupsizeavg'};
        }
        untie %bimagesreg;

    # Server billing

        unless ( tie(%bserversreg,'Tie::DBI', Hash::Merge::merge({table=>'billing_domains', key=>'usernodetime'}, $Stabile::dbopts)) ) {return "Unable to access billing register"};
        unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac'}, $Stabile::dbopts)) ) {return "Unable to access billing register"};

        my @usernodes = keys %nodereg;
        untie %nodereg;

        my @nodebills;
        foreach $mac (@usernodes) {
            my $bserverobj = $bserversreg{"$buser-$mac-$byear-$bmonth"};
            $vcpu += $bserverobj->{'vcpu'};
            $memory += $bserverobj->{'memory'};
            $vcpuavg += $bserverobj->{'vcpuavg'};
            $memoryavg += $bserverobj->{'memoryavg'};
        }
        untie %bserversreg;
    }

    my $uservcpuprice = 0+ $register{$user}->{'vcpuprice'};
    my $usermemoryprice = 0+ $register{$user}->{'memoryprice'};
    my $userstorageprice = 0+ $register{$user}->{'storageprice'};
    my $usernodestorageprice = 0+ $register{$user}->{'nodestorageprice'};
    my $userexternalipprice = 0+ $register{$user}->{'externalipprice'};

    $vcpuprice = $uservcpuprice || $Stabile::config->get('VCPU_PRICE') + 0;
    $memoryprice = $usermemoryprice || $Stabile::config->get('MEMORY_PRICE') + 0;
    $storageprice = $userstorageprice || $Stabile::config->get('STORAGE_PRICE') + 0;
    $nodestorageprice = $usernodestorageprice || $Stabile::config->get('NODESTORAGE_PRICE') + 0;
    $externalipprice = $userexternalipprice || $Stabile::config->get('EXTERNALIP_PRICE') + 0;

    my $memorygb = int(0.5 + 100*$memory/1024)/100;
    my $virtualsizegb = int(0.5 + 100*$virtualsize/1024/1024/1024)/100;
    my $nodevirtualsizegb = int(0.5 + 100*$nodevirtualsize/1024/1024/1024)/100;
    my $backupsizegb = int(0.5 + 100*$backupsize/1024/1024/1024)/100;

    my $totalprice = int(0.5 + 100*($vcpu*$vcpuprice + $memorygb*$memoryprice + $virtualsizegb*$storageprice
     + $nodevirtualsizegb*$nodestorageprice + $backupsizegb*$storageprice + $externalip*$externalipprice)) /100;

    my $memoryavggb = int(0.5 + 100*$memoryavg/1024)/100;
    my $virtualsizeavggb = int(0.5 + 100*$virtualsizeavg/1024/1024/1024)/100;
    my $nodevirtualsizeavggb = int(0.5 + 100*$nodevirtualsizeavg/1024/1024/1024)/100;
    my $backupsizeavggb = int(0.5 + 100*$backupsizeavg/1024/1024/1024)/100;

    my $monfac = 1;
    if ($bmonth == $month) {
        # Find 00:00 of first day of month - http://www.perlmonks.org/?node_id=97120
        my $fstamp = POSIX::mktime(0,0,0,1,$mon,$year-1900,0,0,-1);
        my $lstamp = POSIX::mktime(0,0,0,1,$mon+1,$year-1900,0,0,-1);
        $monfac = ($current_time-$fstamp)/($lstamp-$fstamp);
    }

    my $totalpriceavg = int(0.5 + 100*$monfac * ($vcpuavg*$vcpuprice + $memoryavggb*$memoryprice + $virtualsizeavggb*$storageprice
     + $nodevirtualsizeavggb*$nodestorageprice + $backupsizeavggb*$storageprice + $externalipavg*$externalipprice)) /100;

    $prev_rx = 0 if ($prev_rx>$rx); # Something is fishy
    $prev_tx = 0 if ($prev_tx>$tx);
    my $rxgb = int(0.5 + 100*($rx-$prev_rx)/1024**3)/100;
    my $txgb = int(0.5 + 100*($tx-$prev_tx)/1024**3)/100;

    my %stats;
    $stats{'virtualsize'} = $virtualsizegb;
    $stats{'backupsize'} = $backupsizegb;
    $stats{'externalip'} = $externalip;
    $stats{'memory'} = $memorygb;
    $stats{'month'} = $bmonth;
    $stats{'nodevirtualsize'} = $nodevirtualsizegb;
    $stats{'rx'} = $rxgb;
    $stats{'tx'} = $txgb;
    $stats{'username'} = $buser;
    $stats{'vcpu'} = $vcpu;
    $stats{'year'} = $byear;
    $stats{'totalcost'} = "$cur $totalprice" if ($showcost);
    $stats{'curtotal'} = $totalprice if ($showcost);

    if (!$curuuid) {
        $stats{'virtualsizeavg'} = $virtualsizeavggb;
        $stats{'backupsizeavg'} = $backupsizeavggb;
        $stats{'memoryavg'} = $memoryavggb;
        $stats{'nodevirtualsizeavg'} = $nodevirtualsizeavggb;
        $stats{'vcpuavg'} = int(0.5 + 100*$vcpuavg)/100;
        $stats{'externalipavg'} = int(0.5 + 100*$externalipavg)/100;
        $stats{'totalcostavg'} = "$cur $totalpriceavg" if ($showcost);
    }
    return %stats;
}

sub do_resetpassword {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:username:
Sends an email to a user with a link to reset his password. The user must have a valid email address.
END
    }
    my $username = $obj->{'username'} || $user;
    if ($register{$username} && ($username eq $user || $isadmin)) {
        my $mailaddrs = $register{$username}->{'email'};
        $mailaddrs = $username if (!$mailaddrs && $username =~ /\@/);
        if ($mailaddrs) {
            require (dirname(__FILE__)) . "/../auth/Apache/AuthTkt.pm";
            my $tktname = 'auth_' . substr($engineid, 0, 8);
            my $at = Apache::AuthTkt->new(conf => $ENV{MOD_AUTH_TKT_CONF});
            my $tkt = $at->ticket(uid => $username, digest_type => 'SHA512', tokens => '', debug => 0);
#            my $valid = $at->valid_ticket($tkt);

            my $mailhtml = <<END;
<!DOCTYPE html
	PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
	 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en-US" xml:lang="en-US">
	<head>
		<title>Password reset</title>
		<meta http-equiv="Pragma" content="no-cache" />
		<link rel="stylesheet" type="text/css" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css" />
		<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
	</head>
	<body class="tundra">
		<div>
			<div class="well" style="margin:20px;">
				<h3 style="color: #e74c3c!important; margin-bottom:30px;">You requested a password reset at $enginename</h3>
					To log in and set a new password, please click <a href="$baseurl/auth/autologin?$tktname=$tkt\&back=#chpwd">here</a>.<br>
    				<div>Thanks,<br>your friendly infrastructure services</div>
				</div>
			</div>
		</div>
	</body>
</html>
END
            ;
            my $msg = MIME::Lite->new(
                From     => "$enginename",
                To       => $mailaddrs,
                Type     => 'multipart/alternative',
                Subject  => "Password reset on $enginename",
            );
            # my $att_text = MIME::Lite->new(
            #     Type     => 'text',
            #     Data     => $mailtext,
            #     Encoding => 'quoted-printable',
            # );
            # $att_text->attr('content-type' => 'text/plain; charset=UTF-8');
            # $msg->attach($att_text);
            my $att_html = MIME::Lite->new(
                Type     => 'text',
                Data     => $mailhtml,
                Encoding => 'quoted-printable',
            );
            $att_html->attr('content-type' => 'text/html; charset=UTF-8');
            $msg->attach($att_html);
            my $res = $msg->send;
            $postreply = "Status=OK Password reset email sent to $mailaddrs\n";
        } else {
            $postreply = "Status=Error user does not have a registered email address\n";
        }
    } else {
        $postreply = "Status=Error invalid data submitted\n";
    }
    return $postreply;
}

sub do_changepassword {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:username,password:
Changes the password for a user.
END
    }
    my $username = $obj->{'username'} || $user;
    my $password = $obj->{'password'};
    if ($password && $register{$username} && ($username eq $user || $isadmin)) {
        $MAXLEN = 20;
        var $msg = IsBadPassword($password);
        if ($msg) {
            $postreply = "Status=Error $msg - please choose a stronger password\n";
        } else {
            $password = Digest::SHA::sha512_base64($password);
            $register{$username}->{'password'} = $password;
            $postreply = "Status=OK Password changed for $username\n";
        }
    } else {
        $postreply = "Status=Error invalid data submitted\n";
    }
    return $postreply;
}

sub do_remove {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:username:
Removes a user.
END
    }
    my $username = $obj->{'username'};
    $postreply = remove($username);
    return $postreply;
}

sub remove {
    my $username = shift;
    if (!$isadmin && ($user ne $engineuser)) {
        $postreply .= "Status=ERROR You are not allowed to remove user $username\n";
    } elsif ($register{$username}) {
        delete $register{$username};
        tied(%register)->commit;
        `/bin/rm /tmp/$username~*.tasks`;
        unlink "../cgi/ui_update/$username~ui_update.cgi" if (-e "../cgi/ui_update/$username~ui_update.cgi");
        $main::syslogit->($user, "info", "Deleted user $username from db");
        if ($console) {
            $postreply .= "Status=OK Deleted user $username\n";
        } else {
#            $main::updateUI->({ tab => 'users', type=>'update', user=>$user});
            return "{}";
        }
        return $postreply;
    } else {
        $postreply .= "Status=ERROR No such user: $username\n";
    }
}

# Update engine users with users received from the registry
sub updateEngineUsers {
    my ($json_text) = @_;
    return unless ($isadmin || ($user eq $engineuser));
    my $res;
    my $json = JSON->new;
    $json->utf8([1]);
    my $json_obj = $json->decode($json_text);
    my @ulist = @$json_obj;
    my @efields = qw(password
    	address city company country email fullname phone
        state zip alertemail opemail opfullname opphone
        memoryquota storagequota vcpuquota externalipquota rxquota txquota nodestoragequota
        accounts accountsprivileges privileges modified
    );
    my $ures;
    my $ucount = 0;
    foreach my $u (@ulist) {
        my $username = $u->{'username'};
        if (!$register{$username} && $u->{'password'}) {
            $register{$username} = {
                username => $username,
                password => $u->{'password'},
                allowinternalapi => 1
            };
            $ures .= " *";
        }
        next unless ($register{$username});
        next if ($register{$username}->{'modified'} && $register{$username}->{'modified'} > $u->{'modified'});
        foreach my $efield (@efields) {
            if ($efield eq 'privileges') {
                $u->{$efield} =~ tr/adnrpu//cd; # filter out non-valid privileges
            }
            if (defined $u->{$efield}) {
                $u->{$efield} += 0 if ($efield =~ /(quota|price)$/);
                $register{$username}->{$efield} = $u->{$efield};
            }
            delete $u->{$efield} if (defined $u->{$efield} && $u->{$efield} eq '' && $efield ne 'password')
        }
        $ures .= "$username ($u->{'fullname'}), ";
        $ucount++;
        my $uid = `id -u irigo-$username`; chomp $uid;
        if (!$uid) { # Check user has system account for disk quotas
            $main::syslogit->($user, "info", "Adding system user $username");
            `/usr/sbin/useradd -m "irigo-$username"`;
            `echo "[User]\nSystemAccount=true" > /var/lib/AccountsService/users/irigo-$username`; # Don't show in login screen
        }

    }
    $ures = substr($res, 0, -2) . "\n";
    $res .= "Status=OK Synced $ucount users\n";
    return $res;
}

sub sendEngineUser {
    my ($username) = @_;
    if ($enginelinked) {
    # Send engine user to the registry
        require LWP::Simple;
        my $browser = LWP::UserAgent->new;
        $browser->agent('stabile/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );

        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
        my $tkthash = Digest::SHA::sha512_hex($tktkey);
        my $json = '[' . JSON::to_json(\%{$register{$username}}) . ']';
        $json =~ s/null/""/g;
#        $json = uri_escape_utf8($json);
        $json = URI::Escape::uri_escape($json);
        my $posturl = "https://www.stabile.io/irigo/engine.cgi?action=update";
        my $postreq = ();
        $postreq->{'POSTDATA'} = $json;
        $postreq->{'engineid'} = $engineid;
        $postreq->{'enginetkthash'} = $tkthash;

#        my $req = HTTP::Request->new(POST => $posturl);
#        $req->content_type("application/json; charset='utf8'");
#        $req->content($postreq);

        $content = $browser->post($posturl, $postreq)->content();
#        $content = $browser->post($posturl, 'Content-type' => 'text/plain;charset=utf-8', Content => $postreq)->content();
#        $content = $browser->request($req)->content();
        my $fullname = $register{$username}->{'fullname'};
        $fullname = Encode::decode('utf8', $fullname);
        return "Updated $fullname on $dnsdomain\n";
    }
}
