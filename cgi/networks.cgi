#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license

package Stabile::Networks;

use Error qw(:try);
use Data::Dumper;
use Time::Local;
use Time::HiRes qw( time );
use Data::UUID;
use Net::Netmask;
use Net::Ping;
use File::Basename;
use List::Util qw(shuffle);
use lib dirname (__FILE__);
use Stabile;

($datanic, $extnic) = $main::getNics->();
$extsubnet = $Stabile::config->get('EXTERNAL_SUBNET_SIZE');
$proxynic = $Stabile::config->get('PROXY_NIC') || $extnic;
$proxyip = $Stabile::config->get('PROXY_IP');
$proxygw = $Stabile::config->get('PROXY_GW') || $proxyip;
$proxysubnet = $Stabile::config->get('PROXY_SUBNET_SIZE');
my $engineid = $Stabile::config->get('ENGINEID') || "";
$dodns = $Stabile::config->get('DO_DNS') || "";

my $tenders = $Stabile::config->get('STORAGE_POOLS_ADDRESS_PATHS');
@tenderlist = split(/,\s*/, $tenders);
my $tenderpaths = $Stabile::config->get('STORAGE_POOLS_LOCAL_PATHS') || "/mnt/stabile/images";
@tenderpathslist = split(/,\s*/, $tenderpaths);
my $tendernames = $Stabile::config->get('STORAGE_POOLS_NAMES') || "Standard storage";
@tendernameslist = split(/,\s*/, $tendernames);
$storagepools = $Stabile::config->get('STORAGE_POOLS_DEFAULTS') || "0";

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
    my $uuid = $h{"uuid"};
    my $action = $h{'action'};
    $uuid = $curuuid if ($uuid eq 'this');
    if ($uuid =~ /(\d+\.\d+\.\d+\.\d+)/) { # ip addresses are unique across networks so we allow this
        foreach my $val (values %register) {
            if ($val->{'internalip'} eq $uuid || $val->{'externalip'} eq $uuid) {
                $uuid = $val->{'uuid'};
                last;
            }
        }
    }
    my $dbobj = $register{$uuid} || {};
    my $status = $dbobj->{'status'} || $h{"status"}; # Trust db status if it exists
    if ((!$uuid && $uuid ne '0') && (!$status || $status eq 'new') && ($action eq 'save')) {
        my $ug = new Data::UUID;
        $uuid = $ug->create_str();
        $status = 'new';
    };
    return 0 unless ($uuid && length $uuid == 36);

    $uiuuid = $uuid;
    $uistatus = $dbobj->{'status'};

    my $id = $h{"id"};
    my $dbid = 0+$dbobj->{'id'};
    if ($status eq 'new' || !$dbid) {
        $id = getNextId($id) ;
    } else {
        $id = $dbid;
    }

    if ($id > 4095 || $id < 0 || ($id==0 && $uuid!=0) || ($id==1 && $uuid!=1)) {
        $postreply .= "Status=ERROR Invalid new network id $id\n";
        return;
    }
    my $name = $h{"name"} || $dbobj->{'name'};
    my $internalip = $h{"internalip"} || $dbobj->{'internalip'};
    if (!($internalip =~ /\d+\.\d+\.\d+\.\d+/)) {$internalip = ""};
    my $externalip = $h{"externalip"} || $dbobj->{'externalip'};
    my $ports = $h{"ports"} || $dbobj->{'ports'};
    my $type = $h{"type"} || $dbobj->{'type'};
    my $systems = $h{"systems"} || $dbobj->{'systems'};
    my $force = $h{"force"};
    my $reguser = $dbobj->{'user'};
    # Sanity checks
    if (
        ($name && length $name > 255)
        || ($ports && length $ports > 255)
        || ($type && !($type =~ /gateway|ipmapping|internalip|externalip/))
    ) {
         $postreply .= "Stroke=ERROR Bad network data: $name\n";
         return;
     }
     # Security check
     if (($user ne $reguser && index($privileges,"a")==-1 && $action ne 'save' ) ||
         ($reguser && $status eq "new"))
     {
         $postreply .= "Stroke=ERROR Bad user: $user, $action\n";
         return;
     }

    if (!$type ||($type ne 'gateway' && $type ne 'internalip' && $type ne 'ipmapping' && $type ne 'externalip')) {
         $type = "gateway";
         if ($internalip && $internalip ne "--" && $externalip && $externalip ne "--") {$type = "ipmapping";}
         elsif (($internalip && $internalip ne "--") || $status eq 'new') {$type = "internalip";}
         elsif (($externalip && $externalip ne "--") || $status eq 'new') {$type = "externalip";}
    }

    my $obj = {
        uuid => $uuid,
        id => $id,
        name => $name,
        status => $status,
        type => $type,
        internalip => $internalip,
        externalip => $externalip,
        ports => $ports,
        systems => $systems,
        force => $force,
        action => $h{"action"}
    };
    return $obj;
}

sub Init {

    # Tie database tables to hashes
    unless ( tie(%register,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {return "Unable to access network register"};
    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};

    # simplify globals initialized in Stabile.pm
    $tktuser = $tktuser || $Stabile::tktuser;
    $user = $user || $Stabile::user;

    # Create aliases of functions
    *header = \&CGI::header;

    *Natall = \&Deactivateall;
    *Stopall = \&Deactivateall;
    *Restoreall = \&Activateall;

    *do_save = \&Save;
    *do_tablelist = \&do_list;
    *do_jsonlist = \&do_list;
    *do_listnetworks = \&do_list;
    *do_this = \&do_list;
    *do_help = \&action;
    *do_remove = \&action;

    *do_restoreall = \&privileged_action;
    *do_activateall = \&privileged_action;
    *do_deactivateall = \&privileged_action;
    *do_natall = \&privileged_action;
    *do_stopall = \&privileged_action;
    *do_stop = \&privileged_action;
    *do_activate = \&privileged_action;
    *do_deactivate = \&privileged_action;

    *do_gear_activate = \&do_gear_action;
    *do_gear_deactivate = \&do_gear_action;
    *do_gear_stop = \&do_gear_action;
    *do_gear_activateall = \&do_gear_action;
    *do_gear_restoreall = \&do_gear_action;
    *do_gear_deactivateall = \&do_gear_action;
    *do_gear_stopall = \&do_gear_action;
    *do_gear_natall = \&do_gear_action;

    $rx; # Global rx count in bytes
    $tx; # Global tx count in bytes
    $etcpath = "/etc/stabile/networks";

}

sub do_list {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
List networks current user has access to.
END
    }

    my $res;
    my $filter;
    my $statusfilter;
    my $uuidfilter;
    $uuid = $obj->{'uuid'} if ($obj->{'uuid'});

    if ($curuuid && ($isadmin || $register{$curuuid}->{'user'} eq $user) && $uripath =~ /networks(\.cgi)?\/(\?|)(this)/) {
        $uuidfilter = $curuuid;
    } elsif ($uripath =~ /networks(\.cgi)?\/(\?|)(name|status)/) {
        $filter = $3 if ($uripath =~ /networks(\.cgi)?\/.*name(:|=)(.+)/);
        $statusfilter = $3 if ($uripath =~ /networks(\.cgi)?\/.*status(:|=)(\w+)/);
    } elsif ($uripath =~ /networks(\.cgi)?\/(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})/) {
        $uuidfilter = $2;
    } elsif ($uuid) {
        $uuidfilter = $uuid;
    }
    $uuidfilter = $options{u} unless $uuidfilter;
    $filter = $1 if ($filter =~ /(.*)\*/);
    $statusfilter = '' if ($statusfilter eq '*');

    my $curnetwork = URI::Escape::uri_unescape($params{'network'});
    my $curnetwork1 = URI::Escape::uri_unescape($params{'network1'});

    my $sysuuid;
    if ($params{'system'}) {
        $sysuuid = $params{'system'};
        $sysuuid = $cursysuuid || $curdomuuid if ($params{'system'} eq 'this');
    }

    $res .= header('application/json') unless ($console || $action eq 'tablelist');
    my @curregvalues;

    updateBilling();
    my @regkeys;
    if ($fulllist) {
        @regkeys = keys %register;
    } elsif ($uuidfilter && $isadmin) {
        @regkeys = (tied %register)->select_where("uuid = '$uuidfilter'");
    } else {
        @regkeys = (tied %register)->select_where("user = '$user' OR user = 'common'");
    }

    foreach my $k (@regkeys) {
        my $valref = $register{$k};
        my $uuid = $valref->{'uuid'};
        my $dbuser = $valref->{'user'};
        my $type = $valref->{'type'};
        my $id = $valref->{'id'};
    # Only list networks belonging to current user
        if ($dbuser eq "common" || $user eq $dbuser || $fulllist || ($uuidfilter && $isadmin)) {
            my $dom = $domreg{$valref->{'domains'}};
            next unless (!$sysuuid || $dom->{'system'} eq $sysuuid || $valref->{'domains'} eq $sysuuid);
            validateStatus($valref);

            my %val = %{$valref}; # Deference and assign to new ass array, effectively cloning object
            $val{'id'} += 0;
            $val{'rx'} = $rx;
            $val{'tx'} = $tx;
            if ($filter || $statusfilter || $uuidfilter) { # List filtered networks
                my $fmatch;
                my $smatch;
                my $umatch;
                $fmatch = 1 if (!$filter || $val{'name'}=~/$filter/i);
                $smatch = 1 if (!$statusfilter || $statusfilter eq 'all'
                        || $statusfilter eq $val{'status'}
                        );
                $umatch = 1 if ($val{'uuid'} eq $uuidfilter);
                if ($fmatch && $smatch && !$uuidfilter) {
                    push @curregvalues,\%val;
                } elsif ($umatch) {
                    push @curregvalues,\%val;
                    last;
                }

            } elsif ($action eq "listnetworks") { # List available networks
                if (($id>0 || index($privileges,"a")!=-1) && ((!$valref->{'domains'} && !$valref->{'systems'}) || $type eq 'gateway' || ($curnetwork eq $uuid && !$curnetwork1) || $curnetwork1 eq $uuid)) {
                    push @curregvalues,\%val;
                }
            } else {
                push @curregvalues,\%val if ($id>0 || index($privileges,"a")!=-1);
            }
        }
    }

    # Sort @curregvalues
    my $sort = 'status';
    $sort = $2 if ($uripath =~ /sort\((\+|\-)(\S+)\)/);
    my $reverse;
    $reverse = 1 if ($1 eq '-');
    if ($reverse) { # sort reverse
        if ($sort =~ /id/) {
            @curregvalues = (sort {$b->{$sort} <=> $a->{$sort}} @curregvalues); # Sort as number
        } else {
            @curregvalues = (sort {$b->{$sort} cmp $a->{$sort}} @curregvalues); # Sort as string
        }
    } else {
        if ($sort =~ /id/) {
            @curregvalues = (sort {$a->{$sort} <=> $b->{$sort}} @curregvalues); # Sort as number
        } else {
            @curregvalues = (sort {$a->{$sort} cmp $b->{$sort}} @curregvalues); # Sort as string
        }
    }

    my %val = ("uuid", "--", "name", "--");
    if ($curnetwork1) {
        push @curregvalues, \%val;
    }
    if ($action eq 'tablelist') {
        $res .= header("text/plain") unless ($console);
        my $t2 = Text::SimpleTable->new(36,20,10,5,10,14,14,7);
        $t2->row('uuid', 'name', 'type', 'id', 'internalip', 'externalip', 'user', 'status');
        $t2->hr;
        my $pattern = $options{m};
        foreach $rowref (@curregvalues){
            if ($pattern) {
                my $rowtext = $rowref->{'uuid'} . " " . $rowref->{'name'} . " " . $rowref->{'type'} . " " . $rowref->{'id'}
                   . " " .  $rowref->{'internalip'} . " " . $rowref->{'externalip'} . " " . $rowref->{'user'} . " " . $rowref->{'status'};
                $rowtext .= " " . $rowref->{'mac'} if ($isadmin);
                next unless ($rowtext =~ /$pattern/i);
            }
            $t2->row($rowref->{'uuid'}, $rowref->{'name'}||'--', $rowref->{'type'}, $rowref->{'id'},
            $rowref->{'internalip'}||'--', $rowref->{'externalip'}||'--', $rowref->{'user'}, $rowref->{'status'});
        }
        $res .= $t2->draw;
    } elsif ($console && !$uuidfilter && $action ne 'jsonlist') {
        $res .= Dumper(\@curregvalues);
    } else {
        my $json_text;
        if ($uuidfilter) {
            $json_text = to_json($curregvalues[0], {pretty => 1}) if (@curregvalues);
        } else {
            $json_text = to_json(\@curregvalues, {pretty => 1}) if (@curregvalues);
        }
        $json_text = "[]" unless $json_text;
        $json_text =~ s/""/"--"/g;
        $json_text =~ s/null/"--"/g;
        $json_text =~ s/undef/"--"/g;
        $json_text =~ s/\x/ /g;
        $res .= qq|{"action": "$action", "identifier": "uuid", "label": "name", "items": | if ($action && $action ne 'jsonlist' && $action ne 'list' && !$uuidfilter);
        $res .= $json_text;
        $res .= qq|}| if ($action && $action ne 'jsonlist' && $action ne 'list'  && !$uuidfilter);
#        $res .= "JSON" if (action eq 'jsonlist');
    }
    return $res;
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
        foreach my $uuid (keys %register) {
            if (($register{$uuid}->{'user'} eq $user || $register{$uuid}->{'user'} eq 'common' || $fulllist)
                && ($uuid =~ /^$u/ || $register{$uuid}->{'name'} =~ /^$u/)) {
                $ruuid = $uuid;
                last;
            }
        }
        if (!$ruuid && $isadmin) { # If no match and user is admin, do comprehensive lookup
            foreach $uuid (keys %register) {
                if ($uuid =~ /^$u/ || $register{$uuid}->{'name'} =~ /^$u/) {
                    $ruuid = $uuid;
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
Simple action for showing a single network.
END
    }

    my $res;
    $res .= header('application/json') unless $console;
    my $u = $options{u};
    $u = $curuuid unless ($u || $u eq '0');
    if ($u || $u eq '0') {
        foreach my $uuid (keys %register) {
            if (($register{$uuid}->{'user'} eq $user || $register{$uuid}->{'user'} eq 'common' || index($privileges,"a")!=-1)
                && $uuid =~ /^$u/) {
                my %hash = %{$register{$uuid}};
                delete $hash{'action'};
                delete $hash{'nextid'};
#                my $dump = Dumper(\%hash);
                my $dump = to_json(\%hash, {pretty=>1});
                $dump =~ s/undef/"--"/g;
                $res .= $dump;
                last;
            }
        }
    }
    return $res;
}

sub do_updateui {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:uuid:
Update the web UI for the given uuid (if user has web UI loaded).
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    if ($register{$uuid}) {
        my $uistatus = $register{$uuid}->{'status'};
        $main::updateUI->({tab=>"networks", user=>$user, uuid=>$uuid, status=>$uistatus});
        $res .= "Status=OK Updated UI for $register{$uuid}->{'type'} $register{$uuid}->{'name'}: $uistatus";
    } else {
        $main::updateUI->({tab=>"networks", user=>$user});
        $res .= "Status=OK Updated networks UI for $user";
    }
    return $res;

}

sub do_dnscreate {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:name, value, type:
Create a DNS record in the the subdomain belonging to the the registering engine.
<b>name</b> is a domain name in the Engine's zone. <b>value</b> is either an IP address for A records or a domain name for other. <b>[type]</b> is A, CNAME or MX.
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    $res .= "Status=" . $main::dnsCreate->($engineid, $params{'name'}, $params{'value'}, $params{'type'}, $user);
    return $res;
}

sub do_dnsupdate {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:name:
Updates CNAME records pointing to a A record, to point to the given 'name' in the the subdomain belonging to the the registering engine.
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    $res .= "Status=" . $main::dnsUpdate->($engineid, $params{'name'}, $user);
    return $res;
}

sub do_dnslist {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET::
Lists entries in $dnsdomain zone.
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    $res .= $main::dnsList->($engineid, $user);
    return $res;
}

sub do_dnsclean {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET::
Remove this engines entries in $dnsdomain zone.
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    $res .= $main::dnsClean->($engineid, $user);
    return $res;
}

sub do_dnscheck {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:name:
Checks if a domain name (name[.subdomain]) is available, i.e. not registered,
where subdomain is the subdomain belonging to the the registering engine.
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    my $name = $params{'name'};
    $name = $1 if ($name =~ /(.+)\.$dnsdomain$/);
    if (!$enginelinked) {
        $res .= "Status=ERROR You cannot create DNS records - your engine is not linked.\n";
    } elsif ($name =~ /^\S+$/ && !(`host $name.$dnsdomain authns1.cabocomm.dk` =~ /has address/)
        && $name ne 'www'
        && $name ne 'mail'
        && $name ne 'info'
        && $name ne 'admin'
        && $name ne 'work'
        && $name ne 'io'
        && $name ne 'cloud'
        && $name ne 'compute'
        && $name ne 'sso'
        && $name !~ /valve/
    ) {
        $res .= "Status=OK $name.$dnsdomain is available\n";
    } else {
        $res .= "Status=ERROR $name.$dnsdomain is not available\n";
    }
    return $res;
}

sub do_dnsdelete {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:name:
Delete a DNS record in the configured zone.
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    $res .= $main::dnsDelete->($engineid, $params{'name'}, $user);
    return $res;
}

sub do_getappstoreurl {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET::
Get URL to the app store belonging to engine.
END
    }

    my $res;
    # $res .= header('application/json') unless $console;
    # $res .= qq|{"url": "$appstoreurl"}\n|;
    $res .= "$appstoreurl\n";
    return $res;
}

