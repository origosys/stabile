#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license

package Stabile::Servers;

use Error qw(:try);
use Data::UUID;
use Proc::Daemon;
use File::Basename;
use lib dirname (__FILE__);
use File::Basename;
use lib dirname (__FILE__);
use Stabile;
#use Encode::Escape;

$\ = ''; # Some of the above seems to set this to \n, resulting in every print appending a line feed

$cpuovercommision = $Stabile::config->get('CPU_OVERCOMMISION') || 1;
$dpolicy = $Stabile::config->get('DISTRIBUTION_POLICY') || 'disperse'; #"disperse" or "pack"
$amtpasswd = $Stabile::config->get('AMT_PASSWD') || "";
$brutalsleep = $Stabile::config->get('BRUTAL_SLEEP') || "";
$sshcmd = $sshcmd || $Stabile::sshcmd;

my %ahash; # A hash of accounts and associated privileges current user has access to

#my %options=();
#Getopt::Std::getopts("a:hfu:m:k:", \%options); # -a action -h help -f full-list (all users) -u uuid -m match pattern -k keywords

try {
    Init(); # Perform various initalization tasks
    process() if ($package);

    if ($action || %params) {
    	untie %register;
    	untie %networkreg;
        untie %nodereg;
        untie %xmlreg;
    }

} catch Error with {
	my $ex = shift;
    print $Stabile::q->header('text/html', '500 Internal Server Error') unless ($console);
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
    $uuid = $curuuid if ($uuid eq 'this');
    my $obj;
    $action = $action || $h{'action'};

    if ($h{'action'} eq 'destroy' || $action eq 'destroy' || $action eq 'attach' || $action eq 'detach' || $action =~ /changepassword|sshaccess/) {
        $obj = \%h;
        return $obj;
    }

    # Allow specifying nicmac1 instead of uuid if known
    if (!$uuid) {
        $uuid = nicmac1ToUuid($h{"nicmac1"});
    }
    my $status = 'new';
    $status = $register{$uuid}->{'status'} if ($register{$uuid});

    my $objaction = lc $h{"action"};
    $objaction = "" if ($status eq "new");

    if ((!$uuid) && $status eq 'new') {
        my $ug = new Data::UUID;
        $uuid = $ug->create_str();
        if ($uripath =~ /servers(\.cgi)?\/(.+)/) {
            my $huuid = $2;
            if ($ug->to_string($ug->from_string($huuid)) eq $huuid) { # Check for valid uuid
                $uuid = $huuid;
            }
        }
    };
    unless ($uuid && length $uuid == 36) {
        $posterror .= "Status=Error Invalid uuid.\n";
        return;
    }

    my $dbobj = $register{$uuid} || {};

    my $name = $h{"name"} || $dbobj->{'name'};
    utf8::decode($name);
    my $memory = $h{"memory"} || $dbobj->{'memory'};
    my $vcpu = $h{"vcpu"} || $dbobj->{'vcpu'};
    my $boot = $h{"boot"} || $dbobj->{'boot'};
    my $image = $h{"image"} || $dbobj->{'image'};
    my $imagename = $h{"imagename"} || $dbobj->{'imagename'};
    if ($image && $image ne '--' && !($image =~ /^\//)) { # Image is registered by uuid - we find the path
        unless ( tie(%imagereg2,'Tie::DBI', Hash::Merge::merge({table=>'images', CLOBBER=>1}, $Stabile::dbopts)) ) {$posterror = "Unable to access image uuid register"; return;};
        $image = $imagereg2{$image}->{'path'};
        $imagename = $imagereg2{$image}->{'name'};
        untie %imagereg2;
        return unless ($image);
    }
    my $image2 = $h{"image2"} || $dbobj->{'image2'};
    my $image3 = $h{"image3"} || $dbobj->{'image3'};
    my $image4 = $h{"image4"} || $dbobj->{'image4'};
    my $image2name = $h{"image2name"} || $dbobj->{'image2name'};
    my $image3name = $h{"image3name"} || $dbobj->{'image3name'};
    my $image4name = $h{"image4name"} || $dbobj->{'image4name'};
    if ($image2 && $image2 ne '--' && !($image2 =~ /^\//)) { # Image2 is registered by uuid - we find the path
        unless ( tie(%imagereg2,'Tie::DBI', Hash::Merge::merge({table=>'images', CLOBBER=>1}, $Stabile::dbopts)) ) {$postreply = "Unable to access image uuid register"; return $postreply;};
        $image2 = $imagereg2{$image2}->{'path'};
        $image2name = $imagereg2{$image2}->{'name'};
        untie %imagereg2;
    }
    my $diskbus = $h{"diskbus"} || $dbobj->{'diskbus'};
    my $diskdev = "vda";
    my $diskdev2 = "vdb";
    my $diskdev3 = "vdc";
    my $diskdev4 = "vdd";
    if ($diskbus eq "ide") {$diskdev = "hda"; $diskdev2 = "hdb"; $diskdev3 = "hdc"; $diskdev4 = "hdd"};
    my $cdrom = $h{"cdrom"} || $dbobj->{'cdrom'};
    if ($cdrom && $cdrom ne '--' && !($cdrom =~ /^\//)) {
        unless ( tie(%imagereg2,'Tie::DBI', Hash::Merge::merge({table=>'images', CLOBBER=>1}, $Stabile::dbopts)) ) {$postreply = "Unable to access image uuid register"; return $postreply;};
        $cdrom = $imagereg2{$cdrom}->{'path'};
        untie %imagereg2;
    }

    my $networkuuid1 = $h{"networkuuid1"} || $dbobj->{'networkuuid1'};
    if ($h{"networkuuid1"} eq "0") {$networkuuid1 = "0"}; #Stupid perl... :-)
    my $networkid1 = $h{"networkid1"} || $dbobj->{'networkid1'};
    my $networkname1 = $h{"networkname1"} || $dbobj->{'networkname1'};
    my $nicmodel1 = $h{"nicmodel1"} || $dbobj->{'nicmodel1'};
    my $nicmac1 = $h{"nicmac1"} || $dbobj->{'nicmac1'};
    if (!$nicmac1 || $nicmac1 eq "--") {$nicmac1 = randomMac();}

    my $networkuuid2 = $h{"networkuuid2"} || $dbobj->{'networkuuid2'};
    if ($h{"networkuuid2"} eq "0") {$networkuuid2 = "0"};
    my $networkid2 = $h{"networkid2"} || $dbobj->{'networkid2'};
    my $networkname2 = $h{"networkname2"} || $dbobj->{'networkname2'};
    my $nicmac2 = $h{"nicmac2"} || $dbobj->{'nicmac2'};
    if (!$nicmac2 || $nicmac2 eq "--") {$nicmac2 = randomMac();}

    my $networkuuid3 = $h{"networkuuid3"} || $dbobj->{'networkuuid3'};
    if ($h{"networkuuid3"} eq "0") {$networkuuid3 = "0"};
    my $networkid3 = $h{"networkid3"} || $dbobj->{'networkid3'};
    my $networkname3 = $h{"networkname3"} || $dbobj->{'networkname3'};
    my $nicmac3 = $h{"nicmac3"} || $dbobj->{'nicmac3'};
    if (!$nicmac3 || $nicmac3 eq "--") {$nicmac3 = randomMac();}

    my $action = $h{"action"};
    my $notes = $h{"notes"};
    $notes = $dbobj->{'notes'} if (!$notes || $notes eq '--');
    my $reguser = $dbobj->{'user'};
    my $autostart = ($h{"autostart"} ."") || $dbobj->{'autostart'};
    if ($autostart && $autostart ne "false") {$autostart = "true";}
    my $locktonode = ($h{"locktonode"} ."") || $dbobj->{'locktonode'};
    if ($locktonode && $locktonode ne "false") {$locktonode = "true";}
    my $mac;
    $mac = $dbobj->{'mac'} unless ($objaction eq 'start');
#    $mac = $h{"mac"} if ($isadmin && $locktonode eq 'true' && $h{"mac"});
    $mac = $h{"mac"} if ($isadmin && $h{"mac"});
    my $domuser = $h{"user"} || $user; # Set if user is trying to move server to another account

    # Sanity checks
    if (
        ($name && length $name > 255)
            || ($networkuuid1<0)
            || ($networkuuid2<0)
            || ($networkuuid3<0)
            || ($networkuuid1>1 && length $networkuuid1 != 36)
            || ($networkuuid2>1 && length $networkuuid2 != 36)
            || ($networkuuid3>1 && length $networkuuid3 != 36)
            || ($image && length $image > 255)
            || ($imagename && length $imagename > 255)
            || ($image2 && length $image2 > 255)
            || ($image3 && length $image3 > 255)
            || ($image4 && length $image4 > 255)
            || ($image2name && length $image2name > 255)
            || ($image3name && length $image3name > 255)
            || ($image4name && length $image4name > 255)
            || ($cdrom && length $cdrom > 255)
            || ($memory && ($memory<64 || $memory >1024*32))
    ) {
        $postreply .= "Status=ERROR Missing server data: $name\n";
        return 0;
    }

    # Security check
    if ($status eq 'new' && (($action && $action ne '--' && $action ne 'save') || !$image || $image eq '--')) {
        $postreply .= "Status=ERROR Bad server data: $name\n";
        $postmsg = "Bad server data";
        return 0;
    }
    if (!$reguser && $status ne 'new'
        && !($name && $memory && $vcpu && $boot && $image && $diskbus && $networkuuid1 && $nicmodel1)) {
        $posterror .= "Status=ERROR Insufficient data: $name\n";
        return 0;
    }
    if (!$isadmin) {
        if (($networkuuid1>1 && $networkreg{$networkuuid1}->{'user'} ne $user)
            || ($networkuuid2>1 && $networkreg{$networkuuid2}->{'user'} ne $user)
            || ($networkuuid3>1 && $networkreg{$networkuuid3}->{'user'} ne $user)
        )
        {
            $postreply .= "Status=ERROR No privileges: $networkname1 $networkname2\n";
            return 0;
        }
        if ((($user ne $reguser) && $action ) || ($reguser && $status eq "new"))
        {
            $postreply .= "Status=ERROR No privileges: $name\n";
            return 0;
        }
        if (!($image =~ /\/$user\//)
            || ($image2 && $image2 ne "--" && !($image2 =~ /\/$user\//))
            || ($image3 && $image3 ne "--" && !($image3 =~ /\/$user\//))
            || ($image4 && $image4 ne "--" && !($image4 =~ /\/$user\//))
        )
        {
            $postreply .= "Status=ERROR No image privileges: $name\n";
            return 0;
        }
    }

    # No action - regular save of domain properties
    $cdrom = '--' if ($cdrom eq 'virtio');

    $obj = {
        uuid => $uuid,
        status => $status,
        name => $name,
        memory => $memory,
        vcpu => $vcpu,
        image => $image,
        imagename => $imagename,
        image2 => $image2,
        image2name => $image2name,
        image3 => $image3,
        image3name => $image3name,
        image4 => $image4,
        image4name => $image4name,
        diskbus => $diskbus,
        cdrom => $cdrom,
        boot => $boot,
        networkuuid1 => $networkuuid1,
        networkid1 => $networkid1,
        networkname1 => $networkname1,
        nicmodel1 => $nicmodel1,
        nicmac1 => $nicmac1,
        networkuuid2 => $networkuuid2,
        networkid2 => $networkid2,
        networkname2 => $networkname2,
        nicmac2 => $nicmac2,
        networkuuid3 => $networkuuid3,
        networkid3 => $networkid3,
        networkname3 => $networkname3,
        nicmac3 => $nicmac3,
        notes => $notes,
        autostart => $autostart,
        locktonode => $locktonode,
        mac => $mac,
        user => $domuser
    };
    return $obj;
}

sub Init {
    # Tie database tables to hashes
    unless ( tie(%register,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access image register"};
    unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {return "Unable to access network register"};
    unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac'}, $Stabile::dbopts)) ) {return "Unable to access nodes register"};
    unless ( tie(%xmlreg,'Tie::DBI', Hash::Merge::merge({table=>'domainxml'}, $Stabile::dbopts)) ) {return "Unable to access domainxml register"};

    # simplify globals initialized in Stabile.pm
    $tktuser = $tktuser || $Stabile::tktuser;
    $user = $user || $Stabile::user;
    $isadmin = $isadmin || $Stabile::isadmin;
    $privileges = $privileges || $Stabile::privileges;

    # Create aliases of functions
    *header = \&CGI::header;
    *to_json = \&JSON::to_json;

    *Showautostart = \&Autostartall;

    *do_save = \&Save;
    *do_tablelist = \&do_list;
    *do_jsonlist = \&do_list;
    *do_showautostart = \&action;
    *do_autostartall = \&privileged_action;
    *do_help = \&action;

    *do_start = \&privileged_action;
    *do_destroy = \&action;
    *do_shutdown = \&action;
    *do_suspend = \&action;
    *do_resume = \&action;
    *do_remove = \&privileged_action;
    *do_move = \&action;
    *do_mountcd = \&action;
    *do_changepassword = \&privileged_action;
    *do_sshaccess = \&privileged_action;

    *do_gear_start = \&do_gear_action;
    *do_gear_autostart = \&do_gear_action;
    *do_gear_showautostart = \&do_gear_action;
    *do_gear_autostartall = \&do_gear_action;
    *do_gear_remove = \&do_gear_action;
    *do_gear_changepassword = \&do_gear_action;
    *do_gear_sshaccess = \&do_gear_action;

}

sub do_list {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:uuid:
List servers current user has access to.
END
    }

    my $res;
    my $filter;
    my $statusfilter;
    my $uuidfilter;
    my $curserv = $register{$curuuid};
    if ($curuuid && ($isadmin || $curserv->{'user'} eq $user) && $uripath =~ /servers(\.cgi)?\/(\?|)(this)/) {
        $uuidfilter = $curuuid;
    } elsif ($uripath =~ /servers(\.cgi)?\/(\?|)(name|status)/) {
        $filter = $3 if ($uripath =~ /servers(\.cgi)?\/\??name(:|=)(.+)/);
        $filter = $1 if ($filter =~ /(.*)\*$/);
        $statusfilter = $4 if ($uripath =~ /servers(\.cgi)?\/\??(.+ AND )?status(:|=)(\w+)/);
    } elsif ($uripath =~ /servers(\.cgi)?\/(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})/) {
        $uuidfilter = $2;
    }
    $filter = $1 if ($filter =~ /(.*)\*/);

    my $sysuuid;
    if ($params{'system'}) {
        $sysuuid = $params{'system'};
        $sysuuid = $cursysuuid || $curuuid if ($params{'system'} eq 'this');
    }
    my @curregvalues;
    my @regkeys;
    if ($fulllist && $isadmin) {
        @regkeys = keys %register;
    } elsif ($uuidfilter && $isadmin) {
        @regkeys = (tied %register)->select_where("uuid = '$uuidfilter'");
    } elsif ($sysuuid) {
        @regkeys = (tied %register)->select_where("system = '$sysuuid' OR uuid = '$sysuuid'");
    } else {
        @regkeys = (tied %register)->select_where("user = '$user'");
    }

    unless (tie(%sysreg,'Tie::DBI', Hash::Merge::merge({table=>'systems'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access systems register"}|; return $res;};
    unless (tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access images register"}|; return $res;};

    foreach my $k (@regkeys) {
        $valref = $register{$k};
        # Only include VM's belonging to current user (or all users if specified and user is admin)
        if ($user eq $valref->{'user'} || $fulllist || ($uuidfilter && $isadmin)) {
            next unless (!$sysuuid || $valref->{'system'} eq $sysuuid || $valref->{'uuid'} eq $sysuuid);

            my $validatedref = validateItem($valref);
            my %val = %{$validatedref}; # Deference and assign to new ass array, effectively cloning object
            $val{'memory'} += 0;
            $val{'vcpu'} += 0;
            $val{'nodetype'} = 'parent';
            $val{'internalip'} = $networkreg{$val{'networkuuid1'}}->{'internalip'};
            $val{'self'} = 1 if ($curuuid && $curuuid eq $val{'uuid'});
            if ($action eq 'treelist') {
                if ($val{'system'} && $val{'system'} ne '') {
                    my $sysuuid = $val{'system'};
                    my $sysname = $sysreg{$sysuuid}->{'name'};
                    if (!$sysname) {
                        $sysname = $1 if ($sysname =~ /(.+)\..*/);
                        $sysname = $val{'name'};
                        $sysname =~ s/server/System/i;
                    }
                    $sysreg{$sysuuid} = {
                        uuid => $sysuuid,
                        name => $sysname,
                        user => 'irigo'
                    };

                    my %pval = %{$sysreg{$sysuuid}};
                    $pval{'nodetype'} = 'parent';
                    $pval{'status'} = '--';
                    $val{'nodetype'} = 'child';

                    my @children;
                    push @children,\%val;
                    $pval{'children'} = \@children;
                    push @curregvalues,\%pval;
                } else {
                    push @curregvalues,\%val;
                }
            } elsif ($filter || $statusfilter || $uuidfilter) { # List filtered servers
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
            } else {
                push @curregvalues,\%val;
            }
        }
    }
    tied(%sysreg)->commit;
    untie(%sysreg);
    untie %imagereg;
    @curregvalues = (sort {$a->{'status'} cmp $b->{'status'}} @curregvalues); # Sort by status

    # Sort @curregvalues
    @curregvalues = (sort {$b->{'name'} <=> $a->{'name'}} @curregvalues); # Always sort by name first
    my $sort = 'status';
    $sort = $2 if ($uripath =~ /sort\((\+|\-)(\S+)\)/);
    my $reverse;
    $reverse = 1 if ($1 eq '-');
    if ($reverse) { # sort reverse
        if ($sort =~ /memory|vcpu/) {
            @curregvalues = (sort {$b->{$sort} <=> $a->{$sort}} @curregvalues); # Sort as number
        } else {
            @curregvalues = (sort {$b->{$sort} cmp $a->{$sort}} @curregvalues); # Sort as string
        }
    } else {
        if ($sort =~ /memory|vcpu/) {
            @curregvalues = (sort {$a->{$sort} <=> $b->{$sort}} @curregvalues); # Sort as number
        } else {
            @curregvalues = (sort {$a->{$sort} cmp $b->{$sort}} @curregvalues); # Sort as string
        }
    }

    if ($action eq 'tablelist') {
        my $t2;

        if ($isadmin) {
            $t2 = Text::SimpleTable->new(36,20,20,10,10,12,7);
            $t2->row('uuid', 'name', 'imagename', 'memory', 'user', 'mac', 'status');
        } else {
            $t2 = Text::SimpleTable->new(36,20,20,10,10,7);
            $t2->row('uuid', 'name', 'imagename', 'memory', 'user', 'status');
        }
        $t2->hr;
        my $pattern = $options{m};
        foreach $rowref (@curregvalues){
            if ($pattern) {
                my $rowtext = $rowref->{'uuid'} . " " . $rowref->{'name'} . " " . $rowref->{'imagename'} . " " . $rowref->{'memory'}
                    . " " .  $rowref->{'user'} . " " . $rowref->{'status'};
                $rowtext .= " " . $rowref->{'mac'} if ($isadmin);
                next unless ($rowtext =~ /$pattern/i);
            }
            if ($isadmin) {
                $t2->row($rowref->{'uuid'}, $rowref->{'name'}, $rowref->{'imagename'}, $rowref->{'memory'},
                    $rowref->{'user'}, $rowref->{'mac'}, $rowref->{'status'});
            } else {
                $t2->row($rowref->{'uuid'}, $rowref->{'name'}, $rowref->{'imagename'}, $rowref->{'memory'},
                    $rowref->{'user'}, $rowref->{'status'});
            }
        }
        $res .= $t2->draw;
    } elsif ($console) {
        $res .= Dumper(\@curregvalues);
    } else {
        my $json_text;
        if ($uuidfilter && @curregvalues) {
            $json_text = to_json($curregvalues[0], {pretty => 1});
        } else {
            $json_text = to_json(\@curregvalues, {pretty => 1});
        }

        $json_text =~ s/\x/ /g;
        $json_text =~ s/\"\"/"--"/g;
        $json_text =~ s/null/"--"/g;
        $json_text =~ s/"autostart":"true"/"autostart":true/g;
        $json_text =~ s/"autostart":"--"/"autostart":false/g;
        $json_text =~ s/"locktonode":"true"/"locktonode":true/g;
        $json_text =~ s/"locktonode":"--"/"locktonode":false/g;
        if ($action eq 'jsonlist' || $action eq 'list' || !$action) {
            $res .= $json_text;
        } else {
            $res .= qq|{"action": "$action", "identifier": "uuid", "label": "uuid", "items" : $json_text}|;
        }
    }
    return $res;
}

sub do_uuidshow {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:uuid:
Simple action for showing a single server.
END
    }
    my $res;
    $res .= $Stabile::q->header('text/plain') unless $console;
    my $u = $uuid || $options{u};
    if ($u || $u eq '0') {
        foreach my $uuid (keys %register) {
            if (($register{$uuid}->{'user'} eq $user || $register{$uuid}->{'user'} eq 'common' || $isadmin)
                && $uuid =~ /^$u/) {
                my %hash = %{$register{$uuid}};
                delete $hash{'action'};
                my $dump = Dumper(\%hash);
                $dump =~ s/undef/"--"/g;
                $res .= $dump;
                last;
            }
        }
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
        my $match;
        foreach my $uuid (keys %register) {
            if ($uuid =~ /^$u/) {
                $ruuid = $uuid if ($register{$uuid}->{'user'} eq $user || index($privileges,"a")!=-1);
                $match = 1;
                last;
            }
        }
        if (!$match && $isadmin) { # If no match and user is admin, do comprehensive lookup
            foreach my $uuid (keys %register) {
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

sub do_destroyuserservers {
    if ($help) {
        return <<END
GET::
Simple action for destroying all servers belonging to a user
END
    }
    my $res;
    $res .= $Stabile::q->header('text/plain') unless $console;
    destroyUserServers($user);
    $res .= $postreply;
    return $res;
}

sub do_removeuserservers {
    if ($help) {
        return <<END
GET::
Simple action for removing all servers belonging to a user
END
    }
    my $res;
    $res .= $Stabile::q->header('text/plain') unless $console;
    removeUserServers($user);
    $res .= $postreply;
    return $res;
}

sub do_getappid {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:uuid:
Simple action for getting the app id
END
    }
    my $res;
    $res .= $Stabile::q->header('text/plain') unless $console;
    $uuid = $uuid || $options{u};
    $uuid = $curuuid unless ($uuid);
    if ($uuid && $register{$uuid}) {
        unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {return "Unable to access image register"};
        $res .= "appid: ". $imagereg{$register{$uuid}->{image}}->{appid}, "\n";
        untie %imagereg;
    }
    return $res;
}

sub do_setrunning {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:uuid:
Simple action for setting status back to running after e.g. an upgrade
END
    }
    my $res;
    $res .= $Stabile::q->header('text/plain') unless $console;
    $uuid = $uuid || $options{u};
    $uuid = $curuuid unless ($uuid);
    if ($uuid && $register{$uuid}) {
        $register{$uuid}->{'status'} = 'running';
        $main::updateUI->({ tab => 'servers',
            user                => $user,
            uuid                => $uuid,
            status              => 'running' })

    };
    $res .= "Status=OK Set status of $register{$uuid}->{'name'} to running\n";
    return $res;
}

sub do_getappinfo {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET:uuid:
Simple action for getting the apps basic info
END
    }
    my $res;
    $res .= $Stabile::q->header('application/json') unless $console;
    $uuid = $uuid || $options{u};
    $uuid = $curuuid unless ($uuid);
    my %appinfo;
    if ($uuid && $register{$uuid}) {
        unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {return "Unable to access image register"};
        $appinfo{'appid'} = $imagereg{$register{$uuid}->{image}}->{appid} || '';
        $appinfo{'managementlink'} = $imagereg{$register{$uuid}->{image}}->{managementlink} || '';
        $appinfo{'managementlink'} =~ s/{uuid}/$register{$uuid}->{networkuuid1}/;

        my $termlink = $imagereg{$register{$uuid}->{image}}->{terminallink} || '';
        $termlink =~ s/{uuid}/$register{$uuid}->{networkuuid1}/;
        my $burl = $baseurl;
        $burl = $1 if ($termlink =~ /\/stabile/ && $baseurl =~ /(.+)\/stabile/); # Unpretty, but works for now
        # $termlink = $1 if ($termlink =~ /\/(.+)/);
        # $termlink = "$burl/$termlink" unless ($termlink =~ /^http/ || !$termlink); # || $termlink =~ /^\//
        $appinfo{'terminallink'} = $termlink;

        $appinfo{'upgradelink'} = $imagereg{$register{$uuid}->{image}}->{upgradelink} || '';
        $appinfo{'upgradelink'} =~ s/{uuid}/$register{$uuid}->{networkuuid1}/;
        $appinfo{'version'} = $imagereg{$register{$uuid}->{image}}->{version} || '';
        $appinfo{'status'} = $register{$uuid}->{status} || '';
        $appinfo{'name'} = $register{$uuid}->{name} || '';
        $appinfo{'system'} = $register{$uuid}->{system} || '';

        if ($appinfo{'system'}) {
            unless (tie(%sysreg,'Tie::DBI', Hash::Merge::merge({table=>'systems'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access systems register"}|; return $res;};
            $appinfo{'systemname'} = $sysreg{$appinfo{'system'}}->{name} || '';
            untie(%sysreg);
        } else {
            $appinfo{'systemname'} = $appinfo{'name'};
        }


        if ($appinfo{'appid'}) {
            my @regkeys = (tied %imagereg)->select_where("appid = '$appinfo{appid}'");
            foreach my $k (@regkeys) {
                my $imgref = $imagereg{$k};
                if ($imgref->{'path'} =~ /\.master\.qcow2$/ && $imgref->{'appid'} eq $appinfo{'appid'}
                     && $imgref->{'installable'} && $imgref->{'installable'} ne 'false'
                ) {
                    if ($imgref->{'version'} > $appinfo{'currentversion'}) {
                        $appinfo{'currentversion'} = $imgref->{'version'};
                        $appinfo{'appname'} = $imgref->{'name'};
                    }
                }
            }
        }

        untie %imagereg;
    }
    $appinfo{'appstoreurl'} = $appstoreurl;
    $appinfo{'dnsdomain'} = ($enginelinked)?$dnsdomain:'';
    $appinfo{'dnssubdomain'} = ($enginelinked)?substr($engineid, 0, 8):'';
    $appinfo{'uuid'} = $uuid;
    $appinfo{'user'} = $user;
    $appinfo{'remoteip'} = $remoteip;
    $res .= to_json(\%appinfo, { pretty => 1 });
    return $res;
}

sub do_removeserver {
    if ($help) {
        return <<END
GET:uuid:
Simple action for destroying and removing a single server
END
    }
    my $res;
    $res .= $Stabile::q->header('text/plain') unless $console;
    if ($curuuid) {
        removeUserServers($user, $curuuid, 1);
    }
    else {
        $postreply .= "Status=Error Unable to uninstall\n";
    }
    $res .= $postreply;
    return $res;
}

sub do_updateregister {
    if ($help) {
        return <<END
GET::
Update server register
END
    }
    my $res;
    $res .= $Stabile::q->header('text/plain') unless $console;
    return unless $isadmin;
    updateRegister();
    $res .= "Status=OK Updated server registry for all users\n";
    return $res;
}

sub Autostartall {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
GET::
Start all servers marked for autostart. When called as showautostart only shows which would be started.
END
    }
    my $res;
    $res .= $Stabile::q->header('text/plain') unless $console;
    my $mes;
    return $res if ($isreadonly);

    # Wait for all pistons to be online
    my $nodedown;
    my $nodecount;
    for (my $i = 0; $i < 10; $i++) {
        $nodedown = 0;
        foreach my $node (values %nodereg) {
            if ($node->{'status'} ne 'running' && $node->{'status'} ne 'maintenance') {
                $nodedown = 1;
            }
            else {
                $nodecount++ unless ($node->{'status'} eq 'maintenance');
            }
        }
        if ($nodedown) {
            # Wait and see if nodes come online
            $mes = "Waiting for nodes...(" . (10 - $i) . ")\n";
            print $mes if ($console);
            $res .= $mes;
            sleep 5;
        }
        else {
            last;
        }
    }

    if (!%nodereg || $nodedown || !$nodecount) {
        $mes = "Not autostarting servers - not all nodes ready!\n";
        print $mes if ($console);
        $res .= $mes;
    }
    else {
        $mes = "$nodecount nodes ready - autostarting servers...\n";
        print $mes if ($console);
        $res .= $mes;
        if ($action eq "showautostart") {
            $mes = "Only showing which servers would be starting!\n";
            print $mes if ($console);
            $res .= $mes;
        }

        $Stabile::Networks::user = $user;
        require "$Stabile::basedir/cgi/networks.cgi";
        $Stabile::Networks::console = 1;

        foreach my $dom (values %register) {
            if ($dom->{'autostart'} eq '1' || $dom->{'autostart'} eq 'true') {
                $res .= "Checking if $dom->{'name'} ($dom->{'user'}, $dom->{'uuid'}) should be started\n";
                my $networkstatus1 = $networkreg{$dom->{'networkuuid1'}}->{status};
                my $networkstatus2 = ($networkreg{$dom->{'networkuuid2'}})?$networkreg{$dom->{'networkuuid2'}}->{status}:'';
                my $networkstatus3 = ($networkreg{$dom->{'networkuuid3'}})?$networkreg{$dom->{'networkuuid3'}}->{status}:'';
                my @dnets;
                push @dnets, $dom->{'networkuuid1'} if ($dom->{'networkuuid1'} && $dom->{'networkuuid1'} ne '--' && $networkstatus1 ne 'up');
                push @dnets, $dom->{'networkuuid2'} if ($dom->{'networkuuid2'} && $dom->{'networkuuid2'} ne '--' && $networkstatus2 ne 'up');
                push @dnets, $dom->{'networkuuid3'} if ($dom->{'networkuuid3'} && $dom->{'networkuuid3'} ne '--' && $networkstatus3 ne 'up');
                my $i;
                for ($i=0; $i<5; $i++) { # wait for status newer than 10 secs
                    validateItem($dom);
                    last if (time() - $dom->{timestamp} < 10);
                    $mes = "Waiting for newer timestamp, current is " . (time() - $dom->{timestamp}) . " old\n";
                    print $mes if ($console);
                    $res .= $mes;
                    sleep 2;
                }
                if (
                    $dom->{'status'} eq 'shutoff' || $dom->{'status'} eq 'inactive'
                ) {
                    if ($action eq "showautostart") { # Dry run
                        $mes = "Starting $dom->{'name'} ($dom->{'user'}, $dom->{'uuid'})\n";
                        print $mes if ($console);
                        $res .= $mes;
                    }
                    else {
                        $mes = "Starting $dom->{'name'} ($dom->{'user'}, $dom->{'uuid'})\n";
                        print $mes if ($console);
                        $res .= $mes;
                        $postreply = Start($dom->{'uuid'});
                        print $postreply if ($console);
                        $res .= $postreply;
#                        $mes = `REMOTE_USER=$dom->{'user'} $base/cgi/servers.cgi -a start -u $dom->{'uuid'}`;
                        print $mes if ($console);
                        $res .= $mes;
                        sleep 1;
                    }
                }
                elsif (@dnets) {
                    if ($action eq "showautostart") { # Dry run
                        foreach my $networkuuid (@dnets) {
                            $mes = "Would bring network $networkreg{$networkuuid}->{name} up for $dom->{'name'} ($dom->{'user'}, $dom->{'uuid'})\n";
                            print $mes if ($console);
                            $res .= $mes;
                        }
                    }
                    else {
                        foreach my $networkuuid (@dnets) {
                            $mes = "Bringing network $networkreg{$networkuuid}->{name} up for $dom->{'name'} ($dom->{'user'}, $dom->{'uuid'})\n";
                            print $mes if ($console);
                            $res .= $mes;
                            $mes = Stabile::Networks::Activate($networkuuid, 'activate');
                            print $mes if ($console);
                            $res .= $mes;
                            sleep 1;
                        }
                    }
                }
            } else {
                $res .= "Not marked for autostart $dom->{'name'} ($dom->{'user'}, $dom->{'uuid'})\n";
            }
        }
    }
    return $res;
}

sub do_listnodeavailability {
    if ($help) {
        return <<END
GET::
Utility call - only informational. Shows availability of nodes for starting servers.
END
    }
    my $res;
    $res .= $Stabile::q->header('application/json') unless ($console);
    my ($temp1, $temp2, $temp3, $temp4, $ahashref) = locateTargetNode();
    my @avalues = values %$ahashref;
    my @sorted_values = (sort {$b->{'index'} <=> $a->{'index'}} @avalues);
    $res .= to_json(\@sorted_values, { pretty => 1 });
    return $res;
}

sub do_listbillingdata {
    if ($help) {
        return <<END
GET::
List current billing data.
END
    }
    my $res;
    $res .= $Stabile::q->header('application/json') unless ($console);
    my $buser = URI::Escape::uri_unescape($params{'user'}) || $user;
    my %b;
    my @bmonths;
    if ($isadmin || $buser eq $user) {
        my $bmonth = URI::Escape::uri_unescape($params{'month'}) || $month;
        my $byear = URI::Escape::uri_unescape($params{'year'}) || $year;
        if ($bmonth eq "all") {
            @bmonths = ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12");
        }
        else {
            @bmonths = ($bmonth);
        }

        unless ( tie(%billingreg,'Tie::DBI', Hash::Merge::merge({table=>'billing_domains', key=>'usernodetime'}, $Stabile::dbopts)) ) {return "Unable to access billing register"};

        my @nkeys = keys %nodereg;
        foreach my $bm (@bmonths) {
            my $vcpuavg = 0;
            my $memoryavg = 0;
            foreach my $nmac (@nkeys) {
                $vcpuavg += $billingreg{"$buser-$nmac-$byear-$bm"}->{'vcpuavg'};
                $memoryavg += $billingreg{"$buser-$nmac-$byear-$bm"}->{'memoryavg'};
            }
            $b{"$buser-$byear-$bm"} = {
                id        => "$buser-$byear-$bm",
                vcpuavg   => $vcpuavg,
                memoryavg => $memoryavg,
                month     => $bm + 0,
                year      => $byear + 0
            }
        }
        untie %billingreg;
    }
    my @bvalues = values %b;
    $res .= "{\"identifier\": \"id\", \"label\": \"id\", \"items\":" . to_json(\@bvalues) . "}";
    return $res;
}

# Print list of available actions on objects
sub do_plainhelp {
    my $res;
    $res .= $Stabile::q->header('text/plain') unless $console;
    $res .= <<END
new [name="name"]
* start: Starts a server
* destroy: Destroys a server, i.e. terminates the VM, equivalent of turning the power off a physical computer
* shutdown: Asks the operating system of a server to shut down via ACPI
* suspend: Suspends the VM, effectively putting the server to sleep
* resume: Resumes a suspended VM, effectively waking the server from sleep
* move [mac="mac"]: Moves a server to specified node. If no node is specified, moves to other node with highest availability
index
* delete: Deletes a server. Image and network are not deleted, only information about the server. Server cannot be
runing
* mountcd [cdrom="path"]: Mounts a cd rom
END
    ;
    return $res;
}

# Helper function
sub recurse($) {
	my($path) = @_;
	my @files;
	## append a trailing / if it's not there
	$path .= '/' if($path !~ /\/$/);
	## loop through the files contained in the directory
	for my $eachFile (glob($path.'*')) {
		## if the file is a directory
		if( -d $eachFile) {
			## pass the directory to the routine ( recursion )
			push(@files,recurse($eachFile));
		} else {
			push(@files,$eachFile);
		}
	}
	return @files;
}

sub Start {
    my ($uuid, $action, $obj) = @_;
    $dmac = $obj->{mac};
    $buildsystem = $obj->{buildsystem};
    $uistatus = $obj->{uistatus};
    if ($help) {
        return <<END
GET:uuid,mac:
Start a server. Supply mac for starting on specific node.
END
    }
    $dmac = $dmac || $params{'mac'};
    return "Status=ERROR No uuid\n" unless ($register{$uuid});
    my $serv = $register{$uuid};
    $postreply = '' if ($buildsystem);

    my $name = $serv->{'name'};
    utf8::decode($name);
    my $image = $serv->{'image'};
    my $image2 = $serv->{'image2'};
    my $image3 = $serv->{'image3'};
    my $image4 = $serv->{'image4'};
    my $memory = $serv->{'memory'};
    my $vcpu = $serv->{'vcpu'};
    my $vgpu = $serv->{'vgpu'};
    my $dbstatus = $serv->{'status'};
    my $mac = $serv->{'mac'};
    my $macname = $serv->{'macname'};
    my $networkuuid1 = $serv->{'networkuuid1'};
    my $networkuuid2 = $serv->{'networkuuid2'};
    my $networkuuid3 = $serv->{'networkuuid3'};
    my $nicmodel1 = $serv->{'nicmodel1'};
    my $nicmac1 = $serv->{'nicmac1'};
    my $nicmac2 = $serv->{'nicmac2'};
    my $nicmac3 = $serv->{'nicmac3'};
    my $boot = $serv->{'boot'};
    my $diskbus = $serv->{'diskbus'};
    my $cdrom = $serv->{'cdrom'};
    my $diskdev = "vda";
    my $diskdev2 = "vdb";
    my $diskdev3 = "vdc";
    my $diskdev4 = "vdd";
    if ($diskbus eq "ide") {$diskdev = "hda"; $diskdev2 = "hdb"; $diskdev3 = "hdc"; $diskdev4 = "hdd"};

    my $mem = $memory * 1024;

    unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {return "Unable to access image register"};

    my $img = $imagereg{$image};
    my $imagename = $img->{'name'};
    my $imagestatus = $img->{'status'};
    my $img2 = $imagereg{$image2};
    my $image2status = $img2->{'status'};
    my $img3 = $imagereg{$image3};
    my $image3status = $img3->{'status'};
    my $img4 = $imagereg{$image4};
    my $image4status = $img4->{'status'};

    if (!$imagereg{$image}) {
        $postreply .= "Status=Error Image $image not found - please select a new image for your server, not starting $name\n";
        untie %imagereg;
        return $postreply;
    }
    untie %imagereg;

    if ($imagestatus ne "used" && $imagestatus ne "cloning") {
        $postreply .= "Status=ERROR Image $imagename $image is $imagestatus, not starting $name\n";
    } elsif ($image2 && $image2 ne '--' && $image2status ne "used" && $image2status ne "cloning") {
        $postreply .= "Status=ERROR Image2 is $image2status, not starting $name\n";
    } elsif ($image3 && $image3 ne '--' && $image3status ne "used" && $image3status ne "cloning") {
        $postreply .= "Status=ERROR Image3 is $image3status, not starting $name\n";
    } elsif ($image4 && $image4 ne '--' && $image4status ne "used" && $image4status ne "cloning") {
        $postreply .= "Status=ERROR Image4 is $image4status, not starting $name\n";
    } elsif (overQuotas($memory,$vcpu)) {
        $main::syslogit->($user, "info", "Over quota starting a $dbstatus domain: $uuid");
        $postreply .= "Status=ERROR Over quota - not starting $name\n";
    # Status inactive is typically caused by a movepiston having problems. We should not start inactive servers since
    # they could possibly be running even if movepiston is down. Movepiston on the node should be brought up to update
    # the status, or the node should be removed from the stabile.
    # We now allow to force start of inactive server when dmac is specified
    } elsif ((!$dmac || $dmac eq $mac) && $dbstatus eq 'inactive' && $nodereg{$mac} && ($nodereg{$mac}->{'status'} eq 'inactive' || $nodereg{$mac}->{'status'} eq 'shutdown')) {
        $main::syslogit->($user, "info", "Not starting inactive domain: $uuid (last seen on $mac)");
        $postreply .= "Status=ERROR Not starting $name - Please bring up node $macname\n";
    } elsif ($dbstatus eq 'inactive' || $dbstatus eq 'shutdown' || $dbstatus eq 'shutoff' || $dbstatus eq 'new') {
        unless ($dmac && $isadmin) {
            $dmac = $mac if ($dbstatus eq 'inactive'); # If movepiston crashed while shutting down, allow server to start on same node
        }
        $uistatus = "starting" unless ($uistatus);
        my $hypervisor = getHypervisor($image);
        my ($targetmac, $targetname, $targetip, $port) = locateTargetNode($uuid, $dmac, $mem, $vcpu, $image, $image2 ,$image3, $image4, $hypervisor);

        # Build XML for starting domain
        my $graphics = "vnc";
        $graphics = "rdp" if ($hypervisor eq "vbox");
        my $net1 = $networkreg{$networkuuid1};
        my $networkid1 = $net1->{'id'}; # Get the current vlan id of the network
        my $net2 = $networkreg{$networkuuid2};
        my $networkid2 = $net2->{'id'}; # Get the current vlan id of the network
        my $net3 = $networkreg{$networkuuid2};
        my $networkid3 = $net3->{'id'}; # Get the current vlan id of the network
        my $networkid1ip = $net1->{'internalip'};
        $networkid1ip = $net1->{'externalip'} if ($net1->{'type'} eq 'externalip');

        my $uname = $name . substr($uuid,0,8); # We don't enforce unique names, so we make them
        $uname =~ s/[^[:ascii:]]/_/g; # Get rid of funny chars - they mess up Guacamole
        $uname =~ s/\W/_/g;

        my $driver1;
        my $driver2;
        if ($hypervisor eq 'kvm') {
            my $fmt1 = ($image =~ /\.qcow2$/)?'qcow2':'raw';
            my $fmt2 = ($image2 =~ /\.qcow2$/)?'qcow2':'raw';
            my $fmt3 = ($image3 =~ /\.qcow2$/)?'qcow2':'raw';
            my $fmt4 = ($image4 =~ /\.qcow2$/)?'qcow2':'raw';
            my $cache1 = ($image =~ /\/node\//)?'default':'writeback';
            my $cache2 = ($image2 =~ /\/node\//)?'default':'writeback';
            my $cache3 = ($image3 =~ /\/node\//)?'default':'writeback';
            my $cache4 = ($image4 =~ /\/node\//)?'default':'writeback';
            $driver1 = "\n      <driver name='qemu' type='$fmt1' cache='$cache1'/>";
            $driver2 = "\n      <driver name='qemu' type='$fmt2' cache='$cache2'/>";
            $driver3 = "\n      <driver name='qemu' type='$fmt3' cache='$cache3'/>";
            $driver4 = "\n      <driver name='qemu' type='$fmt4' cache='$cache4'/>";
        }

        my $networktype1 = "user";
        my $networksource1 = "default";
        my $networkforward1 = "bridge";
        my $networkisolated1 = "no";
        $networksource1 = "vboxnet0" if ($hypervisor eq "vbox");
        if ($networkid1 eq '0') {
            $networktype1 = "user";
            $networkforward1 = "nat";
            $networkisolated1 = "yes"
        } elsif ($networkid1 == 1) {
            $networktype1 = "network" ;
            $networkforward1 = "nat";
            $networkisolated1 = "yes"
        } elsif ($networkid1 > 1) {
            $networktype1 = "bridge";
            $networksource1 = "br$networkid1";
        }
        my $networktype2 = "user";
        my $networksource2 = "default";
        my $networkforward2 = "bridge";
        my $networkisolated2 = "no";
        $networksource2 = "vboxnet0" if ($hypervisor eq "vbox");
        if ($networkid2 eq '0') {
            $networktype2 = "user";
            $networkforward2 = "nat";
            $networkisolated2 = "yes"
        } elsif ($networkid2 == 1) {
            $networktype2 = "network" ;
            $networkforward2 = "nat";
            $networkisolated2 = "yes"
        } elsif ($networkid2 > 1) {
            $networktype2 = "bridge";
            $networksource2 = "br$networkid2";
        }
        my $networktype3 = "user";
        my $networksource3 = "default";
        my $networkforward3 = "bridge";
        my $networkisolated3 = "no";
        $networksource3 = "vboxnet0" if ($hypervisor eq "vbox");
        if ($networkid3 eq '0') {
            $networktype3 = "user";
            $networkforward3 = "nat";
            $networkisolated3 = "yes"
        } elsif ($networkid3 == 1) {
            $networktype3 = "network" ;
            $networkforward3 = "nat";
            $networkisolated3 = "yes"
        } elsif ($networkid3 > 1) {
            $networktype3 = "bridge";
            $networksource3 = "br$networkid3";
        }

        my $xml = "<domain type='$hypervisor' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>\n";
#        if ($vgpu && $vgpu ne "--") {
#            $xml .= <<ENDXML2
#  <qemu:commandline>
#    <qemu:arg value='-device'/>
#    <qemu:arg value='vfio-pci,host=01:00.0,x-vga=on'/>
#    <qemu:arg value='-device'/>
#    <qemu:arg value='vfio-pci,host=02:00.0,x-vga=on'/>
#  </qemu:commandline>
#ENDXML2
#            ;
#        }

#    <qemu:arg value='-set'/>
#    <qemu:arg value='device.hostdev1.x-vga=on'/>
#    <qemu:arg value='-cpu'/>
#	<qemu:arg value='host,kvm=off'/>
#    <qemu:arg value='-device'/>
#	<qemu:arg value='pci-assign,host=01:00.0,id=hostdev0,configfd=20,bus=pci.0,addr=0x6,x-pci-vendor-id=0x10DE,x-pci-device-id=0x11BA,x-pci-sub-vendor-id=0x10DE,x-pci-sub-device-id=0x0965'/>

#  <cpu mode='host-model'>
#    <vendor>Intel</vendor>
#    <model>core2duo</model>
#  </cpu>

#    <loader readonly='yes' type='pflash'>/usr/share/OVMF/OVMF_CODE.fd</loader>
#    <nvram template='/usr/share/OVMF/OVMF_VARS.fd'/>

        if ($vgpu && $vgpu ne "--") { $xml .= <<ENDXML
  <cpu mode='host-passthrough'>
    <feature policy='disable' name='hypervisor'/>
  </cpu>
ENDXML
;
        }
        $xml .=  <<ENDXML
  <name>$uname</name>
  <uuid>$uuid</uuid>
  <memory>$mem</memory>
  <vcpu>$vcpu</vcpu>
  <os>
    <type arch='x86_64' machine='pc'>hvm</type>
    <boot dev='$boot'/>
    <bootmenu enable='yes' timeout='200'/>
    <smbios mode='sysinfo'/>
  </os>
  <sysinfo type='smbios'>
    <bios>
      <entry name='vendor'>Origo</entry>
    </bios>
    <system>
      <entry name='manufacturer'>Origo</entry>
      <entry name='sku'>$networkid1ip</entry>
    </system>
  </sysinfo>
  <features>
ENDXML
;
        if ($vgpu && $vgpu ne "--") { $xml .= <<ENDXML
    <kvm>
      <hidden state='on'/>
    </kvm>
ENDXML
;
        }
        $xml .= <<ENDXML
    <pae/>
    <acpi/>
    <apic/>
  </features>
  <clock offset='localtime'>
    <timer name='rtc' tickpolicy='catchup' track='guest'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>restart</on_crash>
  <devices>
  <sound model='ac97'/>
ENDXML
;
#        if ($vgpu && $vgpu ne "--") {
#            $xml .= <<ENDXML2
#  <hostdev mode='subsystem' type='pci' managed='yes'>
#    <source>
#      <address domain='0x0000' bus='0x01' slot='0x00' function='0x0' multifunction='on'/>
#    </source>
#  </hostdev>
#  <hostdev mode='subsystem' type='pci' managed='yes'>
#    <source>
#      <address domain='0x0000' bus='0x02' slot='0x00' function='0x0' multifunction='on'/>
#    </source>
#  </hostdev>
#ENDXML2
#;
#        }
        if ($image && $image ne "" && $image ne "--") {
						$xml .= <<ENDXML2
    <disk type='file' device='disk'>
      <source file='$image'/>$driver1
      <target dev='$diskdev' bus='$diskbus'/>
    </disk>
ENDXML2
;
        };

        if ($image2 && $image2 ne "" && $image2 ne "--") {
						$xml .= <<ENDXML2
    <disk type='file' device='disk'>$driver2
      <source file='$image2'/>
      <target dev='$diskdev2' bus='$diskbus'/>
    </disk>
ENDXML2
;
        };
        if ($image3 && $image3 ne "" && $image3 ne "--") {
						$xml .= <<ENDXML2
    <disk type='file' device='disk'>$driver3
      <source file='$image3'/>
      <target dev='$diskdev3' bus='$diskbus'/>
    </disk>
ENDXML2
;
        };
        if ($image4 && $image4 ne "" && $image4 ne "--") {
						$xml .= <<ENDXML2
    <disk type='file' device='disk'>$driver4
      <source file='$image4'/>
      <target dev='$diskdev4' bus='$diskbus'/>
    </disk>
ENDXML2
;
        };

        unless ($image4 && $image4 ne '--' && $diskbus eq 'ide') {
            if ($cdrom && $cdrom ne "" && $cdrom ne "--") {
						$xml .= <<ENDXML3
    <disk type='file' device='cdrom'>
      <source file='$cdrom'/>
      <target dev='hdd' bus='ide'/>
      <readonly/>
    </disk>
ENDXML3
;
            } elsif ($hypervisor ne "vbox") {
						$xml .= <<ENDXML3
    <disk type='file' device='cdrom'>
      <target dev='hdd' bus='ide'/>
      <readonly/>
    </disk>
ENDXML3
;
            }
        }

        $xml .= <<ENDXML4
    <interface type='$networktype1'>
      <source $networktype1='$networksource1'/>
      <forward mode='$networkforward1'/>
      <port isolated='$networkisolated1'/>
      <model type='$nicmodel1'/>
      <mac address='$nicmac1'/>
    </interface>
ENDXML4
;

        if (($networkuuid2 && $networkuuid2 ne '--') || $networkuuid2 eq '0') {
            $xml .= <<ENDXML5
    <interface type='$networktype2'>
      <source $networktype2='$networksource2'/>
      <forward mode='$networkforward2'/>
      <port isolated='$networkisolated2'/>
      <model type='$nicmodel1'/>
      <mac address='$nicmac2'/>
    </interface>
ENDXML5
;
        }
        if (($networkuuid3 && $networkuuid3 ne '--') || $networkuuid3 eq '0') {
            $xml .= <<ENDXML5
    <interface type='$networktype3'>
      <source $networktype3='$networksource3'/>
      <forward mode='$networkforward3'/>
      <port isolated='$networkisolated3'/>
      <model type='$nicmodel1'/>
      <mac address='$nicmac3'/>
    </interface>
ENDXML5
;
        }
        $xml .= <<ENDXML6
     <serial type='pty'>
       <source path='/dev/pts/0'/>
       <target port='0'/>
     </serial>
    <input type='tablet' bus='usb'/>
    <graphics type='$graphics' port='$port'/>
  </devices>
</domain>
ENDXML6
;


#    <graphics type='$graphics' port='$port' keymap='en-us'/>
#     <console type='pty' tty='/dev/pts/0'>
#       <source path='/dev/pts/0'/>
#       <target port='0'/>
#     </console>
#     <graphics type='$graphics' port='-1' autoport='yes'/>

        $xmlreg{$uuid} = {
            xml=>URI::Escape::uri_escape($xml)
        };

        # Actually ask node to start domain
        if ($targetmac) {
            $register{$uuid}->{'mac'} = $targetmac;
            $register{$uuid}->{'macname'} = $targetname;
            $register{$uuid}->{'macip'} = $targetip;

            my $tasks = $nodereg{$targetmac}->{'tasks'};
            $tasks .= "START $uuid $user\n";
    # Also update allowed port forwards - obsolete
    #        $tasks .= "PERMITOPEN $user\n";
            $nodereg{$targetmac}->{'tasks'} = $tasks;
            tied(%nodereg)->commit;
            $uiuuid = $uuid;
            $uidisplayip = $targetip;
            $uidisplayport = $port;
            $register{$uuid}->{'status'} = $uistatus;
            $register{$uuid}->{'statustime'} = $current_time;
            tied(%register)->commit;

            # Activate networks
            require "$Stabile::basedir/cgi/networks.cgi";
            Stabile::Networks::Activate($networkuuid1, 'activate');
            Stabile::Networks::Activate($networkuuid2, 'activate') if ($networkuuid2 && $networkuuid2 ne '--');
            Stabile::Networks::Activate($networkuuid3, 'activate') if ($networkuuid3 && $networkuuid3 ne '--');

            $main::syslogit->($user, "info", "Marked $name ($uuid) for ". $serv->{'status'} . " on $targetname ($targetmac)");
            $postreply .= "Status=starting OK $uistatus ". $serv->{'name'} . "\n";
        } else {
            $main::syslogit->($user, "info", "Could not find $hypervisor target for creating $uuid ($image)");
            $postreply .= "Status=ERROR problem $uistatus ". $serv->{'name'} . " (unable to locate target node)\n";
        };
    } else {
        $main::syslogit->($user, "info", "Problem $uistatus a $dbstatus domain: $uuid");
        $postreply .= "Status=ERROR problem $uistatus ". $serv->{'name'} . "\n";
    }
    #return ($uiuuid, $uidisplayip, $uidisplayport, $postreply, $targetmac);
    return $postreply;
}

sub do_attach {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,image:
Attaches an image to a server as a disk device. Image must not be in use.
END
    }
    my $dev = '';
    my $imagenum = 0;
    my $serv = $register{$uuid};

    if (!$serv->{'uuid'} || ($serv->{'status'} ne 'running' && $serv->{'status'} ne 'paused')) {
        return "Status=Error Server must exist and be running\n";
    }
    my $macip = $serv->{macip};
    my $image = $obj->{image} || $obj->{path};
    if ($image && !($image =~ /^\//)) { # We have a uuid
        unless ( tie(%imagereg2,'Tie::DBI', Hash::Merge::merge({table=>'images', CLOBBER=>1}, $Stabile::dbopts)) ) {return "Status=Error Unable to access images register\n"};
        $image = $imagereg2{$image}->{'path'} if ($imagereg2{$image});
        untie %imagereg2;
    }
    unless (tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {$postreply .= "Status=Error Unable to access images register\n"; return $postreply;};
    unless ($macip && $imagereg{$image} && $imagereg{$image}->{'user'} eq $user && $serv->{'user'} eq $user)  {$postreply .= "Status=Error Invalid image or server\n"; return $postreply;};
    if ($imagereg{$image}->{'status'} ne 'unused') {return "Status=Error Image $image is already in use ($imagereg{$image}->{'status'})\n"};

    my $cmd = qq|$sshcmd $macip "LIBVIRT_DEFAULT_URI=qemu:///system virsh domblklist $uuid"|;
    my $res = `$cmd`;
    unless ($res =~ /vdb\s+.+/) {$dev = 'vdb'; $imagenum = 2};
    unless ($dev || $res =~ /vdc\s+.+/)  {$dev = 'vdc'; $imagenum = 3};
    unless ($dev || $res =~ /vdd\s+.+/)  {$dev = 'vdd'; $imagenum = 4};
    if (!$dev) {
        $postreply = "Status=Error No more images can be attached\n";
    } else {
        my $xml = <<END
<disk type='file' device='disk'>
  <driver type='qcow2' name='qemu' cache='default'/>
  <source file='$image'/>
  <target dev='$dev' bus='virtio'/>
</disk>
END
;
        $cmd = qq|$sshcmd $macip "echo \\"$xml\\" > /tmp/attach-device-$uuid.xml"|;
        $res = `$cmd`;
        $res .= `$sshcmd $macip LIBVIRT_DEFAULT_URI=qemu:///system virsh attach-device $uuid /tmp/attach-device-$uuid.xml`;
        chomp $res;
        if ($res =~ /successfully/) {
            $postreply .= "Status=OK Attaching $image to $dev\n";
            $imagereg{$image}->{'status'} = 'active';
            $imagereg{$image}->{'domains'} = $uuid;
            $imagereg{$image}->{'domainnames'} = $serv->{'name'};
            $serv->{"image$imagenum"} = $image;
            $serv->{"image$imagenum"."name"} = $imagereg{$image}->{'name'};
            $serv->{"image$imagenum"."type"} = 'qcow2';
        } else {
            $postreply .= "Status=Error Unable to attach image $image to $dev ($res)\n";
        }
    }
    untie %imagereg;
    return $postreply;
}

sub do_detach {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,image:
Detaches a disk device and the associated image from a running server. All associated file-systems within the server should be unmounted before detaching, otherwise data loss i very probable. Use with care.
END
    }
    my $dev = '';
    my $serv = $register{$uuid};

    if (!$serv->{'uuid'} || ($serv->{'status'} ne 'running' && $serv->{'status'} ne 'paused')) {
        return "Status=Error Server must exist and be running\n";
    }
    my $macip = $serv->{macip};

    my $image = $obj->{image} || $obj->{path} || $serv->{'image2'};
    if ($image && !($image =~ /^\//)) { # We have a uuid
        unless ( tie(%imagereg2,'Tie::DBI', Hash::Merge::merge({table=>'images', CLOBBER=>1}, $Stabile::dbopts)) ) {return "Unable to access images register"};
        $image = $imagereg2{$image}->{'path'} if ($imagereg2{$image});
        untie %imagereg2;
    }
    unless (tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {$postreply .= "Status=Error Unable to access images register\n"; return $postreply;};
    unless ($macip && $imagereg{$image} && $imagereg{$image}->{'user'} eq $user && $serv->{'user'} eq $user)  {$postreply .= "Status=Error Invalid image or server. Server must have a secondary image attached.\n"; return $postreply;};

    my $cmd = qq|$sshcmd $macip "LIBVIRT_DEFAULT_URI=qemu:///system virsh domblklist $uuid"|;
    my $res = `$cmd`;
    $dev = $1 if ($res =~ /(vd.)\s+.+$image/);
    if (!$dev) {
        $postreply =  qq|Status=Error Image $image, $cmd, is not currently attached\n|;
    } elsif ($dev eq 'vda') {
        $postreply = "Status=Error You cannot detach the primary image\n";
    } else {
        $res = `$sshcmd $macip LIBVIRT_DEFAULT_URI=qemu:///system virsh detach-disk $uuid $dev`;
        chomp $res;
        if ($res =~ /successfully/) {
            $postreply .= "Status=OK Detaching image $image, $imagereg{$image}->{'uuid'} from $dev\n";
            my $imagenum;
            $imagenum = 2 if ($serv->{'image2'} eq $image);
            $imagenum = 3 if ($serv->{'image3'} eq $image);
            $imagenum = 4 if ($serv->{'image4'} eq $image);
            $imagereg{$image}->{'status'} = 'unused';
            $imagereg{$image}->{'domains'} = '';
            $imagereg{$image}->{'domainnames'} = '';
            if ($imagenum) {
                $serv->{"image$imagenum"} = '';
                $serv->{"image$imagenum"."name"} = '';
                $serv->{"image$imagenum"."type"} = '';
            }
        } else {
            $postreply .= "Status=Error Unable to attach image $image to $dev ($res)\n";
        }
    }
    untie %imagereg;
    return $postreply;
}

sub Destroy {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,wait:
Marks a server for halt, i.e. pull the plug if regular shutdown does not work or is not desired. Server and storage is preserved.
END
    }
    my $uistatus = 'destroying';
    my $name = $register{$uuid}->{'name'};
    my $mac = $register{$uuid}->{'mac'};
    my $macname = $register{$uuid}->{'macname'};
    my $dbstatus = $register{$uuid}->{'status'};
    my $wait = $obj->{'wait'};
    if ($dbstatus eq 'running' or $dbstatus eq 'paused'
        or $dbstatus eq 'shuttingdown' or $dbstatus eq 'starting'
        or $dbstatus eq 'destroying' or $dbstatus eq 'upgrading'
        or $dbstatus eq 'suspending' or $dbstatus eq 'resuming') {
        if ($wait) {
            $postreply = destroyUserServers($user, 1, $uuid);
        } else {
            my $tasks = $nodereg{$mac}->{'tasks'};
            $nodereg{$mac}->{'tasks'} = $tasks . "DESTROY $uuid $user\n";
            tied(%nodereg)->commit;
            $register{$uuid}->{'status'} = $uistatus;
            $register{$uuid}->{'statustime'} = $current_time;
            $uiuuid = $uuid;
            $main::syslogit->($user, "info", "Marked $name ($uuid) for $uistatus on $macname ($mac)");
            $postreply .= "Status=destroying $uistatus ". $register{$uuid}->{'name'} . "\n";
        }
    } else {
        $main::syslogit->($user, "info", "Problem $uistatus a $dbstatus domain: $name ($uuid)");
        $postreply .= "Status=ERROR problem $uistatus $name\n";
    }
    return $postreply;
}

sub getHypervisor {
	my $image = shift;
	# Produce a mapping of image file suffixes to hypervisors
	my %idreg;
    unless ( tie(%idreg,'Tie::DBI', Hash::Merge::merge({table=>'nodeidentities', key=>'identity'}, $Stabile::dbopts)) ) {return "Unable to access nodeidentities register"};
    my @idvalues = values %idreg;
	my %formats;
	foreach my $val (@idvalues) {
		my %h = %$val;
		foreach (split(/,/,$h{'formats'})) {
			$formats{lc $_} = $h{'hypervisor'}
		}
	}
	untie %idreg;

	# and then determine the hypervisor in question
	my $hypervisor = "vbox";
	my ($pathname, $path, $suffix) = fileparse($image, '\.[^\.]*');
	$suffix = substr $suffix, 1;
	my $hypervisor = $formats{lc $suffix};
	return $hypervisor;
}

sub nicmac1ToUuid {
    my $nicmac1 = shift;
    my $uuid;
    return $uuid unless $nicmac1;
    my @regkeys = (tied %register)->select_where("user = '$user' AND nicmac1 = '$nicmac1");
	foreach my $k (@regkeys) {
	    my $val = $register{$k};
		my %h = %$val;
		if (lc $h{'nicmac1'} eq lc $nicmac1 && $user eq $h{'user'}) {
    		$uuid =  $h{'uuid'};
    		last;
		}
	}
	return $uuid;
}

sub randomMac {
	my ( %vendor, $lladdr, $i );
#	$lladdr = '00';
	$lladdr = '52:54:00';# KVM vendor string
	while ( ++$i )
#	{ last if $i > 10;
	{ last if $i > 6;
		$lladdr .= ':' if $i % 2;
		$lladdr .= sprintf "%" . ( qw (X x) [int ( rand ( 2 ) ) ] ), int ( rand ( 16 ) );
	}
	return $lladdr;
}

sub overQuotas {
    my $meminc = shift;
    my $vcpuinc = shift;
	my $usedmemory = 0;
	my $usedvcpus = 0;
	my $overquota = 0;
    return $overquota if ($isadmin || $Stabile::userprivileges =~ /a/); # Don't enforce quotas for admins

	my $memoryquota = $usermemoryquota;
	my $vcpuquota = $uservcpuquota;

	if (!$memoryquota || !$vcpuquota) { # 0 or empty quota means use defaults
        $memoryquota = $memoryquota || $Stabile::config->get('MEMORY_QUOTA');
        $vcpuquota = $vcpuquota || $Stabile::config->get('VCPU_QUOTA');
    }

    my @regkeys = (tied %register)->select_where("user = '$user'");
	foreach my $k (@regkeys) {
	    my $val = $register{$k};
		if ($val->{'user'} eq $user && $val->{'status'} ne "shutoff" &&
		    $val->{'status'} ne "inactive" && $val->{'status'} ne "shutdown" ) {

		    $usedmemory += $val->{'memory'};
		    $usedvcpus += $val->{'vcpu'};
		}
	}
	$overquota = $usedmemory+$meminc if ($memoryquota!=-1 && $usedmemory+$meminc > $memoryquota); # -1 means no quota
	$overquota = $usedvcpus+$vcpuinc if ($vcpuquota!=-1 && $usedvcpus+$vcpuinc > $vcpuquota);
	return $overquota;
}

sub validateItem {
    my $valref = shift;
    my $img = $imagereg{$valref->{'image'}};
    my $imagename = $img->{'name'};
    $valref->{'imagename'} = $imagename if ($imagename);
    my $imagetype = $img->{'type'};
    $valref->{'imagetype'} = $imagetype if ($imagetype);

    # imagex may be registered by uuid instead of path - find the path
    # We now support up to 4 images
    for (my $i=2; $i<=4; $i++) {
        if ($valref->{"image$i"} && $valref->{"image$i"} ne '--' && !($valref->{"image$i"} =~ /^\//)) {
            unless ( tie(%imagereg2,'Tie::DBI', Hash::Merge::merge({table=>'images', CLOBBER=>1}, $Stabile::dbopts)) ) {return "Unable to access images register"};
            $valref->{"image$i"} = $imagereg2{$valref->{"image$i"}}->{'path'};
            untie %imagereg2;
        }

        my $imgi = $imagereg{$valref->{"image$i"}};
        $valref->{"image$i" . 'name'} = $imgi->{'name'} || $valref->{"image$i" . 'name'};
        $valref->{"image$i" . 'type'} = $imgi->{'type'} || $valref->{"image$i" . 'type'};
    }

    my $net1 = $networkreg{$valref->{'networkuuid1'}};
    my $networkname1 = $net1->{'name'};
    $valref->{'networkname1'} = $networkname1 if ($networkname1);
    my $net2 = $networkreg{$valref->{'networkuuid2'}};
    my $networkname2 = $net2->{'name'};
    $valref->{'networkname2'} = $networkname2 if ($networkname2);
    my $name = $valref->{'name'};
    $valref->{'name'} = $imagename unless $name;

    if ($valref->{'status'} eq "shutoff" || $valref->{'status'} eq "inactive") {
        my $node = $nodereg{$valref->{'mac'}};
        if ($valref->{'image'} =~ /\/mnt\/stabile\/node\//) {
            $valref->{'mac'} = $img->{'mac'};
            $valref->{'macname'} = $node->{'name'};
            $valref->{'macip'} = $node->{'ip'};
        } elsif ($valref->{'image2'} =~ /\/mnt\/stabile\/node\//) {
            $valref->{'mac'} = $imagereg{$valref->{'image2'}}->{'mac'};
            $valref->{'macname'} = $node->{'name'};
            $valref->{'macip'} = $node->{'ip'};
        } elsif ($valref->{'image3'} =~ /\/mnt\/stabile\/node\//) {
            $valref->{'mac'} = $imagereg{$valref->{'image3'}}->{'mac'};
            $valref->{'macname'} = $node->{'name'};
            $valref->{'macip'} = $node->{'ip'};
        } elsif ($valref->{'image4'} =~ /\/mnt\/stabile\/node\//) {
            $valref->{'mac'} = $imagereg{$valref->{'image4'}}->{'mac'};
            $valref->{'macname'} = $node->{'name'};
            $valref->{'macip'} = $node->{'ip'};
        }
    }
# Mark domains we have heard from in the last 20 secs as inactive
    my $dbtimestamp = 0;
    $dbtimestamp = $register{$valref->{'uuid'}}->{'timestamp'} if ($register{$valref->{'uuid'}});
    my $timediff = $current_time - $dbtimestamp;
    if ($timediff >= 20) {
        if  (! ($valref->{'status'} eq "shutoff"
                || $valref->{'status'} eq "starting"
            #    || $valref->{'status'} eq "shuttingdown"
            #    || $valref->{'status'} eq "destroying"
                || ($valref->{'status'} eq "moving" && $timediff<40)
            )) { # Move has probably failed
            $valref->{'status'} = "inactive";
            $imagereg{$valref->{'image'}}->{'status'} = "used" if ($valref->{'image'} && $imagereg{$valref->{'image'}});
            $imagereg{$valref->{'image2'}}->{'status'} = "used" if ($valref->{'image2'} && $imagereg{$valref->{'imag2'}});
            $imagereg{$valref->{'image3'}}->{'status'} = "used" if ($valref->{'image3'} && $imagereg{$valref->{'image3'}});
            $imagereg{$valref->{'image4'}}->{'status'} = "used" if ($valref->{'image4'} && $imagereg{$valref->{'image4'}});
        }
    };
    return $valref;
}

# Run through all domains and mark domains we have heard from in the last 20 secs as inactive
sub updateRegister {
    unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>1}, $Stabile::dbopts)) ) {return "Unable to access user register"};
    unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {return "Unable to access images register"};

    my @regkeys = (tied %register)->select_where("user = '$user'");

    foreach my $k (@regkeys) {
        my $valref = $register{$k};
        next unless ($userreg{$valref->{'user'}});
        my $dbtimestamp = $valref->{'timestamp'};
        my $dbstatus = $valref->{'status'};
        my $timediff = $current_time - $dbtimestamp;
        my $imgstatus;
        my $domstatus;
        if ($timediff >= 20) {
            if  ( $valref->{'status'} eq "shutoff" ) {
                $imgstatus = 'used';
            } elsif ((  $valref->{'status'} eq "starting"
                            || $valref->{'status'} eq "shuttingdown"
                        ) && $timediff>50) {
                $imgstatus = 'used';
                $domstatus = 'inactive';
            } elsif ($valref->{'status'} eq "destroying" || $valref->{'status'} eq "moving") {
                ;
            } else {
                $domstatus = 'inactive';
                $imgstatus = 'used';
            }
            $valref->{'status'} = $domstatus if ($domstatus);
            my $image = $valref->{'image'};
            my $image2 = $valref->{'image2'};
            my $image3 = $valref->{'image3'};
            my $image4 = $valref->{'image4'};
            $imagereg{$image}->{'status'} = $imgstatus if ($imgstatus);
            $imagereg{$image2}->{'status'} = $imgstatus if ($image2 && $imgstatus);
            $imagereg{$image3}->{'status'} = $imgstatus if ($image3 && $imgstatus);
            $imagereg{$image4}->{'status'} = $imgstatus if ($image4 && $imgstatus);
            if ($domstatus eq 'inactive ' && $dbstatus ne 'inactive') {
                $main::updateUI->({ tab=>'servers',
                                    user=>$valref->{'user'},
                                    uuid=>$valref->{'uuid'},
                                    sender=>'updateRegister',
                                    status=>'inactive'})
            }
        };

    }
    untie %userreg;
    untie %imagereg;
}


sub locateTargetNode {
    my ($uuid, $dmac, $mem, $vcpu, $image, $image2, $image3, $image4, $hypervisor, $smac)= @_;
    my $targetname;
    my $targetip;
    my $port;
    my $targetnode;
    my $targetindex; # Availability index of located target node
    my %avhash;

    my $mnode = $register{$uuid};
    $dmac = $mnode->{'mac'}
        if (!$dmac
            && $mnode->{'locktonode'} eq 'true'
            && $mnode->{'mac'}
            && $mnode->{'mac'} ne '--'
            );

    $dmac = '' unless ($isadmin); # Only allow admins to select specific node
    if ($dmac && !$nodereg{$dmac}) {
        $main::syslogit->($user, "info", "The target node $dmac no longer exists, starting $uuid on another node if possible");
        $dmac = '';
    }

    my $imageonnode = ($image =~ /\/mnt\/stabile\/node\//
                                          || $image2 =~ /\/mnt\/stabile\/node\//
                                          || $image3 =~ /\/mnt\/stabile\/node\//
                                          || $image4 =~ /\/mnt\/stabile\/node\//
                                          );

    foreach $node (values %nodereg) {
        my $nstatus = $node->{'status'};
        my $maintenance = $node->{'maintenance'};
        my $nmac = $node->{'mac'};

        if (($nstatus eq 'running' || $nstatus eq 'asleep' || $nstatus eq 'maintenance' || $nstatus eq 'waking')
         && $smac ne $nmac
         && (( ($node->{'memfree'} > $mem+512*1024)
         && (($node->{'vmvcpus'} + $vcpu) <= ($cpuovercommision * $node->{'cpucores'} * $node->{'cpucount'})) ) || $action eq 'listnodeavailability')
        ) {
        # Determine how available this node is
        # Available memory
            my $memweight = 0.2; # memory weighing factor
            my $memindex = $avhash{$nmac}->{'memindex'} = int(100* $memweight* $node->{'memfree'} / (1024*1024) )/100;
        # Free cores
            my $cpuindex = $avhash{$nmac}->{'cpuindex'} = int(100*($cpuovercommision * $node->{'cpucores'} * $node->{'cpucount'} - $node->{'vmvcpus'} - $node->{'reservedvcpus'}))/100;
        # Asleep - not asleep gives a +3
            my $sleepindex = $avhash{$nmac}->{'sleepindex'} = ($node->{'status'} eq 'asleep' || $node->{'status'} eq 'waking')?'0':'3';
            $avhash{$nmac}->{'vmvcpus'} = $node->{'vmvcpus'};
#            $avhash{$nmac}->{'cpucommision'} = $cpuovercommision * $node->{'cpucores'} * $node->{'cpucount'};
#            $avhash{$nmac}->{'cpureservation'} = $node->{'vmvcpus'} + $node->{'reservedvcpus'};

            $avhash{$nmac}->{'name'} = $node->{'name'};
            $avhash{$nmac}->{'mac'} = $node->{'mac'};

            my $aindex = $memindex + $cpuindex + $sleepindex;
        # Don't use nodes that are out of memory of cores
            $aindex = 0 if ($memindex <= 0 || $cpuindex <= 0);
            $avhash{$nmac}->{'index'} = $aindex;

            $avhash{$nmac}->{'storfree'} = $node->{'storfree'};
            $avhash{$nmac}->{'memfree'} = $node->{'memfree'};
            $avhash{$nmac}->{'ip'} = $node->{'ip'};
            $avhash{$nmac}->{'identity'} = $node->{'identity'};
            $avhash{$nmac}->{'status'} = $node->{'status'};
            $avhash{$nmac}->{'maintenance'} = $maintenance;
            $avhash{$nmac}->{'reservedvcpus'} = $node->{'reservedvcpus'};
            my $nodeidentity = $node->{'identity'};
            $nodeidentity = 'kvm' if ($nodeidentity eq 'local_kvm');

            if ($hypervisor eq $nodeidentity) {
                # If image is on node, we must start on same node - registered when moving image
                if ($imageonnode) {
                    unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {return "Unable to access images register"};
                    $dmac = $imagereg{$image}->{'mac'};
                    $dmac = $imagereg{$image2}->{'mac'} unless ($dmac);
                    $dmac = $imagereg{$image3}->{'mac'} unless ($dmac);
                    $dmac = $imagereg{$image4}->{'mac'} unless ($dmac);

                    untie %imagereg;
                    if (!$dmac) {
                        $postreply .= "Status=ERROR Image node not found\n";
                        last;
                    }
                }
                $dmac = "" if ($dmac eq "--");
            # If a specific node is asked for, c match mac addresses
                if ($dmac eq $nmac) {
                    $targetnode = $node;
                    last;
                } elsif (!$dmac && $nstatus ne "maintenance" && !$maintenance) {
            # pack or disperse
                    if (!$targetindex) {
                        $targetindex = $aindex;
                        $targetnode = $node;
                    } elsif ($dpolicy eq 'pack') {
                        if ($aindex < $targetindex) {
                            $targetnode = $node;
                            $targetindex = $aindex;
                        }
                    } else {
                        if ($aindex > $targetindex) {
                            $targetnode = $node;
                            $targetindex = $aindex;
                        }
                    }
                }
            }
        }
    }

    if ($targetnode && $uuid) {
        if ($targetnode->{'status'} eq 'asleep') {
            my $nmac = $targetnode->{'mac'};
            my $realmac = substr($nmac,0,2).":".substr($nmac,2,2).":".substr($nmac,4,2).":".substr($nmac,6,2).":".substr($nmac,8,2).":".substr($nmac,10,2);
            my $nlogmsg = "Node $nmac marked for wake ";
            if ($brutalsleep && (
                    ($targetnode->{'amtip'} && $targetnode->{'amtip'} ne '--')
                || ($targetnode->{'ipmiip'} && $targetnode->{'ipmiip'} ne '--')
                )) {
                my $wakecmd;
                if ($targetnode->{'amtip'} && $targetnode->{'amtip'} ne '--') {
                    $wakecmd = "echo 'y' | AMT_PASSWORD='$amtpasswd' /usr/bin/amttool $targetnode->{'amtip'} powerup pxe";
                } else {
                    $wakecmd = "ipmitool -I lanplus -H $targetnode->{'ipmiip'} -U ADMIN -P ADMIN power on";
                }
                $nlogmsg .= `$wakecmd`;
            } else {
                my $broadcastip = $targetnode->{'ip'};
                $broadcastip =~ s/\.\d{1,3}$/.255/;
                $nlogmsg .= 'on lan ' . `/usr/bin/wakeonlan -i $broadcastip $realmac`;
            }
            $targetnode->{'status'} = "waking";
            $nlogmsg =~ s/\n/ /g;
            $main::syslogit->($user, "info", $nlogmsg);
            $postreply .= "Status=OK waking $targetnode->{'name'}\n";
        }
        $targetname = $targetnode->{'name'};
        $targetmac = $targetnode->{'mac'};
        $targetip = $targetnode->{'ip'};
        $targetip = $targetnode->{'ip'};
        my $porttaken = 1;
        while ($porttaken) {
            $porttaken = 0;
            $port = $targetnode->{'vms'} + (($hypervisor eq "vbox")?3389:5900);
            $port += int(rand(200));
            my @regkeys = (tied %register)->select_where("port = '$port' AND macip = '$targetip'");
            foreach my $k (@regkeys) {
                $r = $register{$k};
                if ($r->{'port'} eq $port && $r->{'macip'} eq $targetip) {
                    $porttaken = 1;
                }
            }
        }
        $targetnode->{'vms'}++;
        $targetnode->{'vmvcpus'} += $vcpu;
        $register{$uuid}->{'port'} = $port;
#        $register{$uuid}->{'mac'} = $targetmac;
#        $register{$uuid}->{'macname'} = $targetname;
#        $register{$uuid}->{'macip'} = $targetip;
        $register{$uuid}->{'display'} = (($hypervisor eq "vbox")?'rdp':'vnc');
    } else {
        my $macstatus;
        $macstatus = $nodereg{$dmac}->{status} if ($nodereg{$dmac});
        $main::syslogit->($user, "info", "Could not find target for $uuid, $dmac, $mem, $vcpu, $image, $image2,$image3,$image4, $hypervisor, $smac, dmac-status: $macstatus") if ($uuid);
    }
    return ($targetmac, $targetname, $targetip, $port, \%avhash);
}

sub destroyUserServers {
    my $username = shift;
    my $wait = shift; # Should we wait for servers do die
    my $duuid = shift;
    return unless ($isadmin || $user eq $username);
    my @updateList;

    my @regkeys = (tied %register)->select_where("user = '$username'");
    foreach my $uuid (@regkeys) {
        if ($register{$uuid}->{'user'} eq $username
            && $register{$uuid}->{'status'} ne 'shutoff'
            && (!$duuid || $duuid eq $uuid)
        ) {
            $postreply .= "Destroying $username server $register{$uuid}->{'name'}, $uuid\n";
            Destroy($uuid);
            push (@updateList,{ tab=>'servers',
                                user=>$user,
                                uuid=>$duuid,
                                status=>'destroying'});
        }
    }
    $main::updateUI->(@updateList) if (@updateList);
    if ($wait) {
        my @regkeys = (tied %register)->select_where("user = '$username'");
        my $activeservers = 1;
        my $i = 0;
        while ($activeservers && $i<10) {
            $activeservers = 0;
            foreach my $k (@regkeys) {
                my $valref = $register{$k};
                if ($username eq $valref->{'user'}
                    && ($valref->{'status'} ne 'shutoff'
                    && $valref->{'status'} ne 'inactive')
                    && (!$duuid || $duuid eq $valref->{'uuid'})
                ) {
                    $activeservers = $valref->{'uuid'};
                }
            }
            $i++;
            if ($activeservers) {
                my $res .= "Status=OK Waiting $i for server $register{$activeservers}->{'name'}, $register{$activeservers}->{'status'} to die...\n";
                print $res if ($console);
                $postreply .= $res;
                sleep 2;
            }
        }
        $postreply .= "Status=OK Servers halted for $username\n" unless ($activeservers);
    }
    return $postreply;
}

sub removeUserServers {
    my $username = shift;
    my $uuid = shift;
    my $destroy = shift; # Should running servers be destroyed before removing
    return unless (($isadmin || $user eq $username) && !$isreadonly);
    $user = $username;
    my @regkeys = (tied %register)->select_where("user = '$username'");
    foreach my $ruuid (@regkeys) {
        next if ($uuid && $ruuid ne $uuid);
        if ($destroy && $register{$ruuid}->{'user'} eq $username && ($register{$ruuid}->{'status'} ne 'shutoff' && $register{$ruuid}->{'status'} ne 'inactive')) {
            destroyUserServers($username, 1, $ruuid);
        }

        if ($register{$ruuid}->{'user'} eq $username && ($register{$ruuid}->{'status'} eq 'shutoff' || $register{$ruuid}->{'status'} eq 'inactive')) {
            $postreply .= "Removing $username server $register{$ruuid}->{'name'}, $ruuid" . ($console?'':'<br>') . "\n";
            Remove($ruuid);
        }
    }
}

sub Remove {
    my ($uuid, $action) = @_;
    if ($help) {
        return <<END
DELETE:uuid:
Removes a server. Server must be shutoff. Does not remove associated images or networks.
END
    }
    my $reguser = $register{$uuid}->{'user'};
    my $dbstatus = $register{$uuid}->{'status'};
    my $image = $register{$uuid}->{'image'};
    my $image2 = $register{$uuid}->{'image2'};
    my $image3 = $register{$uuid}->{'image3'};
    my $image4 = $register{$uuid}->{'image4'};
    my $name = $register{$uuid}->{'name'};
    $image2 = '' if ($image2 eq '--');
    $image3 = '' if ($image3 eq '--');
    $image4 = '' if ($image4 eq '--');

    if ($reguser ne $user) {
        $postreply .= "Status=ERROR You cannot delete a vm you don't own\n";
    } elsif ($dbstatus eq 'inactive' || $dbstatus eq 'shutdown' || $dbstatus eq 'shutoff') {

        # Delete software packages and monitors from register
        $postmsg .= deletePackages($uuid);
        my $sname = $register{$uuid}->{'name'};
        utf8::decode($sname);
        $postmsg .= deleteMonitors($uuid)?" deleted monitors for $sname ":'';

        delete $register{$uuid};
        delete $xmlreg{$uuid};

        unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {return "Unable to access images register"};
        $imagereg{$image}->{'status'} = "unused" if ($imagereg{$image});
        $imagereg{$image2}->{'status'} = "unused" if ($image2 && $imagereg{$image2});
        $imagereg{$image3}->{'status'} = "unused" if ($image3 && $imagereg{$image3});
        $imagereg{$image4}->{'status'} = "unused" if ($image4 && $imagereg{$image4});
        untie %imagereg;

        # Delete metrics
        my $metricsdir = "/var/lib/graphite/whisper/domains/$uuid";
        `rm -r $metricsdir` if (-e $metricsdir);
        my $rrdfile = "/var/cache/rrdtool/".$uuid."_highres.rrd";
        `rm $rrdfile` if (-e $rrdfile);

        $main::syslogit->($user, "info", "Deleted domain $uuid from db");
        utf8::decode($name);
        $postmsg .= " deleted server $name";
        $postreply = "[]";
        sleep 1;
    } else {
        $postreply .= "Status=ERROR Cannot delete a $dbstatus server\n";
    }
    return $postreply;
}

# Delete all monitors belonging to a server
sub deleteMonitors {
    my ($serveruuid) = @_;
    my $match;
    if ($serveruuid) {
        if ($register{$serveruuid}->{'user'} eq $user || $isadmin) {
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

sub deletePackages {
    my ($uuid, $issystem, %packreg) = @_;
    unless ( tie(%packreg,'Tie::DBI', Hash::Merge::merge({table=>'packages', key=>'id'}, $Stabile::dbopts)) ) {return "Unable to access images register"};

    my @domains;
    if ($issystem) {
        foreach my $valref (values %register) {
            if (($valref->{'system'} eq $uuid || $uuid eq '*')
                    && ($valref->{'user'} eq $user || $fulllist)) {
                push(@domains, $valref->{'uuid'});
            }
        }
    } else { # Allow if domain no longer exists or belongs to user
        push(@domains, $uuid) if (!$register{$uuid} || $register{$uuid}->{'user'} eq $user || $fulllist);
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
    if ($issystem) {
        my $sname = $register{$uuid}->{'name'};
        utf8::decode($sname);
        return "Status=OK Cleared packages for $sname\n";
    } elsif ($register{$uuid}) {
        my $sname = $register{$uuid}->{'name'};
        utf8::decode($sname);
        return "Status=OK Cleared packages for $sname\n";
    } else {
        return "Status=OK Cleared packages. System not registered\n";
    }
}

sub Save {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
POST:uuid, name, user, system, autostart, locktonode, mac, memory, vcpu, boot, diskbus, nicmodel1, vgpu, cdrom, image, image2, image3, image4, networkuuid2, networkuuid3, networkuuid1, nicmac1, nicmac2, nicmac3:
To save a servers of networks you either PUT or POST a JSON array to the main endpoint with objects representing the servers with the changes you want.
Depending on your privileges not all changes are permitted. If you save without specifying a uuid, a new server is created.
If you pass [user] parameter it is assumed you want to move server to this user's account.
Supported parameters:

uuid: UUID
name: string
user: string
system: UUID of stack this server belongs to
autostart: true|false
locktonode: true|false
mac: MAC address of target node

memory: int bytes
vcpu: int
boot: hd|cdrom|network
diskbus: virtio|ide|scsi
nicmodel1: virtio|rtl8139|ne2k_pci|e1000|i82551|i82557b|i82559er|pcnet
vgpu: int

cdrom: string path
image: string path
image2: string path
image3: string path
image4: string path

networkuuid1: UUID of network connection
networkuuid2: UUID of network connection
networkuuid3: UUID of network connection

END
    }

# notes, opemail, opfullname, opphone, email, fullname, phone, services, recovery, alertemail
# notes: string
# opemail: string
# opfullname: string
# opphone: string
# email: string
# fullname: string
# phone: string
# services: string
# recovery: string
# alertemail: string

    my $system = $obj->{system};
    my $newsystem = $obj->{newsystem};
    my $buildsystem = $obj->{buildsystem};
    my $nicmac1 = $obj->{nicmac1};
    $console = $console || $obj->{console};

    $postmsg = '' if ($buildsystem);
    if (!$uuid && $nicmac1) {
        $uuid = nicmac1ToUuid($nicmac1); # If no uuid try to locate based on mac
    }
    if (!$uuid && $uripath =~ /servers(\.cgi)?\/(.+)/) { # Try to parse uuid out of URI
        my $huuid = $2;
        if ($ug->to_string($ug->from_string($huuid)) eq $huuid) { # Check for valid uuid
            $uuid = $huuid;
        }
    }
    my $regserv = $register{$uuid};
    my $status = $regserv->{'status'} || 'new';
    if ((!$uuid) && $status eq 'new') {
        my $ug = new Data::UUID;
        $uuid = $ug->create_str();
    };
    unless ($uuid && length $uuid == 36){
        $postmsg = "Status=Error No valid uuid ($uuid), $obj->{image}";
        return $postmsg;
    }
    $nicmac1 = $nicmac1 || $regserv->{'nicmac1'};
    my $name = $obj->{name} || $regserv->{'name'};
    my $memory = $obj->{memory} || $regserv->{'memory'};
    my $vcpu = $obj->{vcpu} || $regserv->{'vcpu'};
    my $image = $obj->{image} || $regserv->{'image'};
    my $imagename = $obj->{imagename} || $regserv->{'imagename'};
    my $image2 = $obj->{image2} || $regserv->{'image2'};
    my $image2name = $obj->{image2name} || $regserv->{'image2name'};
    my $image3 = $obj->{image3} || $regserv->{'image3'};
    my $image3name = $obj->{image3name} || $regserv->{'image3name'};
    my $image4 = $obj->{image4} || $regserv->{'image4'};
    my $image4name = $obj->{image4name} || $regserv->{'image4name'};
    my $diskbus = $obj->{diskbus} || $regserv->{'diskbus'};
    my $cdrom = $obj->{cdrom} || $regserv->{'cdrom'};
    my $boot = $obj->{boot} || $regserv->{'boot'};
    my $networkuuid1 = ($obj->{networkuuid1} || $obj->{networkuuid1} eq '0')?$obj->{networkuuid1}:$regserv->{'networkuuid1'};
    my $networkid1 = $obj->{networkid1} || $regserv->{'networkid1'};
    my $networkname1 = $obj->{networkname1} || $regserv->{'networkname1'};
    my $nicmodel1 = $obj->{nicmodel1} || $regserv->{'nicmodel1'};
    my $networkuuid2 = ($obj->{networkuuid2} || $obj->{networkuuid2} eq '0')?$obj->{networkuuid2}:$regserv->{'networkuuid2'};
    my $networkid2 = $obj->{networkid2} || $regserv->{'networkid2'};
    my $networkname2 = $obj->{networkname2} || $regserv->{'networkname2'};
    my $nicmac2 = $obj->{nicmac2} || $regserv->{'nicmac2'};
    my $networkuuid3 = ($obj->{networkuuid3} || $obj->{networkuuid3} eq '0')?$obj->{networkuuid3}:$regserv->{'networkuuid3'};
    my $networkid3 = $obj->{networkid3} || $regserv->{'networkid3'};
    my $networkname3 = $obj->{networkname3} || $regserv->{'networkname3'};
    my $nicmac3 = $obj->{nicmac3} || $regserv->{'nicmac3'};
    my $notes = $obj->{notes} || $regserv->{'notes'};
    my $autostart = $obj->{autostart} || $regserv->{'autostart'};
    my $locktonode = $obj->{locktonode} || $regserv->{'locktonode'};
    my $mac = $obj->{mac} || $regserv->{'mac'};
    my $created = $regserv->{'created'} || time;
    # Sanity checks
    my $tenderpaths = $Stabile::config->get('STORAGE_POOLS_LOCAL_PATHS') || "/mnt/stabile/images";
    my @tenderpathslist = split(/,\s*/, $tenderpaths);

    $networkid1 = $networkreg{$networkuuid1}->{'id'};
    my $networktype1 = $networkreg{$networkuuid1}->{'type'};
    my $networktype2;
    if (!$nicmac1 || $nicmac1 eq "--") {$nicmac1 = randomMac();}
    if ($networkuuid2 && $networkuuid2 ne "--") {
        $networkid2 = $networkreg{$networkuuid2}->{'id'};
        $nicmac2 = randomMac() if (!$nicmac2 || $nicmac2 eq "--");
        $networktype2 = $networkreg{$networkuuid2}->{'type'};
    }
    if ($networkuuid3 && $networkuuid3 ne "--") {
        $networkid3 = $networkreg{$networkuuid3}->{'id'};
        $networkname3 = $networkreg{$networkuuid3}->{'name'};
        $nicmac3 = randomMac() if (!$nicmac3 || $nicmac3 eq "--");
        $networktype3 = $networkreg{$networkuuid3}->{'type'};
    }

    my $imgdup;
    my $netdup;
    my $json_text; # returned if all goes well

    unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {return "Unable to access images register"};

    if ($networkid1 > 1 && $networkid2 > 1 && $networktype1 ne 'gateway' && $networktype2 ne 'gateway'
        && $networkuuid1 eq $networkuuid2) {
        $netdup = 1;
    }
    if ($networkid1 > 1 && $networkid3 > 1 && $networktype1 ne 'gateway' && $networktype3 ne 'gateway'
        && $networkuuid1 eq $networkuuid3) {
        $netdup = 11;
    }

    if ($image eq $image2
        || $image eq $image3
        || $image eq $image4
        || $image2 && $image2 ne '--' && $image2 eq $image3
        || $image2 && $image2 ne '--' && $image2 eq $image4
        || $image3 && $image3 ne '--' && $image3 eq $image4
    ) {
        $imgdup = 1;
    } elsif ($image =~ m/\.master\.qcow2/
        || $image2 =~ m/\.master\.qcow2/
        || $image3 =~ m/\.master\.qcow2/
        || $image4 =~ m/\.master\.qcow2/
    ) {
        $imgdup = 2;
    } else {
        # Check if another server is using image
        my @regkeys = (tied %register)->select_where("user = '$user' OR user = 'common'");
        foreach my $k (@regkeys) {
            my $val = $register{$k};
            my %h = %$val;
            if ($h{'uuid'} ne $uuid) {
                if (
                    $image eq $h{'image'} || $image eq $h{'image2'}|| $image eq $h{'image3'}|| $image eq $h{'image4'}
                ) {
                    $imgdup = 51;
                } elsif ($image2 && $image2 ne "--" &&
                    ($image2 eq $h{'image'} || $image2 eq $h{'image2'} || $image2 eq $h{'image3'} || $image2 eq $h{'image4'})
                ) {
                    $imgdup = 52;
                } elsif ($image3 && $image3 ne "--" &&
                    ($image3 eq $h{'image'} || $image3 eq $h{'image2'} || $image3 eq $h{'image3'} || $image3 eq $h{'image4'})
                ) {
                    $imgdup = 53;
                } elsif ($image4 && $image4 ne "--" &&
                    ($image4 eq $h{'image'} || $image4 eq $h{'image2'} || $image4 eq $h{'image3'} || $image4 eq $h{'image4'})
                ) {
                    $imgdup = 54;
                }

                if ($networkid1>1) {
                    if ($networktype1 ne 'gateway' &&
                        ($networkuuid1 eq $h{'networkuuid1'} || $networkuuid1 eq $h{'networkuuid2'})
                    ) {
                        $netdup = 51;
                    }
                }
                if ($networkid2>1) {
                    if ($networktype2 ne 'gateway' && $networkuuid2 && $networkuuid2 ne "--" &&
                        ($networkuuid2 eq $h{'networkuuid1'} || $networkuuid2 eq $h{'networkuuid2'})
                    ) {
                        $netdup = 52;
                    }
                }
            }
        }
        my $legalpath;
        if ($image =~ m/\/mnt\/stabile\/node\/$user/) {
            $legalpath = 1;
        } else {
            foreach my $path (@tenderpathslist) {
                if ($image =~ m/$path\/$user/) {
                    $legalpath = 1;
                    last;
                }
            }
        }
        $imgdup = 6 unless $legalpath;
        if ($image2 && $image2 ne "--") { # TODO: We should probably check for conflicting nodes for image3 and image 4 too
            if ($image2 =~ m/\/mnt\/stabile\/node\/$user/) {
                if ($image =~ m/\/mnt\/stabile\/node\/$user/) {
                    if ($imagereg{$image}->{'mac'} eq $imagereg{$image2}->{'mac'}) {
                        $legalpath = 1;
                    } else {
                        $legalpath = 0; # Images are on two different nodes
                    }
                } else {
                    $legalpath = 1;
                }
            } else {
                $legalpath = 0;
                foreach my $path (@tenderpathslist) {
                    if ($image2 =~ m/$path\/$user/) {
                        $legalpath = 1;
                        last;
                    }
                }
            }
            $imgdup = 7 unless $legalpath;
        }
    }

    if (!$imgdup && !$netdup) {
        if ($status eq "new") {
            $status = "shutoff";
            $name = $name || 'New Server';
            $memory = $memory || 1024;
            $vcpu = $vcpu || 1;
            $imagename = $imagename || '--';
            $image2 = $image2 || '--';
            $image2name = $image2name || '--';
            $image3 = $image3 || '--';
            $image3name = $image3name || '--';
            $image4 = $image4 || '--';
            $image4name = $image4name || '--';
            $diskbus = $diskbus || 'ide';
            $cdrom = $cdrom || '--';
            $boot = $boot || 'hd';
            $networkuuid1 = $networkuuid1 || 1;
            $networkid1 = $networkid1 || 1;
            $networkname1 = $networkname1 || '--';
            $nicmodel1 = $nicmodel1 || 'rtl8139';
            $nicmac1 = $nicmac1 || randomMac();
            $networkuuid2 = $networkuuid2 || '--';
            $networkid2 = $networkid2 || '--';
            $networkname2 = $networkname2 || '--';
            $nicmac2 = $nicmac2 || randomMac();
            $networkuuid3 = $networkuuid3 || '--';
            $networkid3 = $networkid3 || '--';
            $networkname3 = $networkname3 || '--';
            $nicmac3 = $nicmac3 || randomMac();
            #    $uiuuid = $uuid; # No need to update ui for new server with jsonreststore
            $postmsg .= "OK Created new server: $name";
            $postmsg .= ", uuid: $uuid " if ($console);
        }
        # Update status of images
        my @imgs = ($image, $image2, $image3, $image4);
        my @imgkeys = ('image', 'image2', 'image3', 'image4');
        for (my $i=0; $i<4; $i++) {
            my $img = $imgs[$i];
            my $k = $imgkeys[$i];
            my $regimg = $imagereg{$img};
            # if ($img && $img ne '--' && ($status eq 'new' || $img ne $regserv->{$k})) { # Servers image changed - update image status
            if ($img && $img ne '--') { # Always update image status
                $regimg->{'status'} = 'used' if (
                    $regimg->{'status'} eq 'unused'
                        # Image cannot be active if server is shutoff
                        || ($regimg->{'status'} eq 'active' && $status eq 'shutoff')
                );
                $regimg->{'domains'} = $uuid;
                $regimg->{'domainnames'} = $name;
            }
            # If image has changed, release the old image
            if ($status ne 'new' && $img ne $regserv->{$k} && $imagereg{$regserv->{$k}}) {
                $imagereg{$regserv->{$k}}->{'status'} = 'unused';
                delete $imagereg{$regserv->{$k}}->{'domains'};
                delete $imagereg{$regserv->{$k}}->{'domainnames'};
            }
        }

        my $valref = {
            uuid=>$uuid,
            user=>$user,
            name=>$name,
            memory=>$memory,
            vcpu=>$vcpu,
            image=>$image,
            imagename=>$imagename,
            image2=>$image2,
            image2name=>$image2name,
            image3=>$image3,
            image3name=>$image3name,
            image4=>$image4,
            image4name=>$image4name,
            diskbus=>$diskbus,
            cdrom=>$cdrom,
            boot=>$boot,
            networkuuid1=>$networkuuid1,
            networkid1=>$networkid1,
            networkname1=>$networkname1,
            nicmodel1=>$nicmodel1,
            nicmac1=>$nicmac1,
            networkuuid2=>$networkuuid2,
            networkid2=>$networkid2,
            networkname2=>$networkname2,
            nicmac2=>$nicmac2,
            networkuuid3=>$networkuuid3,
            networkid3=>$networkid3,
            networkname3=>$networkname3,
            nicmac3=>$nicmac3,
            status=>$status,
            notes=>$notes,
            autostart=>$autostart,
            locktonode=>$locktonode,
            action=>"",
            created=>$created
        };
        $valref->{'system'} = $system if ($system);
        if ($mac && $locktonode eq 'true') {
            $valref->{'mac'} = $mac;
            $valref->{'macip'} = $nodereg{$mac}->{'ip'};
            $valref->{'macname'} = $nodereg{$mac}->{'name'};
        }
        if ($newsystem) {
            my $ug = new Data::UUID;
            $sysuuid = $ug->create_str();
            $valref->{'system'} = $sysuuid;
            $postmsg .= "OK sysuuid: $sysuuid " if ($console);
        }

        # Remove domain uuid from old networks. Leave gateways alone - they get updated on next listing
        my $oldnetworkuuid1 = $regserv->{'networkuuid1'};
        if ($oldnetworkuuid1 ne $networkuuid1 && $networkreg{$oldnetworkuuid1}) {
            $networkreg{$oldnetworkuuid1}->{'domains'} =~ s/($uuid)(,?)( ?)//;
        }

        $register{$uuid} = validateItem($valref);

        if ($networkreg{$networkuuid1}->{'type'} eq 'gateway') {
            my $domains = $networkreg{$networkuuid1}->{'domains'};
            $networkreg{$networkuuid1}->{'domains'} = ($domains?"$domains, ":"") . $uuid;
            my $domainnames = $networkreg{$networkuuid1}->{'domainnames'};
            $networkreg{$networkuuid1}->{'domainnames'} = ($domainnames?"$domainnames, ":"") . $name;
        } else {
            $networkreg{$networkuuid1}->{'domains'}  = $uuid;
            $networkreg{$networkuuid1}->{'domainnames'}  = $name;
        }

        if ($networkuuid2 && $networkuuid2 ne '--') {
            if ($networkreg{$networkuuid2}->{'type'} eq 'gateway') {
                my $domains = $networkreg{$networkuuid2}->{'domains'};
                $networkreg{$networkuuid2}->{'domains'} = ($domains?"$domains, ":"") . $uuid;
                my $domainnames = $networkreg{$networkuuid2}->{'domainnames'};
                $networkreg{$networkuuid2}->{'domainnames'} = ($domainnames?"$domainnames, ":"") . $name;
            } else {
                $networkreg{$networkuuid2}->{'domains'}  = $uuid;
                $networkreg{$networkuuid2}->{'domainnames'}  = $name;
            }
        }

        if ($networkuuid3 && $networkuuid3 ne '--') {
            if ($networkreg{$networkuuid3}->{'type'} eq 'gateway') {
                my $domains = $networkreg{$networkuuid3}->{'domains'};
                $networkreg{$networkuuid3}->{'domains'} = ($domains?"$domains, ":"") . $uuid;
                my $domainnames = $networkreg{$networkuuid3}->{'domainnames'};
                $networkreg{$networkuuid3}->{'domainnames'} = ($domainnames?"$domainnames, ":"") . $name;
            } else {
                $networkreg{$networkuuid3}->{'domains'}  = $uuid;
                $networkreg{$networkuuid3}->{'domainnames'}  = $name;
            }
        }
        my %jitem = %{$register{$uuid}};
        $json_text = to_json(\%jitem, {pretty=>1});
        $json_text =~ s/null/"--"/g;
        $uiuuid = $uuid;
        $uiname = $name;

        tied(%register)->commit;
        tied(%imagereg)->commit;
        tied(%networkreg)->commit;

    } else {
        $postmsg .= "ERROR This image ($image) cannot be used ($imgdup) " if ($imgdup);
        $postmsg .= "ERROR This network ($networkname1) cannot be used ($netdup)" if ($netdup);
    }

    my $domuser = $obj->{'user'};
    # We were asked to move server to another account
    if ($domuser && $domuser ne '--' && $domuser ne $user) {
        unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>0}, $Stabile::dbopts)) ) {throw Error::Simple("Stroke=Error User register could not be  accessed")};
        if ($status eq 'shutoff' || $status eq 'inactive') {
            unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>1}, $Stabile::dbopts)) ) {$posterror =  "Unable to access user register"; return 0;};
            my @accounts = split(/,\s*/, $userreg{$tktuser}->{'accounts'});
            my @accountsprivs = split(/,\s*/, $userreg{$tktuser}->{'accountsprivileges'});
            %ahash = ($tktuser, $userreg{$tktuser}->{'privileges'}); # Include tktuser in accounts hash
            for my $i (0 .. scalar @accounts)
            {
                next unless $accounts[$i];
                $ahash{$accounts[$i]} = $accountsprivs[$i] || 'r';
            }
            untie %userreg;

            if (!$isreadonly && $ahash{$domuser} && !($ahash{$domuser} =~ /r/)) { # Check if user is allow to access account
                my $imgdone;
                my $netdone;
                # First move main image
                $Stabile::Images::user = $user;
                require "$Stabile::basedir/cgi/images.cgi";
                $Stabile::Images::console = 1;
                $main::updateUI->({tab=>"servers", user=>$user, message=>"Moving image $imagename to account: $domuser"});
                my $nimage = Stabile::Images::Move($image, $domuser);
                chomp $nimage;
                if ($nimage) {
                    $main::syslogit->($user, "info", "Moving $nimage to account: $domuser");
                    $register{$uuid}->{'image'} = $nimage;
                    $imgdone = 1;
                } else {
                    $main::syslogit->($user, "info", "Unable to move image $imagename to account: $domuser");
                }
                # Move other attached images
                my @images = ($image2, $image3, $image4);
                my @imagenames = ($image2name, $image3name, $image4name);
                my @imagekeys = ('image2', 'image3', 'image4');
                for (my $i=0; $i<3; $i++) {
                    my $img = $images[$i];
                    my $imgname = $imagenames[$i];
                    my $imgkey = $imagekeys[$i];
                    if ($img && $img ne '--') {
                        $main::updateUI->({tab=>"servers", user=>$user, message=>"Moving $imgkey $imgname to account: $domuser"});
                        $nimage = Stabile::Images::Move($img, $domuser);
                        chomp $nimage;
                        if ($nimage) {
                            $main::syslogit->($user, "info", "Moving $nimage to account: $domuser");
                            $register{$uuid}->{$imgkey} = $nimage;
                        } else {
                            $main::syslogit->($user, "info", "Unable to move $imagekeys[$i] $img to account: $domuser");
                        }
                    }
                }
                # Then move network(s)
                if ($imgdone) {
                    $Stabile::Networks::user = $user;
                    require "$Stabile::basedir/cgi/networks.cgi";
                    $Stabile::Networks::console = 1;
                    my @networks = ($networkuuid1, $networkuuid2, $networkuuid3);
                    my @netkeys = ('networkuuid1', 'networkuuid2', 'networkuuid3');
                    my @netnamekeys = ('networkname1', 'networkname2', 'networkname3');
                    for (my $i=0; $i<scalar @networks; $i++) {
                        my $net = $networks[$i];
                        my $netkey = $netkeys[$i];
                        my $netnamekey = $netnamekeys[$i];
                        my $regnet = $networkreg{$net};
                        my $oldid = $regnet->{'id'};
                        next if ($net eq '' || $net eq '--');
                        if ($regnet->{'type'} eq 'gateway') {
                            if ($oldid > 1) { # Private gateway
                                foreach my $networkvalref (values %networkreg) { # use gateway with same id if it exists
                                    if ($networkvalref->{'user'} eq $domuser
                                        && $networkvalref->{'type'} eq 'gateway'
                                        && $networkvalref->{'id'} == $oldid) {
                                        # We found an existing gateway with same id - use it
                                        $register{$uuid}->{$netkey} = $networkvalref->{'uuid'};
                                        $register{$uuid}->{$netnamekey} = $networkvalref->{'name'};
                                        $netdone = 1;
                                        $main::updateUI->({tab=>"networks", user=>$user, message=>"Using network $networkvalref->{'name'} from account: $domuser"});
                                        last;
                                    }
                                }
                                if (!($netdone)) {
                                    # Make a new gateway
                                    my $ug = new Data::UUID;
                                    my $newuuid = $ug->create_str();
                                    Stabile::Networks::save($oldid, $newuuid, $regnet->{'name'}, 'new', 'gateway', '', '', $regnet->{'ports'}, 0, $domuser);
                                    $register{$uuid}->{$netkey} = $newuuid;
                                    $register{$uuid}->{$netnamekey} = $regnet->{'name'};
                                    $netdone = 1;
                                    $main::updateUI->({tab=>"networks", user=>$user, message=>"Created gateway $regnet->{'name'} for account: $domuser"});
                                    $main::syslogit->($user, "info", "Created gateway $regnet->{'name'} for account: $domuser");
                                }
                            } elsif ($oldid==0 || $oldid==1) {
                                $netdone = 1; # Use common gateway
                                $main::updateUI->({tab=>"networks", user=>$user, message=>"Reused network $regnet->{'name'} for account: $domuser"});
                            }
                        } else {
                            my $newid = Stabile::Networks::getNextId('', $domuser);
                            $networkreg{$net}->{'id'} = $newid;
                            $networkreg{$net}->{'user'} = $domuser;
                        #    if ($regnet->{'type'} eq 'internalip' || $regnet->{'type'} eq 'ipmapping') {
                                # Deactivate network and assign new internal ip
                                Stabile::Networks::Deactivate($regnet->{'uuid'});
                                $networkreg{$net}->{'internalip'} =
                                    Stabile::Networks::getNextInternalIP('',$regnet->{'uuid'}, $newid, $domuser);
                        #    }
                            $netdone = 1;
                            $main::updateUI->({tab=>"networks", user=>$user, message=>"Moved network $regnet->{'name'} to account: $domuser"});
                            $main::syslogit->($user, "info", "Moved network $regnet->{'name'} to account: $domuser");
                        }
                    }
                    if ($netdone) {
                        # Finally move the server
                        $register{$uuid}->{'user'} = $domuser;
                        $postmsg .= "OK Moved server $name to account: $domuser";
                        $main::syslogit->($user, "info", "Moved server $name ($uuid) to account: $domuser");
                        $main::updateUI->({tab=>"servers", user=>$user, type=>"update"});
                    } else {
                        $postmsg .= "ERROR Unable to move network to account: $domuser";
                        $main::updateUI->({tab=>"image", user=>$user, message=>"Unable to move network to account: $domuser"});
                    }
                } else {
                    $main::updateUI->({tab=>"image", user=>$user, message=>"Could not move image to account: $domuser"});
                }
            } else {
                $postmsg .= "ERROR No access to move server";
            }
        } else {
            $postmsg .= "Error Unable to move $status server";
            $main::updateUI->({tab=>"servers", user=>$user, message=>"Please shut down before moving server"});
        }
        untie %userreg;
    }

    if ($console) {
        $postreply = $postmsg;
    } else {
        $postreply = $json_text || $postmsg;
    }
    return $postreply;
    untie %imagereg;
}


sub Shutdown {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
Marks a server for shutdown, i.e. send and ACPI shutdown event to the server. If OS supports ACPI, it begins a shutdown.
END
    }
    $uistatus = "shuttingdown";
    my $dbstatus = $obj->{status};
    my $mac = $obj->{mac};
    my $macname = $obj->{macname};
    my $name = $obj->{name};
    if ($dbstatus eq 'running') {
        my $tasks;
        $tasks = $nodereg{$mac}->{'tasks'} if ($nodereg{$mac});
        $nodereg{$mac}->{'tasks'} = $tasks . "SHUTDOWN $uuid $user\n";
        tied(%nodereg)->commit;
        $register{$uuid}->{'status'} = $uistatus;
        $register{$uuid}->{'statustime'} = $current_time;
        $uiuuid = $uuid;
        $main::syslogit->($user, "info", "Marked $name ($uuid) for $uistatus by $macname ($mac)");
        $postreply .= "Status=$uistatus OK $uistatus $name\n";
    } else {
        $main::syslogit->($user, "info", "Problem $uistatus a $dbstatus domain: $uuid");
        $postreply .= "Status=ERROR problem $uistatus $name...\n";
    }
    return $postreply;
}

sub Suspend {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
Marks a server for suspend, i.e. pauses the server. Server must be running
END
    }
#    my $obj = getObj(('uuid', $uuid));
    $uistatus = "suspending";
    my $dbstatus = $obj->{status};
    my $mac = $obj->{mac};
    my $macname = $obj->{macname};
    my $name = $obj->{name};
    if ($dbstatus eq 'running') {
        my $tasks = $nodereg{$mac}->{'tasks'};
        $nodereg{$mac}->{'tasks'} = $tasks . "SUSPEND $uuid $user\n";
        tied(%nodereg)->commit;
        $register{$uuid}->{'status'} = $uistatus;
        $register{$uuid}->{'statustime'} = $current_time;
        $uiuuid = $uuid;
        $main::syslogit->($user, "info", "Marked $name ($uuid) for $uistatus by $macname ($mac)");
        $postreply .= "Status=$uistatus OK $uistatus $name.\n";
    } else {
        $main::syslogit->($user, "info", "Problem $uistatus a $dbstatus domain: $uuid");
        $postreply .= "Status=ERROR problem $uistatus $name.\n";
    }
    return $postreply;
}

sub Resume {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid:
Marks a server for resume running. Server must be paused.
END
    }
    my $dbstatus = $obj->{status};
    my $mac = $obj->{mac};
    my $macname = $obj->{macname};
    my $name = $obj->{name};
    my $image = $obj->{image};
    my $image2 = $obj->{image2};
    my $image3 = $obj->{image3};
    my $image4 = $obj->{image4};
    unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {$posterror = "Unable to access image register"; return;};
    if ($imagereg{$image}->{'status'} ne "paused"
        || ($image2 && $image2 ne '--' && $imagereg{$image}->{'status'} ne "paused")
        || ($image3 && $image3 ne '--' && $imagereg{$image3}->{'status'} ne "paused")
        || ($image4 && $image4 ne '--' && $imagereg{$image4}->{'status'} ne "paused")
    ) {
        $postreply .= "Status=ERROR Image $uuid busy ($imagereg{$image}->{'status'}), please wait 30 sec.\n";
        untie %imagereg;
        return $postreply   ;
    } else {
        untie %imagereg;
    }
    $uistatus = "resuming";
    if ($dbstatus eq 'paused') {
        my $tasks = $nodereg{$mac}->{'tasks'};
        $nodereg{$mac}->{'tasks'} = $tasks . "RESUME $uuid $user\n";
        tied(%nodereg)->commit;
        $register{$uuid}->{'status'} = $uistatus;
        $register{$uuid}->{'statustime'} = $current_time;
        $uiuuid = $uuid;
        $main::syslogit->($user, "info", "Marked $name ($uuid) for $uistatus by $macname ($mac)");
        $postreply .= "Status=$uistatus OK $uistatus ". $register{$uuid}->{'name'} . "\n";
    } else {
        $main::syslogit->($user, "info", "Problem $uistatus a $dbstatus domain: $uuid");
        $postreply .= "Status=ERROR problem $uistatus ". $register{$uuid}->{'name'} . "\n";
    }
    return $postreply;
}

sub Move {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,mac:
Moves a server to a different node (Qemu live migration). Server must be running
END
    }
    my $dbstatus = $obj->{status};
    my $dmac = $obj->{mac};
    my $name = $obj->{name};
    my $mem = $obj->{memory};
    my $vcpu = $obj->{vcpu};
    my $image = $obj->{image};
    my $image2 = $obj->{image2};
    my $image3 = $obj->{image3};
    my $image4 = $obj->{image4};
    $uistatus = "moving";
    if ($dbstatus eq 'running' && $isadmin) {
        my $hypervisor = getHypervisor($image);
        my $mac = $register{$uuid}->{'mac'};
        $dmac = "" if ($dmac eq "--");
        $mac = "" if ($mac eq "--");

        if ($image =~ /\/mnt\/stabile\/node\//
            || $image2 =~ /\/mnt\/stabile\/node\//
            || $image3 =~ /\/mnt\/stabile\/node\//
            || $image4 =~ /\/mnt\/stabile\/node\//
        ) {
            # We do not support moving locally stored VM's yet...
            $postreply = qq|{"error": 1, "message": "Moving servers with local storage not supported"}|;
        } else {
            my ($targetmac, $targetname, $targetip, $port) =
                locateTargetNode($uuid, $dmac, $mem, $vcpu, $image, $image2, $image3, $image4, $hypervisor, $mac);
            if ($targetmac) {
                my $tasks = $nodereg{$targetmac}->{'tasks'};
                $tasks = $tasks . "RECEIVE $uuid $user\n";
                # Also update allowed port forwards
                $nodereg{$targetmac}->{'tasks'} = $tasks . "PERMITOPEN $user\n";
                $register{$uuid}->{'status'} = "moving";
                $register{$uuid}->{'statustime'} = $current_time;
                $uiuuid = $uuid;
                $uidisplayip = $targetip;
                $uidisplayport = $port;
                $main::syslogit->($user, "info", "Marked $name ($uuid) for $uistatus to $targetname ($targetmac)");
                $postreply .= "Status=OK $uistatus ". $register{$uuid}->{'name'} . "\n";

                if ($params{'PUTDATA'}) {
                    my %jitem = %{$register{$uuid}};
                    my $json_text = to_json(\%jitem);
                    $json_text =~ s/null/"--"/g;
                    $postreply = $json_text;
                }
                $main::updateUI->({tab=>"servers", user=>$user, status=>'moving', uuid=>$uuid, type=>'update', message=>"Moving $register{$uuid}->{name} to $targetmac"});
            } else {
                $main::syslogit->($user, "info", "Could not find $hypervisor target for $uistatus $uuid ($image)");
                $postreply = qq|{"error": 1, "message": "Could not find target for $uistatus $register{$uuid}->{'name'}"}|;
            }
        }
    } else {
        $main::syslogit->($user, "info", "Problem moving a $dbstatus domain: $uuid");
        $postreply .= qq|{"error": 1, "message": "ERROR problem moving $register{$uuid}->{'name'} ($dbstatus)"}|;
    }
    return $postreply;
}

sub Changepassword {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
POST:uuid,username,password:
Attempts to set password for [username] to [password] using guestfish. If no username is specified, user 'stabile' is assumed.
END
    }
    my $img = $register{$uuid}->{'image'};
    my $username = $obj->{'username'} || 'stabile';
    my $password = $obj->{'password'};
    return "Status=Error Please supply a password\n" unless ($password);
    return "Status=Error Please shut down the server before changing password\n" unless ($register{$uuid} && $register{$uuid}->{'status'} eq 'shutoff');
    return "Status=Error Not allowed\n" unless ($isadmin || $register{$uuid}->{'user'} eq $user);

    unless (tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access images register"}|; return $res;};
    my $cmd = qq/guestfish --rw -a $img -i command "bash -c 'echo $username:$password | chpasswd'" 2>\&1/;
    if ($imagereg{$img} && $imagereg{$img}->{'mac'}) {
        my $mac = $imagereg{$img}->{'mac'};
        my $macip = $nodereg{$mac}->{'ip'};
        $cmd = "$sshcmd $macip $cmd";
    }
    my $res = `$cmd`;
    $res = $1 if ($res =~ /guestfish: (.*)/);
    chomp $res;
    return "Status=OK Ran chpasswd for user $username in server $register{$uuid}->{'name'}: $res\n";
}

sub Sshaccess {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
POST:uuid,address:
Attempts to change the ip addresses you can access the server over SSH (port 22) from, by adding [address] to /etc/hosts.allow.
[address] should either be an IP address or a range in CIDR notation. Please note that no validation of [address] is performed.
END
    }
    my $img = $register{$uuid}->{'image'};
    my $address = $obj->{'address'};
    return "Status=Error Please supply an aaddress\n" unless ($address);
    return "Status=Error Please shut down the server before changing SSH access\n" unless ($register{$uuid} && $register{$uuid}->{'status'} eq 'shutoff');
    return "Status=Error Not allowed\n" unless ($isadmin || $register{$uuid}->{'user'} eq $user);

    unless (tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access images register"}|; return $res;};

    my $isshcmd = '';
    my $cmd = qq[guestfish --rw -a $img -i command "sed -i -re 's|(sshd: .*)#stabile|\\1 $address #stabile|' /etc/hosts.allow"];
#    my $cmd = qq[guestfish --rw -a $img -i command "bash -c 'echo sshd: $address >> /etc/hosts.allow'"];
    if ($imagereg{$img} && $imagereg{$img}->{'mac'}) {
        my $mac = $imagereg{$img}->{'mac'};
        my $macip = $nodereg{$mac}->{'ip'};
        $isshcmd = "$sshcmd $macip ";
    }
    my $res = `$isshcmd$cmd`;
    chomp $res;
    #$cmd = qq[guestfish --rw -a $img -i command "bash -c 'cat /etc/hosts.allow'"];
    #$res .= `$isshcmd$cmd`;
    #chomp $res;
    return "Status=OK Tried to add sshd: $address to /etc/hosts.allow in server $register{$uuid}->{'name'}\n";
}

sub Mountcd {
    my ($uuid, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:uuid,cdrom:
Mounts a cdrom on a server. Server must be running. Mounting the special cdrom named '--' unomunts any currently mounted cdrom.
END
    }
    my $dbstatus = $obj->{status};
    my $mac = $obj->{mac};
    my $cdrom = $obj->{cdrom};
    unless ($cdrom && $dbstatus eq 'running') {
        $main::updateUI->({tab=>"servers", user=>$user, uuid=>$uuid, type=>'update', message=>"Unable to mount cdrom"});
        $postreply = qq|{"Error": 1, "message": "Problem mounting cdrom on $obj->{name}"}|;
        return;
    }
    my $tasks = $nodereg{$mac}->{'tasks'};
    # $user is in the middle here, because $cdrom may contain spaces...
    $nodereg{$mac}->{'tasks'} = $tasks . "MOUNT $uuid $user \"$cdrom\"\n";
    tied(%nodereg)->commit;
    if ($cdrom eq "--") {
        $postreply = qq|{"OK": 1, "message": "OK unmounting cdrom from $obj->{name}"}|;
    } else {
        $postreply = qq|{"OK": 1, "message": "OK mounting cdrom $cdrom on $obj->{name}"}|;
    }
    $register{$uuid}->{'cdrom'} = $cdrom unless ($cdrom eq 'virtio');
    return $postreply;
}