sub do_getdnsdomain {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET::
Get the domain and the subdomain this Engine registers entries in.
END
    }
    my $domain = ($enginelinked)?$dnsdomain:'';
    my $subdomain = ($enginelinked)?substr($engineid, 0, 8):'';
    my $linked = ($enginelinked)?'true':'false';
    my $res;
    $res .= header('application/json') unless $console;
    $res .= qq|{"domain": "$domain", "subdomain": "$subdomain", "enginelinked": "$linked"}|;
    return $res;
}

sub xmppsend {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:to, msg:
Send out an xmpp alert.
END
    }
    if ($help) {
        return <<END
Send out an xmpp alert
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    $res .= $main::xmppSend->($params{'to'}, $params{'msg'}, $engineid);
    return $res;
}

# List available network types. Possibly limited by exhausted IP ranges.
sub do_listnetworktypes {
    if ($help) {
        return <<END
GET::
List available network types. Possibly limited by exhausted IP ranges.
END
    }

    my $res;
    $res .= header('application/json') unless $console;
    # Check if we have exhausted our IP ranges
    my $intipavail = getNextInternalIP();
    my $extipavail = getNextExternalIP();
    my $arpipavail = getNextExternalIP('','',1);
    my $json_text;
    $json_text .= '{"type": "gateway", "name": "Gateway"}, ';
    $json_text .= '{"type": "internalip", "name": "Internal IP"}, ' if ($intipavail);
    unless (overQuotas()) {
        $json_text .= '{"type": "ipmapping", "name": "IP mapping"}, ' if ($intipavail && $extipavail);
        $json_text .= '{"type": "externalip", "name": "External IP"}, 'if ($arpipavail);
    }
    $json_text = substr($json_text,0,-2);
    $res .= '{"identifier": "type", "label": "name", "items": [' . $json_text  . ']}';
    return $res;
}

# Simple action for removing all networks belonging to a user
sub do_removeusernetworks {
    my ($uuid, $action) = @_;

    if ($help) {
        return <<END
GET::
Remove all networks belonging to a user.
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    if ($readonly) {
        $postreply .= "Status=ERROR Not allowed\n";
    } else {
        Removeusernetworks($user);
    }
    $res .= $postreply || "Status=OK Nothing to remove\n";
    return $res;
}

# Activate all networks. If restoreall (e.g. after reboot) is called, we only activate networks which have entries in /etc/stabile/network
sub Activateall {
    my ($nouuid, $action) = @_;
    if ($help) {
        return <<END
GET::
Tries to activate all networks. If called as restoreall by an admin, will try to restore all user's networks to saved state, e.g. after a reboot.
END
    }
    my @regkeys;
    if (($action eq "restoreall" || $fulllist) && index($privileges,"a")!=-1) { # Only an administrator is allowed to do this
        @regkeys = keys %register;
    } else {
        @regkeys = (tied %register)->select_where("user='$user'");
    }
    my $i = 0;
    if (!$isreadonly) {
    	foreach my $key (@regkeys) {
            my $valref = $register{$key};
    		my $uuid = $valref->{'uuid'};
    		my $type = $valref->{'type'};
    		my $id = $valref->{'id'};
    		my $name = $valref->{'name'};
    		my $internalip = $valref->{'internalip'};
    		my $externalip = $valref->{'externalip'};
    		if ($id!=0 && $id!=1 && $id<4095) {
                my $caction = "nat";
    			if (-e "$etcpath/dhcp-hosts-$id") {
    				if ($action eq "restoreall" && $isadmin) { # If restoring, only activate previously active networks
                        my $hosts;
                        $hosts = lc `/bin/cat $etcpath/dhcp-hosts-$id` if (-e "$etcpath/dhcp-hosts-$id");
                        $caction = "activate" if ($hosts =~ /($internalip|$externalip)/);
    			    } elsif ($action eq "activateall") {
    				    $caction = "activate";
        			}
                    # TODO: investigate why this is necessary - if we don't do it, networks are not activated
                    $user = $valref->{'user'};
                    do_list($uuid, 'list');

                    my $res = Activate($uuid, $caction);
                    if ($res =~ /\w+=(\w+) / ) {
                        $register{$uuid}->{'status'} = $1 unless (uc $1 eq 'ERROR');
                        $i ++ unless (uc $1 eq 'ERROR');
                    } else {
                        $postreply .= "Status=ERROR Cannot $caction $type $name $uuid: $res\n";
                    }
    		    }
            } else {
                $postreply .= "Status=ERROR Cannot $action $type $name\n" unless ($id==0 || $id==1);
        	}
        }
    } else {
        $postreply .= "Status=ERROR Problem activating all networks\n";
    }
    if ($postreply =~/Status=ERROR /) {
        $postreply = header('text/plain', '500 Internal Server Error') . $postreply unless $console;
    }
    $postreply .= "Status=OK activated $i networks\n";
    $main::updateUI->({tab=>"networks", user=>$user});
    updateBilling("$action $user");
    return $postreply;
}

# Deactivate all networks
sub Deactivateall {
    my ($nouuid, $action) = @_;
    if ($help) {
        return <<END
GET::
Tries to deactivate all networks. May also be called as natall or stopall.
END
    }

    my @regkeys;
    if ($fulllist && index($privileges,"a")!=-1) { # Only an administrator is allowed to do this
        @regkeys = keys %register;
    } else {
        @regkeys = (tied %register)->select_where("user='$user'");
    }
    if (!$isreadonly) {
		my %ids;
		foreach my $key (@regkeys) {
            my $valref = $register{$key};
			my $uuid = $valref->{'uuid'};
			my $type = $valref->{'type'};
			my $id = $valref->{'id'};
			my $name = $valref->{'name'};
			if ($id!=0 && $id!=1 && $id<4095) {
				if (-e "$etcpath/dhcp-hosts-$id") {
					my $caction = "deactivate";
					my $result;
					if ($action eq "stopall") {
						$caction = "stop";
						# Stop also deactivates all networks with same id, so only do this once for each id
						if ($ids{$id}) {
							$result = $valref->{'status'};
						} else {
							$result = Stop($id, $caction);
						}
						$ids{$id} = 1;
					} else {
                        my $res = Deactivate($uuid, $caction);
                        if ($res =~ /\w+=(\w+) /) {
                            $register{$uuid}->{'status'} = $1;
                        } else {
                            $postreply .= "Status=ERROR Cannot $caction $type $name $uuid: $res\n";
                        }
					}
					if ($result =~ /\w+=(.\w+) /) {
                        $register{$uuid}->{'status'} = $uistatus = $1;
						$uiuuid = $uuid;
						$postreply .= "Status=OK $caction $type $name $uuid\n";
						$main::syslogit->($user, "info", "$caction network $uuid ($id) ");
					}
				}
			} else {
				$postreply .= "Status=ERROR Cannot $action $type $name\n" unless ($id==0 || $id==1);
			}
		}
	} else {
		$postreply .= "Status=ERROR Problem deactivating all networks\n";
	}
    if ($postreply =~/Status=ERROR /) {
        $res = header('text/plain', '500 Internal Server Error') unless $console;
    } else {
        $res = header('text/plain') unless $console;
    }
	$main::updateUI->({tab=>"networks", user=>$user});
	updateBilling("$action $user");
	return $postreply;
}

sub do_updatebilling {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:uuid:
Update network billing for current user.
END
    }

    my $res;
    $res .= header('text/plain') unless $console;
    if ($isreadonly) {
        $res .= "Status=ERROR Not updating network billing for $user\n";
    } else {
        updateBilling("updatebilling $user");
        $res .= "Status=OK Updated network billing for $user\n";
    }
    return $res;
}

# Print list of available actions on objects
sub do_plainhelp {
    my $res;
    $res .= header('text/plain') unless $console;
    $res .= <<END
* new [type="ipmapping|internalip|externalip|gateway", name="name"]: Creates a new network
* activate: Activates a network. If gateway is down it is brought up.
* stop: Stops the gateway, effectively stopping network communcation with the outside.
* deactivate: Deactivates a network. Removes the associated internal IP address from the DHCP service.
* delete: Deletes a network. Use with care. Network can not be in use.

END
;
}

sub addDHCPAddress {
    my $id = shift;
    my $uuid = shift;
    my $dhcpip = shift;
    my $gateway = shift;
    my $mac = lc shift;
    my $isexternal = !($dhcpip =~ /^10\./);
    my $options;
    my $interface = "br$id"; #,$extnic.$id
    $options = "--strict-order --bind-interfaces --except-interface=lo --interface=$interface " .
    ($proxyip?"--dhcp-range=tag:external,$proxyip,static ":"") .
    "--pid-file=/var/run/stabile-$id.pid --dhcp-hostsfile=$etcpath/dhcp-hosts-$id --dhcp-range=tag:internal,$gateway,static " .
    "--dhcp-optsfile=$etcpath/dhcp-options-$id --port=0 --log-dhcp";

    my $running;
    my $error;
    my $psid;
    return "Status=ERROR Empty mac or ip when configuing dhcp for $name" unless ($mac && $dhcpip);

    eval {
        $psid = `/bin/cat /var/run/stabile-$id.pid` if (-e "/var/run/stabile-$id.pid");
        chomp $psid;
        $running = -e "/proc/$psid" if ($psid);
        # `/bin/ps p $psid` =~ /$psid/
        # `/bin/ps ax | /bin/grep stabile-$id.pid | /usr/bin/wc -l`; 1;} or do
        1;
    } or do {$error .= "Status=ERROR Problem configuring dhcp for $name $@\n";};

    if (-e "$etcpath/dhcp-hosts-$id") {
        open(TEMP1, "<$etcpath/dhcp-hosts-$id") || ($error .= "Status=ERROR Problem reading dhcp hosts\n");
        open(TEMP2, ">$etcpath/dhcp-hosts-$id.new") || ($error .= "Status=ERROR Problem writing dhcp hosts $etcpath/dhcp-hosts-$id.new\n");
        while (<TEMP1>) {
            my $line = $_;
            print TEMP2 $line unless (($mac && $line =~ /^$mac/i) || ($line & $line =~ /.+,$dhcpip/));
        }
        print TEMP2 "$mac," . (($isexternal)?"set:external,":"set:internal,") . "$dhcpip\n";
        close(TEMP1);
        close(TEMP2);
        rename("$etcpath/dhcp-hosts-$id", "$etcpath/dhcp-hosts-$id.old") || ($error .= "Status=ERROR Problem writing dhcp hosts\n");
        rename("$etcpath/dhcp-hosts-$id.new", "$etcpath/dhcp-hosts-$id") || ($error .= "Status=ERROR Problem writing dhcp hosts\n");
    } else {
        open(TEMP1, ">$etcpath/dhcp-hosts-$id") || ($error .= "Status=ERROR Problem writing dhcp options\n");
        print TEMP1 "$mac,$dhcpip\n";
        close (TEMP1);
    }

#    unless (-e "$etcpath/dhcp-options-$id") {
        my $block = new Net::Netmask("$proxygw/$proxysubnet");
        my $proxymask = $block->mask();
        open(TEMP1, ">$etcpath/dhcp-options-$id") || ($error .= "Status=ERROR Problem writing dhcp options\n");

        print TEMP1 <<END;
tag:external,option:router,$proxygw
tag:external,option:netmask,$proxymask
tag:external,option:dns-server,$proxyip
tag:internal,option:router,$gateway
tag:internal,option:netmask,255.255.255.0
tag:internal,option:dns-server,$gateway
option:dns-server,1.1.1.1
END

        close (TEMP1);
#    }

    if ($running) {
        $main::syslogit->($user, 'info', "HUPing dnsmasq 1: $id");
        eval {`/usr/bin/pkill -HUP -f "stabile-$id.pid"`; 1;} or do {$error .= "Status=ERROR Problem configuring dhcp for $name $@\n";};
    } else {
        eval {`/usr/sbin/dnsmasq $options`;1;} or do {$error .= "Status=ERROR Problem configuring dhcp for $name $@\n";};
    }

    return $error?$error:"OK";
}

sub removeDHCPAddress {
    my $id = shift;
    my $uuid = shift;
    my $dhcpip = shift;
    my $mac;
    $mac = lc $domreg{$uuid}->{'nicmac1'} if ($domreg{$uuid});
    my $isexternal = ($dhcpip =~ /^10\./);
    my $running;
    my $error;
    my $psid;
    return "Status=ERROR Empty mac or ip when configuring dhcp for $name" unless ($mac || $dhcpip);

    eval {
        $psid = `/bin/cat /var/run/stabile-$id.pid` if (-e "/var/run/stabile-$id.pid");
        chomp $psid;
        $running = -e "/proc/$psid" if ($psid);
        1;
    } or do {$error .= "Status=ERROR Problem deconfiguring dhcp for $name $@\n";};

    my $keepup;
    if (-e "$etcpath/dhcp-hosts-$id") {
        open(TEMP1, "<$etcpath/dhcp-hosts-$id") || ($error .= "Status=ERROR Problem reading dhcp hosts\n");
        open(TEMP2, ">$etcpath/dhcp-hosts-$id.new") || ($error .= "Status=ERROR Problem writing dhcp hosts\n");
        while (<TEMP1>) {
            my $line = $_; chomp $line;
            if ($line && $line =~ /(.+),.+,($dhcpip)/) { # Release and remove this mac/ip from lease file
                $main::syslogit->($user, 'info', "Releasing dhcp lease: $datanic.$id $dhcpip $1");
                `/usr/bin/dhcp_release $datanic.$id $dhcpip $1`;
            } elsif ($mac && $line =~ /^$mac/i) {
                # If we find a stale assigment to the mac we are removing, remove this also
                $main::syslogit->($user, 'info', "Releasing stale dhcp lease: intnic.$id $dhcpip $mac");
                `/usr/bin/dhcp_release $datanic.$id $dhcpip $mac`;
            } else {
                # Keep all other leases, and keep up the daemon if any leases found
                print TEMP2 "$line\n";
                $keepup = 1 if $line;
            }
        }
        close(TEMP1);
        close(TEMP2);
        rename("$etcpath/dhcp-hosts-$id", "$etcpath/dhcp-hosts-$id.old") || ($error .= "Status=ERROR Problem writing dhcp hosts\n");
        rename("$etcpath/dhcp-hosts-$id.new", "$etcpath/dhcp-hosts-$id") || ($error .= "Status=ERROR Problem writing dhcp hosts\n");
    }

    if ($keepup) {
        if ($running) {
            $main::syslogit->($user, 'info', "HUPing dnsmasq 2: $id");
            eval {`/usr/bin/pkill -HUP -f "stabile-$id.pid"`; 1;} or do {$error .= "Status=ERROR Problem configuring dhcp for $name $@\n";};
        }
    } else {
        unlink "$etcpath/dhcp-options-$id" if (-e "$etcpath/dhcp-options-$id");
        if ($running) {
            # Take down dhcp server
            $main::syslogit->($user, 'info', "Killing dnsmasq 3: $id");
            eval {`/usr/bin/pkill -f "stabile-$id.pid"`; 1;} or do {$error .= "Status=ERROR Problem configuring dhcp for $name $@\n";};
        }
    }

    return $error?$error:"OK";
}

# Helper function
sub save {
    my ($id, $uuid, $name, $status, $type, $internalip, $externalip, $ports, $buildsystem, $username) = @_;
    my $obj = {
        id => $id,
        uuid => $uuid,
        name => $name,
        status => $status,
        type => $type,
        internalip => $internalip,
        externalip => $externalip,
        ports => $ports,
        buildsystem => $buildsystem,
        username => $username
    };
    return Save($uuid, 'save', $obj);
}

sub Save {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
POST:uuid, id, name, internalip, externalip, ports, type, systems, activate:
To save a collection of networks you either PUT or POST a JSON array to the main endpoint with objects representing the networks with the changes you want.
Depending on your privileges not all changes are permitted. If you save without specifying a uuid, a new network is created.
For now, [activate] only has effect when creating a new connection with a linked system/server.
END
    }
    $uuid = $obj->{'uuid'} if ($obj->{'uuid'});
    my $id = $obj->{id};
    my $name = $obj->{name};
    my $status = $obj->{status};
    my $type = $obj->{type};
    my $internalip = $obj->{internalip};
    my $externalip = $obj->{externalip};
    my $ports = $obj->{ports};
    my $buildsystem = $obj->{buildsystem};
    my $username = $obj->{username};
    my $systems = $obj->{systems}; # Optionally link this network to a system

    $postreply = "" if ($buildsystem);
	$username = $user unless ($username);

    my $regnet = $register{$uuid};
    $status = $regnet->{'status'} || $status; # Trust db status if it exists
    if ((!$uuid && $uuid ne '0') && $status eq 'new') {
        my $ug = new Data::UUID;
        $uuid = $ug->create_str();
    };
    if ($status eq 'new') {
        $name  = 'New Connection' unless ($name);
    }
    unless ($uuid && length $uuid == 36) {
        $postreply .= "Status=Error Invalid uuid $uuid\n";
        return $postreply;
    }
    my $systemnames = $regnet->{'systemnames'};

    my $dbid = 0+$regnet->{'id'};
    if ($status eq 'new' || !$dbid) {
        $id = getNextId($id) ;
    } else {
        $id = $dbid;
    }
    if ($id > 4095 || $id < 0 || ($id==0 && $uuid!=0 && $isadmin) || ($id==1 && $uuid!=1 && $isadmin)) {
        $postreply .= "Status=ERROR Invalid network id $id\n";
        return $postreply;
    }
    $name = $name || $regnet->{'name'};
    $internalip = $internalip || $regnet->{'internalip'};
    if (!($internalip =~ /\d+\.\d+\.\d+\.\d+/)) {$internalip = ''};
    $externalip = $externalip || $regnet->{'externalip'};
    $ports = $ports || $regnet->{'ports'};
    my $reguser = $regnet->{'user'};
    # Sanity checks
    if (
        ($name && length $name > 255)
        || ($ports && length $ports > 255)
        || ($type && !($type =~ /gateway|ipmapping|internalip|externalip/))
    ) {
        $postreply .= "Stroke=ERROR Bad data: $name, $ports, $type\n";
        return $postreply;
    }
    # Security check
    if (($reguser && $username ne $reguser && !$isadmin ) ||
        ($reguser && $status eq "new"))
    {
        $postreply .= "Status=Error Bad user: $username ($status)\n";
        return $postreply;
    }

    my $hit = 0;
# Check if user is allowed to use network
    my @regvalues = values %register;
    foreach my $val (@regvalues) {
        $dbid = $val->{"id"};
        $dbuser = $val->{"user"};
        if ($dbid == $id && $username ne $dbuser && $dbuser ne "common") {
            $hit = 1;
            last;
        }
    }
    if ($hit && !$isadmin) { # Network is nogo (unless you are an admin)
        $postreply .= "Status=ERROR Network id $id not available\n";
        return $postreply;
    } elsif (!$type) {
        $postreply .= "Status=ERROR Network must have a type\n";
        return $postreply;
    } elsif ($status eq 'down' || $status eq 'new' || $status eq 'nat') {
        # Check if network has been modified or is new
        if ($regnet->{'id'} ne $id ||
            $regnet->{'name'} ne $name ||
            $regnet->{'type'} ne $type ||
            $regnet->{'internalip'} ne $internalip ||
            $regnet->{'externalip'} ne $externalip ||
            $regnet->{'systems'} ne $systems ||
            $regnet->{'ports'} ne $ports)
        {
            if ($type eq "externalip") {
                $internalip = "--";
                $externalip = getNextExternalIP($externalip, $uuid, 1);
                if (!$externalip) {
                    $postreply .= "Status=ERROR Unable to allocate external proxy IP for $name\n";
                    $externalip = "--";
                    $internalip = getNextInternalIP($internalip, $uuid, $id);
                    $type = "internalip";
                } else {
                    $postreply .= "Status=OK Allocated external IP: $externalip\n" unless ($regnet->{'externalip'} eq $externalip);
                    if ($dodns) {
                        $main::dnsCreate->($engineid, $externalip, $externalip, 'A', $user);
                    }
                }

            } elsif ($type eq "ipmapping") {
                $externalip = getNextExternalIP($externalip, $uuid);
                if (!$externalip) {
                    $postreply .= "Status=ERROR Unable to allocate external IP for $name\n";
                    $externalip = "--";
                    $type = "internalip";
                } else {
                    $postreply .= "Status=OK Allocated external IP: $externalip\n" unless ($regnet->{'externalip'} eq $externalip);
                    if ($dodns) {
                        $postreply .= "Status=OK Trying to register DNS " . $main::dnsCreate->($engineid, $externalip, $externalip, 'A', $user);
                    }
                }
                $internalip = getNextInternalIP($internalip, $uuid, $id);
                if (!$internalip) {
                    $postreply .= "Status=ERROR Unable to allocate internal IP for $name\n";
                    $internalip = "--";
                    $type = "gateway";
                } else {
                    $postreply .= "Status=OK Allocated internal IP: $internalip for $name\n" unless ($regnet->{'internalip'} eq $internalip);
                }

            } elsif ($type eq "internalip") {
                $externalip = "--";
                $ports = "--";
                my $ointip = $internalip;
                $internalip = getNextInternalIP($internalip, $uuid, $id);
                if (!$internalip) {
                    $postreply .= "Status=ERROR Unable to allocate internal IP $internalip ($id, $uuid, $ointip) for $name\n";
                    $internalip = "--";
                    $type = "gateway";
                } else {
                    $postreply .= "Status=OK Allocated internal IP: $internalip for $name\n" unless ($regnet->{'internalip'} eq $internalip);
                }

            } elsif ($type eq "gateway") {
            #    $internalip = "--";
            #    $externalip = "--";
            #    $ports = "--";
            } else {
                $postreply .= "Status=ERROR Network must have a valid type\n";
                return $postreply;
            }
            # Validate ports
            my @portslist = split(/, ?| /, $ports);
            if ($ports ne "--") {
                foreach my $port (@portslist) {
                    my $p = $port; # Make a copy of var
                    if ($p =~ /(\d+\.\d+\.\d+\.\d+):(\d+)/) {
                        $p = $2;
                    };
                    $p = 0 unless ($p =~ /\d+/);
                    if ($p<1 || $p>65535) {
                        $postreply .= "Status=ERROR Invalid port mapping for $name\n";
                        $ports = "--";
                        last;
                    }
                }
            }
            if ($ports ne "--") {
                $ports = join(',', @portslist);
            }
            if ($systems ne $regnet->{'systems'}) {
                my $regsystems = $regnet->{'systems'};
                unless (tie(%sysreg,'Tie::DBI', Hash::Merge::merge({table=>'systems'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access systems register"}|; return $res;};

                # Remove existing link to system
                if ($sysreg{$regsystems}) {
                    $sysreg{$regsystems}->{'networkuuids'} =~ s/$uuid,? ?//;
                    $sysreg{$regsystems}->{'networknames'} = s/$regnet->{'name'},? ?//;
                } elsif ($domreg{$regsystems}) {
                    $domreg{$regsystems}->{'networkuuids'} =~ s/$uuid,? ?//;
                    $domreg{$regsystems}->{'networknames'} = s/$regnet->{'name'},? ?//;
                }
                if ($systems) {
                    if ($sysreg{$systems}) { # Add new link to system
                        $sysreg{$systems}->{'networkuuids'} .= (($sysreg{$systems}->{'networkuuids'}) ? ',' : '') . $uuid;
                        $sysreg{$systems}->{'networknames'} .= (($sysreg{$systems}->{'networknames'}) ? ',' : '') . $name;
                        $systemnames = $sysreg{$systems}->{'name'};
                    } elsif ($domreg{$systems}) {
                        $domreg{$systems}->{'networkuuids'} .= (($domreg{$systems}->{'networkuuids'}) ? ',' : '') . $uuid;
                        $domreg{$systems}->{'networknames'} .= (($domreg{$systems}->{'networknames'}) ? ',' : '') . $name;
                        $systemnames = $domreg{$systems}->{'name'};
                    } else {
                        $systems = '';
                    }
                }
                tied(%sysreg)->commit;
                untie(%sysreg);
            }
            $register{$uuid} = {
                uuid=>$uuid,
                user=>$username,
                id=>$id,
                name=>$name,
                internalip=>$internalip,
                externalip=>$externalip,
                ports=>$ports,
                type=>$type,
                systems=>$systems,
                systemnames=>$systemnames,
                action=>""
            };
            my $res = tied(%register)->commit;
            my $obj = $register{$uuid};
            $postreply .= "Status=OK Network $register{$uuid}->{'name'} saved: $uuid\n";
            $postreply .= "Status=OK uuid: $uuid\n" if ($console && $status eq 'new');
            if ($status eq 'new') {
                validateStatus($register{$uuid});
                $postmsg = "Created connection $name";
                $uiupdatetype = "update";
            }
            updateBilling("allocate $externalip") if (($type eq "ipmapping" || $type eq "externalip") && $externalip && $externalip ne "--");

        } else {
        	$postreply = "Status=OK Network $uuid ($id) unchanged\n";
        }

        if ($params{'PUTDATA'}) {
            my %jitem = %{$register{$uuid}};
            my $json_text = to_json(\%jitem);
            $json_text =~ s/null/"--"/g;
            $json_text =~ s/""/"--"/g;
            $postreply = $json_text;
            $postmsg = $postmsg || "OK, updated network $name";
        }

        return $postreply;

    } else {
        if ($id ne $regnet->{'id'} ||
        $internalip ne $regnet->{'internalip'} || $externalip ne $regnet->{'externalip'}) {
            return "Status=ERROR Cannot modify active network: $uuid\n";
        } elsif ($name ne $regnet->{'name'}) {
            $register{$uuid}->{'name'} = $name;
            $postreply .= "Status=OK Network \"$register{$uuid}->{'name'}\" saved: $uuid\n";
            if ($params{'PUTDATA'}) {
                my %jitem = %{$register{$uuid}};
                my $json_text = to_json(\%jitem);
                $json_text =~ s/null/"--"/g;
                $postreply = $json_text;
                $postmsg = "OK, updated network $name";
            }
        } else {
            $postreply .= "Status=OK Nothing to save\n";
            if ($params{'PUTDATA'}) {
                my %jitem = %{$register{$uuid}};
                my $json_text = to_json(\%jitem);
                $json_text =~ s/null/"--"/g;
                $postreply = $json_text;
            }
        }
    }

}

sub Activate {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
Activate a network which must be in status down or nat.
END
    }
    $uuid = $obj->{'uuid'} if ($obj->{'uuid'});
    $action = 'activate' || $action;
    my $regnet = $register{$uuid};
    my $id = $regnet->{'id'};
    my $name = $regnet->{'name'};
    my $type = $regnet->{'type'};
    my $status = $regnet->{'status'};
    my $domains = $regnet->{'domains'};
    my $systems = $regnet->{'systems'};
    my $internalip = $regnet->{'internalip'};
    my $externalip = $regnet->{'externalip'};
    my $ports = $regnet->{'ports'};
    my $idleft = ($id>99)?(substr $id,0,-2)+0 : 0;
    my $idright = (substr $id,-2) + 0;
    my $interfaces = `/sbin/ifconfig`;
    my $dom = $domreg{$domains};
    my $nicindex = ($dom->{'networkuuid1'} eq $uuid)?1:
            ($dom->{'networkuuid2'} eq $uuid)?2:
            ($dom->{'networkuuid3'} eq $uuid)?3:
            0;
    my $nicmac = $dom->{"nicmac$nicindex"};
    my $e;

	if (!$id || $id==0 || $id==1 || $id>4095) {
        $postreply .= "Status=ERROR Invalid ID activating $type\n";
	    return $postreply;
	} elsif (overQuotas()) { # Enforce quotas
        $postreply .= "Status=ERROR Over quota activating $type " . overQuotas() . "\n";
        return $postreply;
    } elsif (($status ne 'down' && $status ne 'nat')) {
        $postreply .= "Status=ERROR Cannot activate $type $name (current status is: $status)\n";
        return $postreply;
    }
    # Enable nat'ing
    eval {
        my $masq = `/sbin/iptables -L -n -t nat`;
#        if (!($masq =~ "MASQUERADE.+all.+--.+0\.0\.0\.0/0")) {
        `/sbin/iptables -D POSTROUTING -t nat --out-interface $extnic -s 10.0.0.0/8 -j MASQUERADE`;
        `/sbin/iptables -A POSTROUTING -t nat --out-interface $extnic -s 10.0.0.0/8 -j MASQUERADE`;
            # Christian's dev environment
#            my $interfaces = `/sbin/ifconfig`;
#            if ($interfaces =~ m/ppp0/) {
#                `/sbin/iptables --table nat --append POSTROUTING --out-interface ppp0 -s 10.0.0.0/8 -j MASQUERADE`;
#            }
#        };
        1;
    } or do {print "Unable to enable masquerading: $@\n";};

    # Check if vlan with $id is created and doing nat, if not create it and create the gateway
    unless (-e "/proc/net/vlan/$datanic.$id") {
        eval {`/sbin/vconfig add $datanic $id`;} or do {$e=1; $postreply .= "Status=ERROR Problem adding vlan $datanic.$id $@\n"; return $postreply;};
        eval {`/sbin/ifconfig $datanic.$id up`;}# or do {$e=1; $postreply .= "Status=ERROR Problem activating vlan $datanic.$id $@\n"; return $postreply;};
    }
#    if (!($interfaces =~ m/$datanic\.$id /)) {
    if (!($interfaces =~ m/br$id /)) {
        # check if gw is created locally
        unless (`arping -C1 -c2 -D -I $datanic.$id 10.$idleft.$idright.1` =~ /reply from/) { # check if gw is created on another engine
            # Create gw
#            eval {`/sbin/ifconfig $datanic.$id 10.$idleft.$idright.1 netmask 255.255.255.0 broadcast 10.$idleft.$idright.255 up`; 1;} or do {
#                $e=1; $postreply .= "Status=ERROR $@\n"; return $postreply;
            #            };
            # To support local instances on valve, gw is now created as a bridge
            eval {`/sbin/brctl addbr br$id`; 1;} or do {$e=1; $postreply .= "Status=ERROR $@\n"; return $postreply; };
            eval {`/sbin/brctl addif br$id $datanic.$id`; 1;} or do {$e=1; $postreply .= "Status=ERROR $@\n"; return $postreply; };
            eval {`/sbin/ifconfig br$id 10.$idleft.$idright.1/24 up`; 1;} or do {
                $e=1; $postreply .= "Status=ERROR $@\n"; return $postreply; }
        } else {
            $postreply .= "Status=OK GW is active on another Engine, assuming this is OK\n";
        }
    }
    my $astatus = "nat" unless ($e);
    `/usr/bin/touch $etcpath/dhcp-hosts-$id` unless (-e "$etcpath/dhcp-hosts-$id");
    if ($action eq "activate") { #} && $domains) {
        if ($type eq "internalip" || $type eq "ipmapping") {
            # Configure internal dhcp server
            if ($domains) {
                my $result = addDHCPAddress($id, $domains, $internalip, "10.$idleft.$idright.1", $nicmac);
                if ($result eq "OK") {
                    $astatus = "up" if ($type eq "internalip");
                } else {
                    $e = 1;
                    $postreply .= "$result\n";
                }
            }

            # Also export storage pools to user's network
            my @spl = split(/,\s*/, $storagepools);
            my $reloadnfs;
            my $uid = `id -u irigo-$user`; chomp $uid;
            $uid = `id -u nobody` unless ($uid =~ /\d+/); chomp $uid;
            my $gid = `id -g irigo-$user`; chomp $gid;
            $gid = `id -g nobody` unless ($gid =~ /\d+/); chomp $gid;

            # We are dealing with multiple upstream routes - configure local routing
            if ($proxynic && $proxynic ne $extnic) {
                if (-e "/etc/iproute2/rt_tables" && !grep(/1 proxyarp/, `cat /etc/iproute2/rt_tables`)) {
                    `/bin/echo "1 proxyarp" >> /etc/iproute2/rt_tables`;
                }
                if (!grep(/$datanic\.$id/, `/sbin/ip route show table proxyarp`)) {
                    `/sbin/ip route add "10.$idleft.$idright.0/24" dev $datanic.$id table proxyarp`;
                }
            }

            # Manuipulate NFS exports and related disk quotas
            foreach my $p (@spl) {
                if ($tenderlist[$p] && $tenderpathslist[$p]) {
                    my $fuelpath = $tenderpathslist[$p] . "/$user/fuel";
                    unless (-e $fuelpath) {
                        if ($tenderlist[$p] eq 'local') { # We only support fuel on local tender for now
                            `mkdir "$fuelpath"`;
                            `chmod 777 "$fuelpath"`;
                        }
                    }
                    if ($tenderlist[$p] eq "local") {
                        `chown irigo-$user:irigo-$user "$fuelpath"`;
                        my $mpoint = `df -P "$fuelpath" | tail -1 | cut -d' ' -f 1`;
                        chomp $mpoint;
                        my $storagequota = $Stabile::userstoragequota;
                        if (!$storagequota) {
                            $storagequota = $Stabile::config->get('STORAGE_QUOTA');
                        }
                        my $nfsquota = $storagequota * 1024 ; # quota is in MB
                        $nfsquota = 0 if ($nfsquota < 0); # quota of -1 means no limit
                        `setquota -u irigo-$user $nfsquota $nfsquota 0 0 "$mpoint"` if (-e "$mntpoint");
                        if (!(`grep "$fuelpath 10\.$idleft\.$idright" /etc/exports`) && -e $fuelpath) {
                            `echo "$fuelpath 10.$idleft.$idright.0/255.255.255.0(sync,no_subtree_check,all_squash,rw,anonuid=$uid,anongid=$gid)" >> /etc/exports`;
                            $reloadnfs = 1;
                        }
                    }
                }
            }
            `/usr/sbin/exportfs -r` if ($reloadnfs); #Reexport nfs shares

        } elsif ($type eq "externalip") {
            # A proxy is needed to route traffic, don't go any further if not configured
            if ($proxyip) {
                # Set up proxy
                if (!($interfaces =~ m/$proxyip/ && $interfaces =~ m/br$id:proxy/)) {
                    eval {`/sbin/ifconfig br$id:proxy $proxyip/$proxysubnet up`; 1;}
                        or do {$e=1; $postreply .= "Status=ERROR Problem setting up proxy arp gw $datanic.$id $@\n";};
                    eval {`/sbin/ifconfig $proxynic:proxy $proxyip/$proxysubnet up`; 1;}
                        or do {$e=1; $postreply .= "Status=ERROR Problem setting up proxy arp gw $proxynic $@\n";};
                }
                my $result = "OK";
                # Configure dhcp server
                if ($domains) {
                    $result = addDHCPAddress($id, $domains, $externalip, "10.$idleft.$idright.1", $nicmac) if ($domains);
                    if ($result eq "OK") {
                        ;
                    } else {
                        $e = 1;
                        $postreply .= "$result\n";
                    }
                }
            } else {
                $postreply .= "Status=ERROR Cannot set up external IP without Proxy ARP gateway\n";
            }
        }

        # Handle routing with Iptables
        if ($type eq "ipmapping" || $type eq "internalip") {
            `iptables -I FORWARD -d $internalip -m state --state ESTABLISHED,RELATED -j RETURN`;
        }
        # Check if external ip exists and routing configured, if not create and configure it
        if ($type eq "ipmapping") {
            if ($internalip && $internalip ne "--" && $externalip && $externalip ne "--" && !($interfaces =~ m/$externalip /g)) { # the space is important
                $externalip =~ /\d+\.\d+\.(\d+\.\d+)/;
                my $ipend = $1; $ipend =~ s/\.//g;
                eval {`/sbin/ifconfig $extnic:$id-$ipend $externalip/$extsubnet up`; 1;}
                    or do {$e=1; $postreply .= "Status=ERROR Problem adding interface $extnic:$id-$ipend $@\n";};
                unless (`ip addr show dev $extnic` =~ /$externalip/) {
                    $e=10;
                    $postreply .= "Status=ERROR Problem adding interface $extnic:$id-$ipend\n";
                }
                # `/sbin/iptables -A POSTROUTING -t nat -s $internalip -j LOG --log-prefix "SNAT-POST"`;
                # `/sbin/iptables -A INPUT -t nat -s $internalip -j LOG --log-prefix "SNAT-INPUT"`;
                # `/sbin/iptables -A OUTPUT -t nat -s $internalip -j LOG --log-prefix "SNAT-OUTPUT"`;
                # `/sbin/iptables -A PREROUTING -t nat -s $internalip -j LOG --log-prefix "SNAT-PRE"`;
                if ($ports && $ports ne "--") { # Port mapping is defined
                    my @portslist = split(/, ?| /, $ports);
                    foreach $port (@portslist) {
                        my $ipfilter;
                        if ($port =~ /(\d+)\.(\d+)\.(\d+)\.(\d+)(\/\d+)?:(\d+)/) {
                            my $portip = "$1.$2.$3.$4$5";
                            $port = $6;
                            $ipfilter = "-s $portip";
                        } else {
                            $port = 0 unless ($port =~ /\d+/);
                        }
                        if ($port<1 || $port>65535) {
                            $postreply .= "Status=ERROR Invalid port mapping for $name\n";
                            $ports = "--";
                            last;
                        }

                        if ($port>1 || $port<65535) {
                            # DNAT externalip -> internalip
                            eval {`/sbin/iptables -A PREROUTING -t nat -p tcp $ipfilter -d $externalip --dport $port -j DNAT --to $internalip`; 1;}
                               or do {$e=2; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                            eval {`/sbin/iptables -A PREROUTING -t nat -p udp $ipfilter -d $externalip --dport $port -j DNAT --to $internalip`; 1;}
                               or do {$e=3; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                            # PREROUTING is not parsed for packets coming from local host...
                            eval {`/sbin/iptables -A OUTPUT -t nat -p tcp $ipfilter -d $externalip --dport $port -j DNAT --to $internalip`; 1;}
                                or do {$e=2; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                            eval {`/sbin/iptables -A OUTPUT -t nat -p udp $ipfilter -d $externalip --dport $port -j DNAT --to $internalip`; 1;}
                                or do {$e=3; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                            # Allow access to ipmapped internal ip on $port
                            `iptables -I FORWARD -d $internalip -p tcp --dport $port -j RETURN`;
                            `iptables -I FORWARD -d $internalip -p udp --dport $port -j RETURN`;
                        }
                    }
                    eval {`/sbin/iptables -D INPUT -d $externalip -j DROP`; 1;} # Drop traffic to all other ports
                        or do {$e=5; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                    eval {`/sbin/iptables -A INPUT -d $externalip -j DROP`; 1;} # Drop traffic to all other ports
                        or do {$e=6; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                } else {
                    # DNAT externalip -> internalip coming from outside , --in-interface $extnic
                    eval {`/sbin/iptables -A PREROUTING -t nat -d $externalip -j DNAT --to $internalip`; 1;}
                        or do {$e=7; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                    # PREROUTING is not parsed for packets coming from local host...
                    eval {`/sbin/iptables -A OUTPUT -t nat -d $externalip -j DNAT --to $internalip`; 1;}
                        or do {$e=7; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                    # Allow blanket access to ipmapped internal ip
                    `iptables -I FORWARD -d $internalip -j RETURN`;
                }
                # We masquerade packets going to internalip from externalip to avoid confusion
                #eval {`/sbin/iptables -A POSTROUTING -t nat --out-interface br$id -s $externalip -j MASQUERADE`; 1;}
                #    or do {$e=3; $postreply .= "Status=ERROR Problem setting up routing $@\n";};

                # Masquerade packets from internal ip's not going to our own subnet
                # `/sbin/iptables -D POSTROUTING -t nat --out-interface br$id ! -d 10.$idleft.$idright.0/24 -j MASQUERADE`;
                #eval {`/sbin/iptables -A POSTROUTING -t nat --out-interface br$id ! -d 10.$idleft.$idright.0/24 -j MASQUERADE`; 1;}
                #    or do {$e=3; $postreply .= "Status=ERROR Problem setting up routing $@\n";};

                # When receiving packet from client, if it's been routed, and outgoing interface is the external interface, SNAT.
                unless ($Stabile::disablesnat) {
                    eval {`/sbin/iptables -A POSTROUTING -t nat -s $internalip ! -d 10.$idleft.$idright.0/24 -j SNAT --to-source $externalip`; 1; }
                        or do {$e=4; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                #    eval {`/sbin/iptables -A POSTROUTING -t nat -s $internalip -j SNAT --to-source $externalip`; 1; }
                #        or do {$e=4; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                    eval {`/sbin/iptables -I INPUT -t nat -s $internalip ! -d 10.$idleft.$idright.0/24 -j SNAT --to-source $externalip`; 1; }
                        or do {$e=4; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                #    eval {`/sbin/iptables -I INPUT -t nat -s $internalip -j SNAT --to-source $externalip`; 1; }
                #        or do {$e=4; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                }

                if ($e) {
                    $main::syslogit->($user, 'info', "Problem $action network $uuid ($name, $id): $@");
                } else {
                    $astatus = "up"
                }
            }
        } elsif ($type eq "externalip") {
            my $route = `/sbin/ip route`;
            my $tables = `/sbin/iptables -L -n`;

            # Allow external IP send packets out
            `/sbin/iptables -D FORWARD --in-interface br$id -s $externalip -j RETURN`;
            `/sbin/iptables -I FORWARD --in-interface br$id -s $externalip -j RETURN`;

            # We are dealing with multiple upstream routes - configure local routing
            if ($proxynic && $proxynic ne $extnic) {
                if (-e "/etc/iproute2/rt_tables" && !grep(/1 proxyarp/, `cat /etc/iproute2/rt_tables`)) {
                    `/bin/echo "1 proxyarp" >> /etc/iproute2/rt_tables`;
                }
                if (!grep(/$proxygw/, `/sbin/ip route show table proxyarp`)) {
                    `/sbin/ip route add default via $proxygw dev $proxynic table proxyarp`;
                }
                if (!grep(/proxyarp/, `/sbin/ip rule show`)) {
                    `/sbin/ip rule add to $proxygw/$proxysubnet table main`;
                    `/sbin/ip rule add from $proxygw/$proxysubnet table proxyarp`;
                }
                my $proxyroute = `/sbin/ip route show table proxyarp`;
#                `/sbin/ip route add $externalip/32 dev $datanic.$id:proxy src $proxyip table proxyarp` unless ($proxyroute =~ /$externalip/);
                `/sbin/ip route add $externalip/32 dev br$id:proxy src $proxyip table proxyarp` unless ($proxyroute =~ /$externalip/);
            }
            eval {`/bin/echo 1 > /proc/sys/net/ipv4/conf/$datanic.$id/proxy_arp`; 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up proxy arp $@\n";};
            eval {`/bin/echo 1 > /proc/sys/net/ipv4/conf/$proxynic/proxy_arp`; 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up proxy arp $@\n";};
            eval {`/sbin/ip route add $externalip/32 dev br$id:proxy src $proxyip` unless ($route =~ /$externalip/); 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up proxy arp $@\n";};

            eval {`/sbin/iptables -D FORWARD -i $proxynic -d $externalip -m state --state ESTABLISHED,RELATED -j RETURN`; 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            eval {`/sbin/iptables -A FORWARD -i $proxynic -d $externalip -m state --state ESTABLISHED,RELATED -j RETURN`; 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};


            eval {`/sbin/iptables -D FORWARD -i $proxynic -d $externalip -j REJECT` if
                ($tables =~ /REJECT .+ all .+ $externalip/); 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};

            if ($ports && $ports ne "--") {
                my @portslist = split(/, ?| /, $ports);
                foreach $port (@portslist) {
                    my $ipfilter;
                    if ($port =~ /(\d+)\.(\d+)\.(\d+)\.(\d+)(\/\d+)?:(\d+)/) {
                        my $portip = "$1.$2.$3.$4$5";
                        $port = $6;
                        $ipfilter = "-s $portip";
                    } else {
                        $port = 0 unless ($port =~ /\d+/);
                    }
                    if ($port<1 || $port>65535) {
                        $postreply .= "Status=ERROR Invalid port mapping for $name\n";
                        $ports = "--";
                        last;
                    }

                    if ($port>1 && $port<65535 && $port!=67) { # Disallow setting up a dhcp server
                        eval {`/sbin/iptables -A FORWARD -p tcp -i $proxynic $portfilter -d $externalip --dport $port -j RETURN`; 1;}
                            or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                        eval {`/sbin/iptables -A FORWARD -p udp -i $proxynic $portfilter -d $externalip --dport $port -j RETURN`; 1;}
                            or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                    }
                }
                eval {`/sbin/iptables -D FORWARD -i $proxynic -d $externalip -j REJECT`; 1;} # Drop traffic to all other ports
                    or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                eval {`/sbin/iptables -A FORWARD -i $proxynic -d $externalip -j REJECT`; 1;} # Drop traffic to all other ports
                    or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            } else {
                # First allow everything else to this ip
                eval {`/sbin/iptables -D FORWARD -i $proxynic -d $externalip -j RETURN`; 1;}
                    or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                eval {`/sbin/iptables -A FORWARD -i $proxynic -d $externalip -j RETURN`; 1;}
                    or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                # Then disallow setting up a dhcp server
                eval {`/sbin/iptables -D FORWARD -p udp -i $proxynic -d $externalip --dport 67 -j REJECT`; 1;}
                    or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                eval {`/sbin/iptables -A FORWARD -p udp -i $proxynic -d $externalip --dport 67 -j REJECT`; 1;}
                    or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            }
        }
    }

    # Allow all inter-VLAN communication
    `iptables -D FORWARD --in-interface br$id --out-interface br$id -j RETURN 2>/dev/null`;
    `iptables -I FORWARD --in-interface br$id --out-interface br$id -j RETURN`;
    # Disallow any access to vlan except mapped from external NIC i.e. ipmappings
    `iptables -D FORWARD ! --in-interface $extnic --out-interface br$id -j DROP 2>/dev/null`;
    `iptables -A FORWARD ! --in-interface $extnic --out-interface br$id -j DROP`;

    # Only forward packets coming from subnet assigned to vlan unless we are setting up a gateway on the proxy nic and the proxy nic is on a vlan
#    `/sbin/iptables --delete FORWARD --in-interface $datanic.$id ! -s 10.$idleft.$idright.0/24 -j DROP`;
    unless ($proxynic eq "$datanic.$id") {
#        `/sbin/iptables --append FORWARD --in-interface $datanic.$id ! -s 10.$idleft.$idright.0/24 -j DROP`;
    }

    $uistatus = ($e)?"":validateStatus($register{$uuid});
    if ($uistatus && $uistatus ne 'down') {
        $uiuuid = $uuid;
        $postreply .= "Status=$uistatus OK $action $type $name\n";
    } else {
        $postreply .= "Status=ERROR Cannot $action $type $name ($uistatus)\n";
    }
    $main::syslogit->($user, 'info', "$action network $uuid ($name, $id) -> $uistatus");
    updateBilling("$uistatus $uuid ($id)");
    # $main::updateUI->({tab=>"networks", user=>$user, uuid=>$uiuuid, status=>$uistatus}) if ($uistatus);
    return $postreply;
}

sub Removeusernetworks {
    my $username = shift;
    return unless (($isadmin || $user eq $username) && !$isreadonly);
    $user = $username;
    foreach my $uuid (keys %register) {
        if ($register{$uuid}->{'user'} eq $user) {
            $postreply .=  "Removing network $register{$path}->{'name'}, $uuid" . ($console?'':'<br>') . "\n";
            Deactivate($uuid);
            Remove('remove', $uuid);
        }
    }
}

sub Remove {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
DELETE:uuid,force:
Delete a network which must be in status down or nat and should not be used by any servers, or linked to any stacks.
May also be called with endpoints "/stabile/[uuid]" or "/stabile?uuid=[uuid]"
Set [force] to remove even if linked to a system.
END
    }
    $uuid = $obj->{'uuid'} if ($curuuid && $obj->{'uuid'}); # we are called from a VM with an ip address as target
    my $force = $obj->{'force'};
    ( my $domains, my $domainnames ) = getDomains($uuid);
    ( my $systems, my $systemnames ) = getSystems($uuid);

    if ($register{$uuid}) {
        my $id = $register{$uuid}->{'id'};
        my $name = $register{$uuid}->{'name'};
        utf8::decode($name);
        my $status = $register{$uuid}->{'status'};
        my $type = $register{$uuid}->{'type'};
        my $internalip = $register{$uuid}->{'internalip'};
        my $externalip = $register{$uuid}->{'externalip'};

        my @regvalues = values %register;
        if (
            $id!=0 && $id!=1 && (!$domains || $domains eq '--')
                && ((!$systems || $systems eq '--' || $force)
                # allow internalip's to be removed if active and only linked, i.e. not providing dhcp
                || ($status eq 'down' || $status eq 'new' || $status eq 'nat' || ($type eq 'internalip' && $systems && $systems ne '--')))
        ) {
            # Deconfigure internal dhcp server and DNS
            if ($type eq "internalip") {
                my $result =  removeDHCPAddress($id, $domains, $internalip);
                $postreply .= "$result\n" unless $result eq "OK";
            } elsif ($type eq "ipmapping") {
                my $result =  removeDHCPAddress($id, $domains, $internalip);
                $postreply .= "$result\n" unless $result eq "OK";
                if ($dodns) {
                    $main::dnsDelete->($engineid, $externalip) if ($enginelinked);
                }
            } elsif ($type eq "externalip") {
                my $result =  removeDHCPAddress($id, $domains, $externalip);
                $postreply .= "$result\n" unless $result eq "OK";
                if ($dodns) {
                    $main::dnsDelete->($engineid, $externalip) if ($enginelinked);
                }
            }
            if ($status eq 'nat') {
                # Check if last network in vlan. If so take it down
                my $notlast;
                foreach my $val (@regvalues) {
                    if ($val->{'user'} eq $user && $val->{'id'} == $id) {
                        $notlast = 1;
                    }
                }
                if (!$notlast) {
                    eval {`/sbin/ifconfig $datanic.$id down`; 1;} or do {;};
                    eval {`/sbin/vconfig rem $datanic.$id`; 1;} or do {;};
                }
            }

            unless (tie(%sysreg,'Tie::DBI', Hash::Merge::merge({table=>'systems'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access systems register"}|; return $res;};
            if ($sysreg{$systems}) { # Remove existing link to system
                $sysreg{$systems}->{'networkuuids'} =~ s/$uuid,?//;
                $sysreg{$systems}->{'networknames'} = s/$name,?//;
            }
            tied(%sysreg)->commit;
            untie(%sysreg);


            delete $register{$uuid};
            tied(%register)->commit;
            updateBilling("delete $val->{'externalip'}") if ($type eq "ipmapping");
            $main::syslogit->($user, "info", "Deleted network $uuid ($id)");
            $postreply = "[]" || $postreply;
            $main::updateUI->({tab=>"networks", user=>$user, type=>"update"});
        } else {
            $postreply .= "Status=ERROR Cannot remove $uuid which is $status. Cannot delete network 0,1 or a network which is active or in use.\n";
            $main::updateUI->({tab=>"networks", user=>$user, message=>"Cannot remove a network which is active, linked or in use."});
        }
    } else {
        $postreply .= "Status=ERROR Network $uuid $ipaddress not found\n";
    }
    return $postreply;
}

sub Deactivate {
    my ($uuid, $action, $obj) = @_;

    if ($help) {
        return <<END
GET:uuid:
Deactivate a network which must be in status up.
END
    }
    $uuid = $obj->{'uuid'} if ($obj->{'uuid'});

    unless ($register{$uuid}) {
        $postreply .= "Status=ERROR Connection with uuid $uuid not found\n";
        return $postreply;
    }
    my $regnet = $register{$uuid};

    $action = $action || 'deactivate';
    ( my $domains, my $domainnames ) = getDomains($uuid);
    my $interfaces = `/sbin/ifconfig`;

    my $id = $regnet->{'id'};
    my $name = $regnet->{'name'};
    my $type = $regnet->{'type'};
    my $internalip = $regnet->{'internalip'};
    my $externalip = $regnet->{'externalip'};
    my $ports = $regnet->{'ports'};

    if ($id!=0 && $id!=1 && $status ne 'down') {
    # If gateway is created, take it down along with all user's networks
        if ($action eq "stop") {
            my $res = Stop($id, $action);
            if ($res) {
                unlink "$etcpath/dhcp-hosts-$id" if (-e "$etcpath/dhcp-hosts-$id");
            };
        }
    } else {
        $postreply .= "Status=ERROR Cannot $action network $name\n";
        return $postreply;
    }

    my $idleft = ($id>99)?(substr $id,0,-2)+0 : 0;
    my $idright = (substr $id,-2) + 0;
    my $e = 0;
    my $duprules = 0;

    if ($type eq "ipmapping" || $type eq "internalip") {
        `iptables -D FORWARD -d $internalip -m state --state ESTABLISHED,RELATED -j RETURN`;
    }
    if ($type eq "ipmapping") {
        # Check if external ip exists and take it down if so
        if ($internalip && $internalip ne "--" && $externalip && $externalip ne "--" && ($interfaces =~ m/$externalip/g)) {
            $externalip =~ /\d+\.\d+\.(\d+\.\d+)/;
            my $ipend = $1; $ipend =~ s/\.//g;
            eval {`/sbin/ifconfig $extnic:$id-$ipend down`; 1;} or do {$e=1; $postreply .= "Status=ERROR $@\n";};

            if ($ports && $ports ne "--") { # Port mapping is defined
                my @portslist = split(/, ?| /, $ports);
                foreach my $port (@portslist) {
                    my $ipfilter;
                    if ($port =~ /(\d+)\.(\d+)\.(\d+)\.(\d+)(\/\d+)?:(\d+)/) {
                        my $portip = "$1.$2.$3.$4$5";
                        $port = $6;
                        $ipfilter = "-s $portip";
                    } else {
                        $port = 0 unless ($port =~ /\d+/);
                    }
                    if ($port<1 || $port>65535) {
                        $postreply .= "Status=ERROR Invalid port mapping for $name\n";
                        $ports = "--";
                        last;
                    }
                    # Remove DNAT rules
                    if ($port>1 || $port<65535) {
                        # repeat for good measure
                        for (my $di=0; $di < 10; $di++) {
                            $duprules = 0;
                            eval {$duprules++ if (`/sbin/iptables -D PREROUTING -t nat -p tcp $ipfilter -d $externalip --dport $port -j DNAT --to $internalip`); 1;}
                                or do {$postreply .= "Status=ERROR $@\n"; $e=1};
                            eval {$duprules++ if (`/sbin/iptables -D PREROUTING -t nat -p udp $ipfilter -d $externalip --dport $port -j DNAT --to $internalip`); 1;}
                                or do {$postreply .= "Status=ERROR $@\n"; $e=1};
                            eval {$duprules++ if (`/sbin/iptables -D OUTPUT -t nat -p tcp $ipfilter -d $externalip --dport $port -j DNAT --to $internalip`); 1;}
                                or do {$postreply .= "Status=ERROR $@\n"; $e=1};
                            eval {$duprules++ if (`/sbin/iptables -D OUTPUT -t nat -p udp $ipfilter -d $externalip --dport $port -j DNAT --to $internalip`); 1;}
                                or do {$postreply .= "Status=ERROR $@\n"; $e=1};
                            eval {$duprules++ if (`/sbin/iptables -D POSTROUTING -t nat --out-interface br$id -s $externalip -j MASQUERADE`); 1;}
                                or do {$e=3; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                            # Remove access to ipmapped internal ip on $port
                            eval {$duprules++ if (`/sbin/iptables -D FORWARD -d $internalip -p udp --dport $port -j RETURN`); 1;}
                                or do {$e=3; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                            eval {$duprules++ if (`/sbin/iptables -D FORWARD -d $internalip -p tcp --dport $port -j RETURN`); 1;}
                                or do {$e=3; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                            last if ($duprules >6);
                        }
                    }
                }
                # Remove SNAT rules
                # repeat for good measure
                for (my $di=0; $di < 10; $di++) {
                    $duprules = 0;
                    eval {$duprules++ if (`/sbin/iptables -D POSTROUTING -t nat -s $internalip ! -d 10.$idleft.$idright.0/24 -j SNAT --to-source $externalip`); 1; }
                        or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                    last if ($duprules);
                }
                # Remove rule to drop traffic to all other ports
                eval {`/sbin/iptables -D INPUT -d $externalip -j DROP`; 1;}
                    or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            } else {
                # Remove DNAT rules
                # repeat for good measure
                for (my $di=0; $di < 10; $di++) {
                    $duprules = 0;
                    eval {$duprules++ if (`/sbin/iptables -D PREROUTING -t nat -d $externalip -j DNAT --to $internalip`); 1;}
                        or do {$postreply .= "Status=ERROR $@\n"; $e=1};
                    eval {$duprules++ if (`/sbin/iptables -D OUTPUT -t nat -d $externalip -j DNAT --to $internalip`); 1;}
                        or do {$postreply .= "Status=ERROR $@\n"; $e=1};
                    last if ($duprules >1);
                }
                # Remove blanket access to ipmapped internal ip
                `iptables -D FORWARD -d $internalip -j RETURN`;
            }
            # Remove SNAT and MASQUERADE rules
            # repeat for good measure
            for (my $di=0; $di < 10; $di++) {
                $duprules = 0;
            #    eval {$duprules++ if (`/sbin/iptables -D POSTROUTING -t nat --out-interface br$id -s $externalip -j MASQUERADE`); 1;}
            #        or do {$e=3; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                eval {$duprules++ if (`/sbin/iptables -D POSTROUTING -t nat --out-interface br$id ! -d 10.$idleft.$idright.0/24 -j MASQUERADE`); 1;}
                    or do {$e=3; $postreply .= "Status=ERROR Problem setting up routing $@\n";};

                eval {$duprules++ if (`/sbin/iptables -D POSTROUTING -t nat -s $internalip ! -d 10.$idleft.$idright.0/24 -j SNAT --to-source $externalip`); 1; }
                    or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            #    eval {$duprules++ if (`/sbin/iptables -D POSTROUTING -t nat -s $internalip -j SNAT --to-source $externalip`); 1; }
            #        or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                eval {$duprules++ if (`/sbin/iptables -D INPUT -t nat -s $internalip ! -d 10.$idleft.$idright.0/24 -j SNAT --to-source $externalip`); 1; }
                    or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            #    eval {$duprules++ if (`/sbin/iptables -D INPUT -t nat -s $internalip -j SNAT --to-source $externalip`); 1; }
            #        or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            #    eval {$duprules++ if (`/sbin/iptables -D INPUT -t nat -s $internalip ! -d 10.$idleft.$idright.0/24 -j SNAT --to-source $externalip`); 1; }
            #        or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            #    eval {$duprules++ if (`/sbin/iptables -D INPUT -t nat -s $internalip -j SNAT --to-source $externalip`); 1; }
            #        or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                last if ($duprules >1);
            }
            # `/sbin/iptables -D POSTROUTING -t nat -s $internalip -j LOG --log-prefix "SNAT-POST"`;
            # `/sbin/iptables -D INPUT -t nat -s $internalip -j LOG --log-prefix "SNAT-INPUT"`;
            # `/sbin/iptables -D OUTPUT -t nat -s $internalip -j LOG --log-prefix "SNAT-OUTPUT"`;
            # `/sbin/iptables -D PREROUTING -t nat -s $internalip -j LOG --log-prefix "SNAT-PRE"`;
        }
    } elsif ($type eq "externalip") {
        if ($externalip && $externalip ne "--") {
            # We are dealing with multiple upstream routes - configure local routing
            if ($proxynic && $proxynic ne $extnic) {
                my $proxyroute = `/sbin/ip route show table proxyarp`;
                `/sbin/ip route del $externalip/32 dev br$id:proxy src $proxyip table proxyarp` if ($proxyroute =~ /$externalip/);
            }

            eval {`/sbin/ip route del $externalip/32 dev br$id:proxy`; 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem deconfiguring proxy arp $@\n";};

            if ($ports && $ports ne "--") {
                my @portslist = split(/, ?| /, $ports);
                foreach my $port (@portslist) {
                    my $ipfilter;
                    if ($port =~ /(\d+)\.(\d+)\.(\d+)\.(\d+)(\/\d+)?:(\d+)/) {
                        my $portip = "$1.$2.$3.$4$5";
                        $port = $6;
                        $ipfilter = "-s $portip";
                    } else {
                        $port = 0 unless ($port =~ /\d+/);
                    }
                    if ($port<1 || $port>65535) {
                        $postreply .= "Status=ERROR Invalid port mapping for $name\n";
                        $ports = "--";
                        last;
                    }

                    if ($port>1 || $port<65535) {
                        # repeat for good measure
                        for (my $di=0; $di < 10; $di++) {
                            $duprules = 0;
                            eval {$duprules++ if (`/sbin/iptables -D FORWARD -p tcp -i $proxynic $ipfilter -d $externalip --dport $port -j RETURN`); 1;}
                                or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                            eval {$duprules++ if (`/sbin/iptables -D FORWARD -p udp -i $proxynic $ipfilter -d $externalip --dport $port -j RETURN`); 1;}
                                or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
                            last if ($duprules > 1);
                        }
                    }
                }
            }
            # Remove rule to allow forwarding from $externalip
	        `/sbin/iptables --delete FORWARD --in-interface br$id -s $externalip -j RETURN`;
            # Remove rule to disallow setting up a dhcp server
            eval {`/sbin/iptables -D FORWARD -p udp -i $proxynic -d $externalip --dport 67 -j REJECT`; 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            # Leave outgoing connectivity - not
            eval {`/sbin/iptables -D FORWARD -i $proxynic -d $externalip -m state --state ESTABLISHED,RELATED -j RETURN`; 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            eval {`/sbin/iptables -D FORWARD -i $proxynic -d $externalip -j RETURN`; 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
            # No need to reject - we reject all per default to the subnet
            eval {`/sbin/iptables -D FORWARD -i $proxynic -d $externalip -j REJECT`; 1;}
                or do {$e=1; $postreply .= "Status=ERROR Problem setting up routing $@\n";};
        }
    }
    # Deconfigure internal dhcp server
    if ($type eq "internalip" || $type eq "ipmapping") {
        my $result =  removeDHCPAddress($id, $domains, $internalip);
        if ($result ne "OK") {
            $e=1;
            $postreply .= "$result\n";
        }
    } elsif ($type eq "externalip" && $domains) {
        my $result =  removeDHCPAddress($id, $domains, $externalip);
        if ($result ne "OK") {
            $e=1;
            $postreply .= "$result\n";
        }
    }
    $uistatus = ($e)?"":validateStatus($register{$uuid});
    if ($uistatus) {
        $uiuuid = $uuid;
        $postreply .= "Status=$uistatus OK $action $type $name: $uistatus\n";
    } else {
        $postreply .= "Status=ERROR Cannot $action $type $name: $uistatus\n";
    }
    $main::syslogit->($user, 'info', "$action network $uuid ($name, $id) -> $uistatus");
    updateBilling("$uistatus $uuid ($id)");
    # $main::updateUI->({tab=>"networks", user=>$user, uuid=>$uiuuid, status=>$uistatus}) if ($uistatus);
    return $postreply;
}

sub Stop {
    my ($id, $action) = @_;
    # Check if we were passed a uuid
    if ($id =~ /\-/ && $register{$id} && ($register{$id}->{'user'} eq $user || $isadmin)) {
        $id = $register{$id}->{'id'}
    }
    if ($help) {
        return <<END
GET:uuid:
Stops a network by removing gateway. Network must be in status up or nat.
END
    }

    my $idleft = ($id>99)?(substr $id,0,-2)+0 : 0;
    my $idright = (substr $id,-2) + 0;
    my $e = 0;
    # First deactivate all user's networks with same id
    my @regkeys = (tied %register)->select_where("user = '$user'");
    foreach my $key (@regkeys) {
        my $valref = $register{$key};
        my $cuuid = $valref->{'uuid'};
        my $ctype = $valref->{'type'};
        my $cdbuser = $valref->{'user'};
        my $cid = $valref->{'id'};
    # Only list networks belonging to current user
        if ($user eq $cdbuser && $id eq $cid && $ctype ne "gateway") {
            if ($ctype eq "internalip" || $ctype eq "ipmapping" || $ctype eq "externalip") {
                my $result = Deactivate($cuuid, 'deactivate');
                if ($result =~ /\w+=ERROR (.+)/i) {
                    $e = $1;
                }
            }
        }
     }
    my $interfaces = `/sbin/ifconfig br$id`;
     # Only take down interface and vlan if gateway IP is active on interface
    if ($e) {
        $postreply .= "Status=Error Not taking down gateway, got an error: $e\n"
#    } elsif ($interfaces =~ /^$datanic\.$id.+\n.+inet .+10\.$idleft\.$idright\.1/
    } elsif ($interfaces =~ /10\.$idleft\.$idright\.1/
            && !$e) {
        eval {`/sbin/brctl delif br$id $datanic.$id`; 1;} or do {$e=1;};
        eval {`/sbin/ifconfig br$id down`; 1;} or do {$e=1;};
        eval {`/sbin/ifconfig $datanic.$id down`; 1;} or do {$e=1;};
        eval {`/sbin/vconfig rem $datanic.$id`; 1;} or do {$e=1;};
    } else {
        $postreply .= "Status=Error Not taking down interface, gateway 10.$idleft.$idright.1 is not active on interface br$id - $interfaces.\n"
    }
    # Remove rule to only forward packets coming from subnet assigned to vlan
#    `/sbin/iptables --delete FORWARD --in-interface $datanic.$id ! -s 10.$idleft.$idright.0/24 -j DROP`;

    $uistatus = ($e)?$uistatus:"down";
    if ($uistatus eq 'down') {
        $uiuuid = $uuid;
        $postreply .= "Status=$uistatus OK $action gateway: $uistatus\n";
    } else {
        $postreply .= "Status=Error Cannot $action $type $name: $uistatus\n";
    }
    return $postreply;
}

sub getDomains {
    my $uuid = shift;
    my $domains;
    my $domainnames;
    my @domregvalues = values %domreg;
    foreach my $domval (@domregvalues) {
        if (($domval->{'networkuuid1'} eq $uuid || $domval->{'networkuuid2'} eq $uuid || $domval->{'networkuuid3'} eq $uuid)
                && $domval->{'user'} eq $user) {
            $domains .= $domval->{'uuid'} . ", ";
            $domainnames .= $domval->{'name'} . ", ";
        }
    }
    $domains = substr $domains, 0, -2;
    $domainnames = substr $domainnames, 0, -2;
    return ($domains, $domainnames); 
}

sub getSystems {
    my $uuid = shift;
    my $systems;
    my $systemnames;
    unless (tie(%sysreg,'Tie::DBI', Hash::Merge::merge({table=>'systems'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access systems register"}|; return $res;};
    my @sysregvalues = values %sysreg;
    foreach my $sysval (@sysregvalues) {
        my $networkuuids = $sysval->{'networkuuids'};
        if ($networkuuids =~ /$uuid/ && $sysval->{'user'} eq $user) {
            $systems = $sysval->{'uuid'};
            $systemnames = $sysval->{'name'};
            last;
        }
    }
    unless ($systems) {
        my @sysregvalues = values %domreg;
        foreach my $sysval (@sysregvalues) {
            my $networkuuids = $sysval->{'networkuuids'};
            if ($networkuuids =~ /$uuid/ && $sysval->{'user'} eq $user) {
                $systems = $sysval->{'uuid'};
                $systemnames = $sysval->{'name'};
                last;
            }
        }
    }
    return ($systems, $systemnames);
}

sub getNextId {
	# Find the next available vlan id
	my $reqid = shift;
	my $username = shift;
	$username = $user unless ($username);
    my $nextid = 1;
	my $vlanstart = $Stabile::config->get('VLAN_RANGE_START');
	my $vlanend = $Stabile::config->get('VLAN_RANGE_END');

    if ($reqid eq 0 || $reqid == 1) {
        return $requid;
    } elsif ($reqid && ($reqid > $vlanend || $reqid < $vlanstart)) {
        return -1 unless ($isadmin);
    }

	$reqid = $reqid + 0;

    my %ids;
    # First check if the user has an existing vlan, if so use the first we find as default value
    my @regvalues = values %register;
    @regvalues = (sort {$a->{id} <=> $b->{id}} @regvalues);
    foreach my $val (@regvalues) { # Traverse all id's in use
        my $id = 0 + $val->{'id'};
        my $dbuser = $val->{'user'};
        if ($id > 1) {
            if ($username eq $dbuser) { # If a specific id was requested map all id's
                if (!$reqid) {# If no specific id was asked for, stop now, and use the user's first one
                    $nextid = $id;
                    last;
                }
            } else {
                $ids{$id} = 1; # Mark this id as used (by another user)
            }
        }
    }
    if ($nextid>1) {
        return $nextid;
    } elsif ($reqid) {
        if (!$ids{$reqid} || $isadmin) { # If an admin is requesting id used by another, assume he knows what he is doing
            $nextid = $reqid; # Safe to use
        } else {
            $nextid = -1; # Id already in use by another
        }
    } elsif ($nextid == 1) { # This user is not currently using any vlan's, find the first free one
        for ($n=$vlanstart; $n<$vlanend; $n++) {
            if (!$ids{$n}) { # Don't return an id used (by another user)
                $nextid = $n;
                last;
            }
        }
    }
	return $nextid;
}

sub getNextExternalIP {
	# Find the next available IP
	my $extip = shift;
	my $extuuid = shift;
	my $proxyarp = shift; # Are we trying to assign a proxy arp's external IP?
	$extip="" if ($extip eq "--");

	my $extipstart;
	my $extipend;

    if ($proxyarp) {
        $extipstart = $Stabile::config->get('PROXY_IP_RANGE_START');
        $extipend = $Stabile::config->get('PROXY_IP_RANGE_END');
    } else {
        $extipstart = $Stabile::config->get('EXTERNAL_IP_RANGE_START');
        $extipend = $Stabile::config->get('EXTERNAL_IP_RANGE_END');
    }

	return "" unless ($extipstart && $extipend);

	my $interfaces = `/sbin/ifconfig`;
#	$interfaces =~ m/eth0 .+\n.+inet addr:(\d+\.\d+\.\d+)\.(\d+)/;
	$extipstart =~  m/(\d+\.\d+\.\d+)\.(\d+)/;
	my $bnet1 = $1;
	my $bhost1 = $2+0;
	$extipend =~  m/(\d+\.\d+\.\d+)\.(\d+)/;
	my $bnet2 = $1;
	my $bhost2 = $2+0;
	my $nextip = "";
	if ($bnet1 ne $bnet2) {
		print "Status=ERROR Only 1 class C subnet is supported for $name\n";
		return "";
	}
	my %ids;
	# First create map of IP's reserved by other servers in DB
	my @regvalues = values %register;
	foreach my $val (@regvalues) {
		my $ip = $val->{'externalip'};
		# $ip =~ m/(\d+\.\d+\.\d+)\.(\d+)/;
		# my $id = $2;
		$ids{$ip} = $val->{'uuid'} unless ($extuuid eq $val->{'uuid'});
	}
    
	if (overQuotas(1)) { # Enforce quotas
        $postreply .= "Status=ERROR Over quota allocating external IP\n";
	} elsif ($extip && $extip =~  m/($bnet1)\.(\d+)/ && $2>=$bhost1 && $2<$bhost2) {
	# An external ip was supplied - check if it's free and ok
		if (!$ids{$extip} && !($interfaces =~ m/$extip.+\n.+inet addr:$extip/) && $extip=~/$bnet$\.(\d)/) {
			$nextip = $extip;
		}
	} else {
	# Find random IP not reserved, and check it is not in use (for other purposes)
	    my @bhosts = ($bhost1..$bhost2);
        my @rbhosts = shuffle @bhosts;
		for ($n=0; $n<$bhost2-$bhost1; $n++) {
		    my $nb = $rbhosts[$n];
			if (!$ids{"$bnet1.$nb"}) {
				if (!($interfaces =~ m/$extip.+\n.+inet addr:$bnet1\.$nb/)) {
					$nextip = "$bnet1.$nb";
					last;
				}
			}
		}
	}
	$postreply .= "Status=ERROR No more external IPs available\n" if (!$nextip);
	return $nextip;
}

sub ip2domain {
    my $ip = shift;
    my $ruuid;
    if ($ip) {
        my @regkeys = (tied %register)->select_where("internalip = '$ip' OR externalip = '$ip'");
        foreach my $k (@regkeys) {
            my $valref = $register{$k};
            if ($valref->{'internalip'} eq $ip || $valref->{'externalip'} eq $ip) {
                $ruuid = $valref->{'domains'};
                last;
            }
        }
    }
    return $ruuid;
}

sub getNextInternalIP {
	my $intip = shift;
	my $uuid = shift;
	my $id = shift;
	my $username = shift;
	$username = $user unless ($username);
	my $nextip = "";
	my $intipnum;
	my $subnet;
	my %ids;
    my $ping = Net::Ping->new();

    $id = getNextId() unless ($id);
    my $idleft = ($id>99)?(substr $id,0,-2)+0 : 0;
    my $idright = (substr $id,-2) + 0;
    $intip = "10.$idleft.$idright.0" if (!$intip || $intip eq '--');
    
    return '' unless ($intip =~ m/(\d+\.\d+\.\d+)\.(\d+)/ );
    $subnet = $1;
    $intipnum = $2;

	# First create hash of IP's reserved by other servers in DB
	my @regvalues = values %register;
	foreach my $val (@regvalues) {
    	if ($val->{'user'} eq $username) {
            my $ip = $val->{'internalip'} ;
            $ids{$ip} = $val->{'uuid'};
		}
	}

	if ($intipnum && $intipnum>1 && $intipnum<255) {
	# An internal ip was supplied - check if it's free, if not keep the ip already registered in the db
        if (!$ids{$intip}
#            && !($ping->ping($intip, 0.1)) # 0.1 secs timeout, check if ip is in use, possibly on another engine
            && !(`arping -C1 -c2 -D -I $datanic.$id $intip` =~ /reply from/)  # check if ip is created on another engine
        ) {
            $nextip = $intip;
        } else {
            $nextip = $register{$uuid}->{'internalip'}
        }
	} else {
	# Find first IP not reserved
		for ($n=2; $n<255; $n++) {
			if (!$ids{"$subnet.$n"}
# TODO: The arping check takes too long - two networks created by the same user can too easily be assigned the same IP's
#                && !(`arping -f -c2 -D -I $datanic.$id $subnet.$n` =~ /reply from/)  # check if ip is created on another engine
			) {
                $nextip = "$subnet.$n";
                last;
			}
		}
	}
	$postreply .= "Status=ERROR No more internal IPs available\n" if (!$nextip);
	return $nextip;
}

sub validateStatus {
    my $valref = shift;

    my $interfaces = `/sbin/ifconfig`;
    my $uuid = $valref->{'uuid'};
    my $type = $valref->{'type'};
    my $id = $valref->{'id'};
    my $idleft = ($id>99)?(substr $id,0,-2)+0 : 0;
    my $idright = (substr $id,-2) + 0;

    ( $valref->{'domains'}, $valref->{'domainnames'} ) = getDomains($uuid);
    my ( $systems, $systemnames ) = getSystems($uuid);
    my $extip = $valref->{'externalip'};
    my $intip = $valref->{'internalip'};

    if ($type eq "gateway") {
        $valref->{'internalip'} = "10.$idleft.$idright.1" if ($id>1);
    } else {
        $type = "gateway";
        if ($intip && $intip ne "--" && $extip && $extip ne "--") {
            $type = "ipmapping";
        } elsif ($intip && $intip ne "--") {
            $type = "internalip";
        } elsif ($extip && $extip ne "--") {
            $type = "externalip";
        }
        $valref->{'type'} = $type;
    }

    $valref->{'status'} = "down";
    my $nat;
    if ($id == 0 || $id == 1) {
        $valref->{'status'} = "nat";
    # Check if vlan $id is created (and doing nat)
#    } elsif ($interfaces =~ m/$datanic\.$id.+\n.+10\.$idleft\.$idright\.1/) {
    } elsif (-e "/proc/net/vlan/$datanic.$id") {
        $nat = 1;
    }

    if (($type eq "internalip" || $type eq "ipmapping")) { # && $val->{'domains'}) {
        $valref->{'status'} = "nat" if ($nat);
        my $dhcprunning;
        my $dhcpconfigured;
        eval {
            my $psid;
            $psid = `/bin/cat /var/run/stabile-$id.pid` if (-e "/var/run/stabile-$id.pid");
            chomp $psid;
            $dhcprunning = -e "/proc/$psid" if ($psid);
            my $dhcphosts;
            $dhcphosts = lc `/bin/cat $etcpath/dhcp-hosts-$id` if (-e "$etcpath/dhcp-hosts-$id");
            $dhcpconfigured = ($dhcphosts =~ /$intip/);
            1;
        } or do {;};

        if ($type eq "internalip") {
        # Check if external ip has been created and dhcp is ok
            if ($nat && (($dhcprunning && $dhcpconfigured) || $systems)) {
                $valref->{'status'} = "up";
            }
        } elsif ($type eq "ipmapping") {
        # Check if external ip has been created, dhcp is ok and vlan interface is created
        # An ipmapping linked to a system is considered up if external interface exists
            if ($nat && $interfaces =~ m/$extip/ && (($dhcprunning && $dhcpconfigured) || $systems)) {
                $valref->{'status'} = "up";
            }
        }

    } elsif ($type eq "externalip") {
        my $dhcprunning;
        my $dhcpconfigured;
        eval {
            my $psid;
            $psid = `/bin/cat /var/run/stabile-$id.pid` if (-e "/var/run/stabile-$id.pid");
            chomp $psid;
            $dhcprunning = -e "/proc/$psid" if ($psid);
            my $dhcphosts;
            $dhcphosts = `/bin/cat $etcpath/dhcp-hosts-$id` if (-e "$etcpath/dhcp-hosts-$id");
            $dhcpconfigured = ($dhcphosts =~ /$extip/);
            1;
        } or do {;};

        my $vproxy = `/bin/cat /proc/sys/net/ipv4/conf/$datanic.$id/proxy_arp`; chomp $vproxy;
        my $eproxy = `/bin/cat /proc/sys/net/ipv4/conf/$proxynic/proxy_arp`; chomp $eproxy;
        my $proute = `/sbin/ip route | grep "$extip dev"`; chomp $proute;
        if ($vproxy && $eproxy && $proute) {
            if ((($dhcprunning && $dhcpconfigured) || $systems)) {
                $valref->{'status'} = "up";
            } elsif (!$valref->{'domains'}) {
                $valref->{'status'} = "nat";
            }
        } else {
            #print "$vproxy && $eproxy && $proute && $dhcprunning && $dhcpconfigured :: $extip\n";        
        }

    } elsif ($type eq "gateway") {
        if ($nat || $id == 0 || $id == 1) {$valref->{'status'} = "up";}
    }
    return $valref->{'status'};
}

sub trim{
   my $string = shift;
   $string =~ s/^\s+|\s+$//g;
   return $string;
}

sub overQuotas {
    my $reqips = shift; # number of new ip's we are asking for
	my $usedexternalips = 0;
	my $overquota = 0;
    return $overquota if ($Stabile::userprivileges =~ /a/); # Don't enforce quotas for admins

	my $externalipquota = $userexternalipquota;
	if (!$externalipquota) {
        $externalipquota = $Stabile::config->get('EXTERNAL_IP_QUOTA');
    }

	my $rxquota = $userrxquota;
	if (!$rxquota) {
        $rxquota = $Stabile::config->get('RX_QUOTA');
    }

	my $txquota = $usertxquota;
	if (!$txquota) {
        $txquota = $Stabile::config->get('TX_QUOTA');
    }

    my @regkeys = (tied %register)->select_where("user = '$user'");
	foreach my $k (@regkeys) {
	    my $val = $register{$k};
		if ($val->{'user'} eq $user && $val->{'externalip'} && $val->{'externalip'} ne "--" ) {
		    $usedexternalips += 1;
		}
	}
	if (($usedexternalips + $reqips) > $externalipquota && $externalipquota > 0) { # -1 means no quota
	    $overquota = $usedexternalips;
	} elsif ($rx > $rxquota*1024 && $rxquota > 0) {
	    $overquota = -1;
	} elsif ($tx > $txquota*1024 && $txquota > 0) {
	    $overquota = -2;
	}

	return $overquota;
}

sub updateBilling {
    my $event = shift;
    my %billing;
    my @regkeys = (tied %register)->select_where("user = '$user' or user = 'common'") unless ($fulllist);
    foreach my $k (@regkeys) {
        my $valref = $register{$k};
        my %val = %{$valref}; # Deference and assign to new array, effectively cloning object
        if ($val{'user'} eq $user && ($val{'type'} eq 'ipmapping' || $val{'type'} eq 'externalip') && $val{'externalip'} ne '--') {
            $billing{$val{'id'}}->{'externalip'} += 1;
        }
    }

    my %billingreg;
    my $monthtimestamp = timelocal(0,0,0,1,$mon,$year); #$sec,$min,$hour,$mday,$mon,$year

    unless ( tie(%billingreg,'Tie::DBI', Hash::Merge::merge({table=>'billing_networks', key=>'useridtime'}, $Stabile::dbopts)) ) {return "Unable to access billing register"};

    my $rx_bytes_total = 0;
    my $tx_bytes_total = 0;

    my $prevmonth = $month-1;
    my $prevyear = $year;
    if ($prevmonth == 0) {$prevmonth=12; $prevyear--;};
    $prevmonth = substr("0" . $prevmonth, -2);
    my $prev_rx_bytes_total = 0;
    my $prev_tx_bytes_total = 0;

    foreach my $id (keys %billing) {
        my $b = $billing{$id};
        my $externalip = $b->{'externalip'};
        my $externalipavg = 0;
        my $startexternalipavg = 0;
        my $starttimestamp = $current_time;
        my $rx_bytes = 0;
        my $tx_bytes = 0;
        my $rx_stats = "/sys/class/net/$datanic.$id/statistics/rx_bytes";
        my $tx_stats = "/sys/class/net/$datanic.$id/statistics/tx_bytes";
        $rx_bytes = `/bin/cat $rx_stats` if (-e $rx_stats);
        chomp $rx_bytes;
        $tx_bytes = `/bin/cat $tx_stats` if (-e $tx_stats);
        chomp $tx_bytes;

        if ($current_time - $monthtimestamp < 4*3600) {
            $starttimestamp = $monthtimestamp;
            $externalipavg = $externalip;
            $startexternalipavg = $externalip;
        }

        my $bill = $billingreg{"$user-$id-$year-$month"};
        my $regrx_bytes = $bill->{'rx'};
        my $regtx_bytes = $bill->{'tx'};
        $rx_bytes += $regrx_bytes if ($regrx_bytes > $rx_bytes); # Network interface was reloaded
        $tx_bytes += $regtx_bytes if ($regtx_bytes > $tx_bytes); # Network interface was reloaded

        # Update timestamp and averages on existing row
        if ($billingreg{"$user-$id-$year-$month"}) {
            $startexternalipavg = $bill->{'startexternalipavg'};
            $starttimestamp = $bill->{'starttimestamp'};

            $externalipavg = ($startexternalipavg*($starttimestamp - $monthtimestamp) + $externalip*($current_time - $starttimestamp)) /
                            ($current_time - $monthtimestamp);

            $billingreg{"$user-$id-$year-$month"}->{'externalip'} = $externalip;
            $billingreg{"$user-$id-$year-$month"}->{'externalipavg'} = $externalipavg;
            $billingreg{"$user-$id-$year-$month"}->{'timestamp'} = $current_time;
            $billingreg{"$user-$id-$year-$month"}->{'rx'} = $rx_bytes;
            $billingreg{"$user-$id-$year-$month"}->{'tx'} = $tx_bytes;
        }

        # No row found or something happened which justifies writing a new row
        if (!$billingreg{"$user-$id-$year-$month"}
        || ($b->{'externalip'} != $bill->{'externalip'})
        ) {

            my $inc = 0;
            if ($billingreg{"$user-$id-$year-$month"}) {
                $startexternalipavg = $externalipavg;
                $starttimestamp = $current_time;
                $inc = $bill->{'inc'};
            }
            # Write a new row
            $billingreg{"$user-$id-$year-$month"} = {
                externalip=>$externalip+0,
                externalipavg=>$externalipavg,
                startexternalipavg=>$startexternalipavg,
                timestamp=>$current_time,
                starttimestamp=>$starttimestamp,
                event=>$event,
                inc=>$inc+1,
                rx=>$rx_bytes,
                tx=>$tx_bytes
            };
        }

        $rx_bytes_total += $rx_bytes;
        $tx_bytes_total += $tx_bytes;
        my $prevbill = $billingreg{"$user-$id-$prevyear-$prevmonth"};
        $prev_rx_bytes_total += $prevbill->{'rx'};
        $prev_tx_bytes_total += $prevbill->{'tx'};
    }
    untie %billingreg;
    $rx = ($rx_bytes_total>$prev_rx_bytes_total)?$rx_bytes_total - $prev_rx_bytes_total:$rx_bytes_total;
    $tx = ($tx_bytes_total>$prev_tx_bytes_total)?$tx_bytes_total - $prev_tx_bytes_total:$tx_bytes_total;
    my $oq = overQuotas();
    if ($oq) {
        foreach my $id (keys %billing) {
            $main::syslogit->($user, 'info', "$user over rx/tx quota ($oq) stopping network $id");
            Stop($id, 'stop');
        }
    }
}

sub Bit2netmask {
	my $netbit = shift;
	my $_bit         = ( 2 ** (32 - $netbit) ) - 1;
	my ($full_mask)  = unpack( "N", pack( "C4", split(/./, '255.255.255.255') ) );
	my $netmask      = join( '.', unpack( "C4", pack( "N", ( $full_mask ^ $_bit ) ) ) );
	return $netmask;
}
