#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license

BEGIN {
    open STDERR, '>>', '/dev/null' or die "Couldn't redirect STDERR: $!";
}

package Stabile::Piston;

use Error qw(:try);
use Socket;
use Data::UUID;
use File::Basename;
use Time::Local;
use Time::HiRes qw( time );
use LWP::Simple;
use lib dirname (__FILE__) . "/../cgi";
use Stabile;

$q = new CGI;
%params = $q->Vars;

my $servername = $ENV{'SERVER_NAME'};
$servername = "localhost" unless $servername;
my $serverip = scalar(inet_ntoa(inet_aton($servername)));

$backupdir = $Stabile::config->get('STORAGE_BACKUPDIR') || "/mnt/stabile/backups";
my $engineid = $Stabile::config->get('ENGINEID') || "";
#my $enginelinked = $Stabile::config->get('ENGINE_LINKED') || "";
$brutalsleep = $Stabile::config->get('BRUTAL_SLEEP') || "";
$amtpasswd = $Stabile::config->get('AMT_PASSWD') || "";

try {
	my $logentry = "";
	my @keys = keys %params;
	my @values = values %params;
	while ($#keys >= 0)
	{
		$key = pop(@keys); $value = pop(@values);
		$logentry .= "$key: $value; ";
	}
	$logentry .= "REMOTE_ADDR: $ENV{'REMOTE_ADDR'}; Time: $current_time";
	# $main::syslogit->('--', 'debug', $logentry);

	my $status = $params{'status'};
	my ($user, $uitab, $uiuuid, $uistatus, $plogentry) = split(/: /, uri_unescape($params{'logentry'}));
	my $uipath;

# We got a request for clearing the local log file
	if ($status eq "clearlog") {
		unlink $logfile;
		print "\nStatus=OK Log cleared\n";
		print end_html(), "\n";
		return;
	}

    my $mac = uri_unescape($params{'mac'});
	$mac =~ tr/[A-Z]/[a-z]/;
	$mac =~ s/:/-/g;	
	unless ($status eq 'permitopen' || $status eq 'listimagemaster' || $mac =~ /^(\S{2}-\S{2}-\S{2}-\S{2}-\S{2}-\S{2})$/) {throw Error::Simple ("Status=Error invalid mac address: $mac for $id $ENV{'REMOTE_ADDR'}")};
	my $filename = $1; # $filename now untainted
	my $file = "/mnt/stabile/tftp/pxelinux.cfg/01-$filename";
	$mac =~ s/-//g;

	my $ipmiip;
	$ipmiip = uri_unescape($params{'ipmiip'}) if ($params{'ipmiip'});
	
	unless (tie %register,'Tie::DBI', {
		db=>'mysql:steamregister',
		table=>'nodes',
		key=>'mac',
		autocommit=>0,
		CLOBBER=>3,
		user=>$dbiuser,
		password=>$dbipasswd}) {throw Error::Simple("Status=Error Register could not be accessed")};

	unless (tie %domreg,'Tie::DBI', {
		db=>'mysql:steamregister',
		table=>'domains',
		key=>'uuid',
		autocommit=>0,
		CLOBBER=>3,
		user=>$dbiuser,
		password=>$dbipasswd}) {throw Error::Simple("Status=Error Register could not be accessed")};

    unless (tie %imagereg,'Tie::DBI', {
        db=>'mysql:steamregister',
        table=>'images',
        key=>'path',
        autocommit=>0,
        CLOBBER=>3,
        user=>$dbiuser,
        password=>$dbipasswd}) {throw Error::Simple("Status=Image register could not be accessed")};

	unless (tie %idreg,'Tie::DBI', {
		db=>'mysql:steamregister',
		table=>'nodeidentities',
		key=>'identity',
		autocommit=>0,
		CLOBBER=>3,
		user=>$dbiuser,
		password=>$dbipasswd}) {throw Error::Simple("Status=Error Register could not be accessed")};

	if ($uiuuid) {
        if ($uitab eq 'images' && $imagereg{$uiuuid}) { # We got a path
            $uipath = $uiuuid;
            $uiuuid = $imagereg{$uipath}->{'uuid'};
        } else {
            $uiuuid =~ tr/[A-Z]/[a-z]/;
            $uiuuid =~ s/\%3a//g;
        }
	} else {
        $uiuuid = $mac;
	}


	if ($status eq "joining" && $mac) {
		print header(),
		     start_html('Updating Stabile node...'),
		     h1('Examining piston request...'),
		     hr;
		# A new node is trying to join
		# First find out which kind of nodes are needed

		my $id = $idreg{'default'}->{'hypervisor'};
		my $dist = $idreg{'default'}->{'dist'};
		my $path = $idreg{'default'}->{'path'};
		my $kernel = $idreg{'default'}->{'kernel'};
        $kernel = "-$kernel" if ($kernel);
#		untie %idreg;
		my $bootentry;
		
		unless ($dist) {$dist = "lucid"};

		unless (open(TEMP2, ">$file")) {throw Error::Simple("Status=Error boot file \"$file\" could not be created")};
		if ($dist eq 'lucid') {
			$bootentry = <<ENDBOOT;
prompt 0
default Stabile Node
label Stabile Node
kernel vmlinuz$kernel
ipappend 2
append initrd=initrd.img$kernel ro nomodeset root=/dev/nfs nfsroot=$serverip:$path netboot=nfs union=aufs boot=live ip=dhcp identity=$id acpi=force console=ttyS4,115200n81 console=ttyS1,115200n81 console=tty0 ipv6.disable=1 intel_iommu=on
ENDBOOT

    		print TEMP2 $bootentry . "\n";
	    	close(TEMP2);
		} elsif ($dist) {
			$bootentry = <<ENDBOOT;
prompt 0
default Stabile Node
label Stabile Node
kernel vmlinuz$kernel
ipappend 2
append initrd=initrd.img$kernel ro nomodeset root=/dev/nfs nfsroot=$serverip:$path netboot=nfs union=aufs boot=casper ip=dhcp identity=$id acpi=force console=ttyS4,115200n81 console=ttyS1,115200n81 console=tty0 ipv6.disable=1 intel_iommu=on disable_mtrr_cleanup
ENDBOOT

			print TEMP2 $bootentry . "\n";
			close(TEMP2);
		} else {throw Error::Simple("Status=Error no default node identity")};

		$register{$mac} = {
            identity=>$id,
            timestamp=>$current_time,
            ip=>$ENV{'REMOTE_ADDR'},
            name=>$mac,
            cpucores=>$params{'cpucores'},
            cpucount=>$params{'cpucount'},
            cpuspeed=>$params{'cpuspeed'},
            cpuname=>uri_unescape($params{'cpuname'}),
            cpufamily=>$params{'cpufamily'},
            cpumodel=>$params{'cpumodel'},
            memtotal=>$params{'memtotal'},
            memfree=>$params{'memfree'},
            stortotal=>$params{'stortotal'},
            storfree=>$params{'storfree'},
            status=>$status,
            ipmiip=>$ipmiip
		};
		tied(%register)->commit;
		print "\nAssimilation=OK $mac\n";
		print end_html(), "\n";

# We got a request for updating a user's UI
	} elsif ($status eq "updateui") {
		print header();
		if ($user && $uitab eq "images" && $uiuuid && !($uistatus =~ /backingup/)) {
            $imagereg{$uipath}->{'status'} = $uistatus;
            tied(%imagereg)->commit();
            if ($plogentry =~ /Backed up/) { # An image was backed up from the node
                $imagereg{$uipath}->{'btime'} = $current_time;
                my $imguser = $imagereg{$uipath}->{'user'};
                my($fname, $dirpath, $suffix) = fileparse($uipath, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));
                my $subdir = "";
                if ($dirpath =~ /\/$user(\/.+)\//) {
                    $subdir = $1;
                }
                my $backupsize = getBackupSize($subdir, "$fname$suffix", $imguser);
                updateImageBilling($user, $uipath, "backed up", $backupsize);
            }
            if ($plogentry) {
				if ($plogentry =~ /Backup aborted/) {
					# A backup has been aborted - possibly a node was rebooted - update image status
					$Stabile::Images::user = $user;
					$Stabile::Images::console = 1;
					require "$Stabile::basedir/cgi/images.cgi";
					my $res = Stabile::Images::Updateregister($uipath, 'updateregister');
					$main::syslogit->($user, 'info', "Updated image status - $user, $uipath, $res");
					$uistatus = $res if ($res);
				}
				my $upd = {user=>$user, uuid=>$uiuuid, status=>$uistatus, message=>$plogentry, type=>'update', tab=>'images'};
				$upd->{'backup'} = $uipath if ($plogentry =~ /Backed up/);
				$main::updateUI->($upd);
                $main::syslogit->($user, 'info', "$plogentry $uiuuid ($uitab, $uistatus)");
                $plogentry = "";
            }
        }
# List the master associated with an image if any
	} elsif ($status eq "listimagemaster") {
		print header('text/xml');
		my $path = $params{'image'};
		$path = uri_unescape($path);
		my $master = $imagereg{$path}->{'master'};
		$master = uri_escape($master);
        print $master;
# We got a request for listing a domains xml description
	} elsif ($status eq "listxml") {
		print header('text/xml');
		my %xmlreg;
		unless (tie %xmlreg,'Tie::DBI', {
			db=>'mysql:steamregister',
			table=>'domainxml',
			key=>'uuid',
			autocommit=>0,
			CLOBBER=>3,
			user=>$dbiuser,
			password=>$dbipasswd}) {throw Error::Simple("Status=Error Register could not be accessed")};

		my $uuid = $params{'uuid'};
		unless ((defined $uuid) && ($uuid =~ /^(\S{8}-\S{4}-\S{4}-\S{4}-\S{12})$/)) {throw Error::Simple ("Status=Error invalid uuid: $uuid")};
		my $xml = $xmlreg{$uuid}->{'xml'};
		print uri_unescape($xml);
		untie %xmlreg;

# Update sshd_config to allow ssh port forwarding to consoles of a users vm's
	} elsif ($status eq "permitopen") {
		print header;
		my $user = $params{'user'};
        $user =~ /(.+)/; $user = $1; #untaint
		print start_html('Opening ports...');
		permitOpen($user);
		print end_html();

# A node is updating it's status
	} else {
		print header(),
		     start_html('Updating Stabile node...'),
		     h1('Examining piston request...'),
		     hr;
		# Look for action requests (from users)
		$action = $register{$mac}->{'action'};

        # Look for node tasks, only post requests, get requests generally only update this side
        if ($ENV{'REQUEST_METHOD'} eq 'POST') {
            $tasks = $register{$mac}->{'tasks'};
            $register{$mac}->{'tasks'} = '';
            tied(%register)->commit;
#            chomp $tasks;
        }

		$maintenance = $register{$mac}->{'maintenance'};
		# If the node is shutting down or joining, don't reboot it
		if ($status eq "shutdown" || $status eq "joining") {
			$action = "";
		}
		my $dbstatus = $register{$mac}->{'status'};
		my $macname = $register{$mac}->{'name'};
		my $nodestatus = $status;
        $nodestatus = 'maintenance' if ($status eq 'running' && $maintenance);
		if (($dbstatus eq "maintenance" && $status ne "drowsing") || $dbstatus eq "sleeping" || $dbstatus eq "shuttingdown" || !$status || $status eq '--') {
            $nodestatus = $dbstatus;
		} elsif ( $status eq 'drowsing' && ($dbstatus eq 'running' || $dbstatus eq 'maintenance')) {
            if ($brutalsleep && (
                    ($register{$mac}->{'amtip'} && $register{$mac}->{'amtip'} ne '--')
                || ($register{$mac}->{'ipmiip'} && $register{$mac}->{'ipmiip'} ne '--')
                )) {
                my $sleepcmd;
                $uistatus = "asleep";
                print  "\nStatus=SWEETDREAMS";
                sleep 2;
                if ($register{$mac}->{'amtip'} && $register{$mac}->{'amtip'} ne '--') {
                    $sleepcmd = "echo 'y' | AMT_PASSWORD='$amtpasswd' /usr/bin/amttool $register{$mac}->{'amtip'} powerdown";
                } else {
                    $sleepcmd = "ipmitool -I lanplus -H $register{$mac}->{'ipmiip'} -U ADMIN -P ADMIN power off";
                }
                my $logmsg = "Node $mac marked for drowse ";
                $logmsg .= `$sleepcmd`;
                $logmsg =~ s/\n/ /g;
                $main::syslogit->('--', "info", $logmsg);
            }
            $nodestatus = 'asleep';
		}

        my %billing;

	# Look for info on whether if this node is waiting to receive vm's and activate the sender
        my $receive = uri_unescape($params{'receive'});
        if ($receive) {
            @uuids = split(/, */,$receive);
            foreach my $uuid (@uuids) {
                # Sender is the current node/mac running the vm
                my $sendmac = $domreg{$uuid}->{'mac'};
                my $rip = $register{$mac}->{'ip'};
                my $sendtasks = "MOVE $uuid $rip $mac $user\n". $register{$sendmac}->{'tasks'};
                chop $sendtasks;
                $register{$sendmac}->{'tasks'} .= $sendtasks;
            }
        }
        my $returntasks = uri_unescape($params{'returntasks'});
        if ($returntasks && $returntasks ne "--") {
            $register{$mac}->{'tasks'} .= $returntasks; # Some tasks have failed, try again
        }

        # Don't update anything for node feedbacks from actions
        if ($status ne '--'
            && $status ne 'asleep'
            && $status ne 'awake'
            && $status ne 'shutdown'
            && $status ne 'reboot'
            && $status ne 'unjoin'
            && $status ne 'permitopen'
            && $status ne 'reload'
        ) {
    # Update basic parameters
            my $memfree = $params{'memfree'} || $register{$mac}->{'memfree'};
            my $memtotal = $params{'memtotal'} || $register{$mac}->{'memtotal'};
            my $cpuload = $params{'cpuload'} || $register{$mac}->{'cpuload'};
            my $cpucount = $params{'cpucount'} || $register{$mac}->{'cpucount'};
            my $cpucores = $params{'cpucores'} || $register{$mac}->{'cpucores'};
            my $nfsroot = uri_unescape($params{'nfsroot'}) || $register{$mac}->{'nfsroot'};
            my $kernel = uri_unescape($params{'kernel'}) || $register{$mac}->{'kernel'};
            my $reservedvcpus = 0;

            $register{$mac} = {
                timestamp=>$current_time,
                identity=>$params{'identity'},
                ip=>$ENV{'REMOTE_ADDR'},
                status=>$nodestatus,
                memfree=>$memfree,
                memtotal=>$memtotal,
                cpuload=>$cpuload,
                cpucount=>$cpucount,
                cpucores=>$cpucores,
    #            reservedvcpus=>0,
                nfsroot=>$nfsroot,
                kernel=>$kernel,
                action=>""
            };

            if ($ipmiip) {
                $register{$mac}->{'ipmiip'} = $ipmiip;
            }
            if ($params{'stortotal'} || $params{'stortotal'} eq "0") {
                $register{$mac}->{'stortotal'} = $params{'stortotal'};
                $register{$mac}->{'storfree'} = $params{'storfree'};
                $register{$mac}->{'stor'} = $params{'stor'};
            }
            tied(%register)->commit;

    # Look for supplied info on domains running on this node, and locally stored images, and update db
            my @keys = keys %params;
            my @values = values %params;
            my $vmvcpus = 0;
            my $vms = 0;
            my $vmuuids;
            my $vmnames;
            my $vmusers;
            my %reportedimgs;
            my $ug = new Data::UUID;
            my %nodedomains;
            while ($#keys >= 0)
            {
                $key = pop(@keys); $value = pop(@values);
                if ($key =~ m/dom(\d+)/) {
                    my $i = $1;
                    my $domstatus = $params{"domstate$i"};
                    $domreg{$value}->{'statustime'} = $current_time unless ($domreg{$value}->{'statustime'});
                    my $statedelta = $current_time - $domreg{$value}->{'statustime'}; # The number of seconds domain has been in same state
                    my $domdisplay = $params{"domdisplay$i"};
                    my $domport = $params{"domport$i"};
                    my $dbdomstatus = $domreg{$value}->{'status'};
                    my $dbdommac = $domreg{$value}->{'mac'};
                    my $dommac = $mac;
                    my $duser = $domreg{$value}->{'user'};
                    $nodedomains{$value} = 1;
                    $vms++;
                    $vmuuids .= "$value, ";
                    $vmnames .= "$domreg{$value}->{'name'}, ";
                    $vmusers .= "$domreg{$value}->{'user'}, ";
                    # Domain status has changed, evaluate if it warrants a ui update
                    if ($dbdomstatus eq 'moving') {
    #				    $main::syslogit->($user, 'info', "MOVING: $domstatus/$dommac, $dbdomstatus/$dbdommac");
                    }
                    if ($dbdomstatus && $domstatus && ($dbdomstatus ne $domstatus)) {
                        # Transitional states like shuttingdown are not reported by hypervisor
                        # we only update db with permanent states when exiting a transitional hypervisor state or
                        # too much time has passed
                        if (($dbdomstatus eq "shuttingdown" && $domstatus eq "running" && $statedelta<120)
                            || ($dbdomstatus eq "starting" && $domstatus eq "inactive" && $statedelta<30)
                            || ($dbdomstatus eq "starting" && $domstatus eq "shutdown" && $statedelta<30)
                            || ($dbdomstatus eq "starting" && $domstatus eq "shutoff" && $statedelta<30)
                            || ($dbdomstatus eq "suspending" && $domstatus eq "running" && $statedelta<30)
                            || ($dbdomstatus eq "resuming" && $domstatus eq "paused" && $statedelta<30)
                        # When moving $dbdommac is the originating mac, wait 5 min for moves
                            || ($dbdomstatus eq "moving" && $domstatus eq "running" && $dbdommac eq $mac && $statedelta<300)
                            || ($dbdomstatus eq "moving" && $domstatus eq "paused" && $dbdommac ne $mac && $statedelta<300)
                            || ($dbdomstatus eq "moving" && $domstatus eq "shutoff" && $dbdommac eq $mac && $statedelta<300)
                            || ($domstatus eq "nostate")
                            || ($dbdomstatus eq "destroying" && $domstatus eq "running" && $statedelta<30)
                            || ($dbdomstatus eq "destroying" && $domstatus eq "paused" && $statedelta<30)
                            || ($dbdomstatus eq "upgrading" && $statedelta<600)
                        ) {
                            $domstatus = $dbdomstatus;
                            $dommac = $dbdommac;
                        } else {
                        # We have exited from a transition, update the UI
                            $domreg{$value}->{'statustime'} = $current_time;
                            $billing{$duser}->{'event'} .= "$domstatus $value\n";
                            $main::updateUI->({tab=>"servers", user=>"$duser", uuid=>$value, status=>$domstatus,
                                                mac=>$mac, macname=>$macname});
                            if ($enginelinked && $engineid) {
                                my $sysuuid = $domreg{$value}->{'uuid'};
                                my $sysstatus = $domstatus;
                                if ($domreg{$value}->{'system'} && $domreg{$value}->{'system'} ne '--') { # This is a system
                                    $sysuuid = $domreg{$value}->{'system'};
                                    unless (tie %sysreg,'Tie::DBI', {
                                        db=>'mysql:steamregister',
                                        table=>'systems',
                                        key=>'uuid',
                                        autocommit=>0,
                                        CLOBBER=>3,
                                        user=>$dbiuser,
                                        password=>$dbipasswd}) {throw Error::Simple("Status=ERROR System register could not be accessed")};
                                    # Check if we are dealing with the admin server
                                    if ($domreg{$value}->{'image'} ne $sysreg{$sysuuid}->{'image'}) {
                                        $sysuuid = '';
                                    }

                                    untie %sysreg;
                                }
                                if ($sysuuid) {
                                my $json_text = <<END
{"uuid": "$sysuuid" , "status": "$sysstatus"}
END
;
                                    print "\n" . $main::postAsyncToOrigo->($engineid, 'updateapps', "[$json_text]") . "\n";
                                }
                            }
                        }
                    }

                    # If a domain is shutoff or state is undetermined, dont't count it in billing
                    # if ($domstatus eq "shutoff" || $domstatus eq "inactive" ) {
                    if ($domstatus eq "shutoff" || $domstatus eq "inactive" ) {
                        $billing{$duser}->{'vcpu'} += 0;
                        $billing{$duser}->{'memory'} += 0;
                    # All other states count
                    } else {
                        $billing{$duser}->{'vcpu'} += $domreg{$value}->{'vcpu'};
                        $billing{$duser}->{'memory'} += $domreg{$value}->{'memory'};
                    }
                    # We don't update timestamp for moving domains, so if move fails, eventually they will be marked as inactive
                    my $timestamp = $current_time;
                    $timestamp = $domreg{$value}->{'timestamp'} if ($domstatus eq "moving");
                    $domreg{$value} = {
                        status=>$domstatus,
                        mac=>$dommac,
                        macname=>$register{$dommac}->{'name'},
                        macip=>$register{$dommac}->{'ip'},
                        maccpucores=>$register{$dommac}->{'cpucores'},
                        timestamp=>$timestamp
                    };
                    $domreg{$value}->{'mac'} = $dommac unless ($domstatus eq 'moving');
                    $domreg{$value}->{'display'} = $domdisplay if $domdisplay;
                    $domreg{$value}->{'port'} = $domport if $domport;
                    if ($params{"domstate$i"} eq 'running') {$vmvcpus += $domreg{$value}->{'vcpu'}};
                # If a domain was moved, update permitted ports
                    if (($dbdomstatus eq "moving" && $domstatus eq "running" && $dbdommac ne $mac)) {
                        $main::syslogit->($duser, 'info', "Moved $domreg{$value}->{'name'} ($value) to $register{$dommac}->{'name'}");
                        permitOpen($duser);
                    }
                # Update status of server's images
                    my $image = $domreg{$value}->{'image'};
                    my $image2 = $domreg{$value}->{'image2'};
                    my $image3 = $domreg{$value}->{'image3'};
                    my $image4 = $domreg{$value}->{'image4'};
                    my $imgstatus = 'active'; # if server is running, moving, etc.
                    if ($domstatus eq 'paused') {
                        $imgstatus = 'paused'
                    } elsif ($domstatus eq "shutoff" || $domstatus eq "inactive")  {
                        $imgstatus = 'used'
                    }
                    $imagereg{$image}->{'status'} = $imgstatus if ($imagereg{$image}->{'status'} !~ /backingup/);
                    $imagereg{$image2}->{'status'} = $imgstatus if ($image2 && $image2 ne '--' && $imagereg{$image2}->{'status'} !~ /backingup/);
                    $imagereg{$image3}->{'status'} = $imgstatus if ($image3 && $image3 ne '--' && $imagereg{$image3}->{'status'} !~ /backingup/);
                    $imagereg{$image4}->{'status'} = $imgstatus if ($image4 && $image4 ne '--' && $imagereg{$image4}->{'status'} !~ /backingup/);

                } elsif ($key =~ m/img(\d+)/) {
            # The node is reporting about a locally stored image
                    my $f = uri_unescape($value);
                    my $size = $params{"size$1"};
                    my $realsize = $params{"realsize$1"};
                    my $virtualsize = $params{"virtualsize$1"};
                    my($fname, $dirpath, $suffix) = fileparse($f, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));
                    my $regimg = $imagereg{$f};
                    my $uuid = $regimg->{'uuid'};

                    my $storagepool = -1;
                    $f =~ m/\/mnt\/stabile\/node\/(.+?)\/.+/; # ungready matching
                    my $imguser = $1;

            # Create a new uuid if we are dealing with a new file in the file-system
                    if (!$uuid) {
                        $uuid = $ug->create_str() unless ($uuid);
                        $main::syslogit->($imguser, 'info', "Assigned new uuid $uuid to $f belonging to $imguser");
                    }

                    my $mtime = $newmtime || $regimg->{'mtime'};
                    my $name = $regimg->{'name'} || $fname;

                    my $subdir = "";
                    if ($dirpath =~ /\/$imguser(\/.+)\//) {
                        $subdir = $1;
                    }
                    my $bdu;
                    my $backupsize = 0;
                    my $imgpath = "$fname$suffix";
                    $imgpath = $1 if $cmdpath =~ /(.+)/; # untaint
                    $backupsize = getBackupSize($subdir, $imgpath, $imguser);
            # If image on node is attached to a domain, reserve vcpus for starting domain on node
                    my $imgdom = $regimg->{'domains'};
                    if ($imgdom && $domreg{$imgdom}) {
                        my $imgvcpus = $domreg{$imgdom}->{'vcpu'};
                        my $imgdomstatus = $domreg{$imgdom}->{'status'};
                        $reservedvcpus += $imgvcpus if ($imgdomstatus eq 'shutoff' || $imgdomstatus eq 'inactive');
                    }

                    $reportedimgs{$f} = 1;
                    if (($regimg->{'virtualsize'} == 0 && $virtualsize) || $regimg->{'status'} eq 'moving') {
                        $reportedimgs{$f} = 2; # Mark that we should update the UI - this is a recently transferred image
                    }
                    if ($f && $imguser) {
                        my $imgstatus = $regimg->{'status'};
                        # This only happens first time after an image has been transferred manually to a node
                        if (!$imgstatus || $imgstatus eq '--' || $imgstatus eq 'cloning') {
                            $imgstatus = "unused";
                            my $imgdomains = $regimg->{'domains'};
                            my $imgdomainnames = $regimg->{'domainnames'};
                            (tied %domreg)->select_where("user = '$imguser' or user = 'common'") unless ($fulllist);
                            foreach my $dom (values %domreg) {
                                my $img = $dom->{'image'};
                                my $img2 = $dom->{'image2'};
                                my $img3 = $dom->{'image3'};
                                my $img4 = $dom->{'image4'};
                                if ($f eq $img || $f eq $img2 || $f eq $img3 || $f eq $img4) {
                                    $imgstatus = "active";
                                    my $domstatus = $dom->{'status'};
                                    if ($domstatus eq "shutoff" || $domstatus eq "inactive") {$imgstatus = "used";}
                                    elsif ($domstatus eq "paused") {$imgstatus = "paused";}
                                    $imgdomains = $dom->{'uuid'};
                                    $imgdomainnames = $dom->{'name'};
                                };
                            }
                            $imagereg{$f} = {
                                user=>$imguser,
                                type=>substr($suffix,1),
                                size=>$size,
                                realsize=>$realsize,
                                virtualsize=>$virtualsize,
                                backupsize=>$backupsize,
                                name=>$name,
                                uuid=>$uuid,
                                storagepool=>$storagepool,
                                mac=>$mac,
                                mtime=>$mtime,
                                status=>$imgstatus,
                                domains=>$imgdomains,
                                domainnames=>$imgdomainnames
                            }
                        } else {
                            $imagereg{$f} = {
                                user=>$imguser,
                                type=>substr($suffix,1),
                                size=>$size,
                                realsize=>$realsize,
                                virtualsize=>$virtualsize,
                                backupsize=>$backupsize,
                                name=>$name,
                                uuid=>$uuid,
                                storagepool=>$storagepool,
                                mac=>$mac,
                                mtime=>$mtime
                            }
                        }
                    }

                }
            }

            if ($params{'dominfo'} || $params{'dom1'}) {
                $register{$mac}->{'vms'} = $vms;
                $register{$mac}->{'vmvcpus'} = $vmvcpus;
                $register{$mac}->{'vmuuids'} = substr($vmuuids,0,-2);
                $register{$mac}->{'vmnames'} = substr($vmnames,0,-2);
                $register{$mac}->{'vmusers'} = substr($vmusers,0,-2);
            }
            if ($params{'stortotal'}) {
                $register{$mac}->{'reservedvcpus'} = $reservedvcpus;
            }

    # Clean up image db - remove images that are no longer on the node
            if ($params{'stortotal'} || $params{'stortotal'} eq "0") {
                my @regkeys = (tied %imagereg)->select_where("mac = '$mac'");
                foreach my $k (@regkeys) {
                    my $valref = $imagereg{$k};
                    if ( ($valref->{'storagepool'} == -1) && ($valref->{'mac'} eq $mac) && ($valref->{'status'} ne "moving") && !($valref->{'status'} =~ /cloning/) ) {
                        if ($reportedimgs{$valref->{'path'}} == 1) {
                        } elsif ($reportedimgs{$valref->{'path'}} == 2){
                            updateImageBilling($valref->{'user'}, $valref->{'path'}, "new image");
                        } else {
                            $main::updateUI->({tab=>"images", user=>$valref->{'user'}});
                            $main::syslogit->($valref->{'user'}, 'info', "Deleting image from db $valref->{'user'} - $reportedimgs{$valref->{'path'}} - $valref->{'path'} - $valref->{'status'} - $valref->{'mac'}");
                            delete $imagereg{$valref->{'path'}};
                            updateImageBilling($valref->{'user'}, $valref->{'path'}, "no image");
                        }
                    } elsif ($valref->{'storagepool'} == -1) {
                        ;
                    }
                }
            }

    # Clean up domain status, mark domains which are inactive or shuttingdown and not present on this node as shutoff
            my @regkeys = (tied %domreg)->select_where("mac = '$mac'");
            foreach my $domkey (@regkeys) {
                my $domref = $domreg{$domkey};
                if ($domref->{'mac'} eq $mac) {
                    if ($domref->{'status'} eq 'inactive' ||
                        ($domref->{'status'} eq 'shuttingdown' && $params{'memfree'} && !($nodedomains{$domref->{'uuid'}})) # domain has shut down, checking for param 'memfree' to make sure it's not just a status update from node
                    ) {
                        $domref->{'status'} = 'shutoff';
    #                    $main::updateUI->({tab=>"servers", user=>$domref->{'user'}, uuid=>$domref->{'uuid'}, status=>'shutoff',
    #                        message=>"shutoff ".$vmuuids."::".$domref->{'uuid'}});
                    }
                }
            }


    # Update billing
            my %billingreg;
            $monthtimestamp = timelocal(0,0,0,1,$mon,$year); #$sec,$min,$hour,$mday,$mon,$year
            # $monthtimestamp = timelocal(0,0,$hour,$mday,$mon,$year); #$sec,$min,$hour,$mday,$mon,$year
            unless (tie %userreg,'Tie::DBI', {
                db=>'mysql:steamregister',
                table=>'users',
                key=>'username',
                autocommit=>0,
                CLOBBER=>1,
                user=>$dbiuser,
                password=>$dbipasswd}) {return 0};
            my @pusers = keys %userreg;
            untie %userreg;
            unless (tie %billingreg,'Tie::DBI', {
                db=>'mysql:steamregister',
                table=>'billing_domains',
                key=>'usernodetime',
                autocommit=>0,
                CLOBBER=>3,
                user=>$dbiuser,
                password=>$dbipasswd}) {throw Error::Simple("Status=Error Billing register could not be accessed")};

            foreach my $puser (@pusers) {
                my $b = $billing{$puser};
                my $vcpu = $b->{'vcpu'};
                my $memory = $b->{'memory'};
                my $startvcpuavg = 0;
                my $startmemoryavg = 0;
                my $vcpuavg = 0;
                my $memoryavg = 0;
                my $starttimestamp = $current_time;

            # Are we just starting a new month
                if ($current_time - $monthtimestamp < 4*3600) {
                    $starttimestamp = $monthtimestamp;
                    $vcpuavg = $vcpu;
                    $startvcpuavg = $vcpu;
                    $memoryavg = $memory;
                    $startmemoryavg = $memory;
                }

                if ($billingreg{"$puser-$mac-$year-$month"}) {
                # Update timestamp and averages
                    $startvcpuavg = $billingreg{"$puser-$mac-$year-$month"}->{'startvcpuavg'};
                    $startmemoryavg = $billingreg{"$puser-$mac-$year-$month"}->{'startmemoryavg'};
                    $starttimestamp = $billingreg{"$puser-$mac-$year-$month"}->{'starttimestamp'};
                    $vcpuavg = ($startvcpuavg*($starttimestamp - $monthtimestamp) + $vcpu*($current_time - $starttimestamp)) /
                                    ($current_time - $monthtimestamp);
                    $memoryavg = ($startmemoryavg*($starttimestamp - $monthtimestamp) + $memory*($current_time - $starttimestamp)) /
                                    ($current_time - $monthtimestamp);

                    $billingreg{"$puser-$mac-$year-$month"}->{'vcpuavg'} = $vcpuavg;
                    $billingreg{"$puser-$mac-$year-$month"}->{'memoryavg'} = $memoryavg;
                    $billingreg{"$puser-$mac-$year-$month"}->{'timestamp'} = $current_time;
                }

                # No row found or something happened which justifies writing a new row
                if (!$billingreg{"$puser-$mac-$year-$month"}
                || ($vcpu != $billingreg{"$puser-$mac-$year-$month"}->{'vcpu'})
                || ($memory != $billingreg{"$puser-$mac-$year-$month"}->{'memory'})
                ) {
                    my $inc = 0;
                    if ($billingreg{"$puser-$mac-$year-$month"}) {
                        $startvcpuavg = $vcpuavg;
                        $startmemoryavg = $memoryavg;
                        $starttimestamp = $current_time;
                        $inc = $billingreg{"$puser-$mac-$year-$month"}->{'inc'};
                    }
                    # Write a new row
                    $billingreg{"$puser-$mac-$year-$month"} = {
                        vcpu=>$vcpu,
                        memory=>$memory,
                        vcpuavg=>$vcpuavg,
                        memoryavg=>$memoryavg,
                        startvcpuavg=>$startvcpuavg,
                        startmemoryavg=>$startmemoryavg,
                        timestamp=>$current_time,
                        starttimestamp=>$starttimestamp,
                        event=>$b->{'event'},
                        inc=>$inc+1,
                    };
                }
            }
            untie %billingreg;

            tied(%domreg)->commit;

		}
# Check if this node has tasks, and send them to the node them if any

		if ($tasks) {
    		my $sendtasks = '';
			@tasklist = split(/\n/,$tasks);
			$sendtasks .= "\n";
			foreach $thetask (@tasklist) {
			    my ($task,$user) = split(/ /, $tasks);
				if ($task eq 'reboot') {
					$sendtasks .= "\nStatus=REBOOT $user\n";
				} elsif ($task eq 'shutdown' || $task eq 'halt') {
					$sendtasks .= "\nStatus=HALT $user\n";
				} elsif ($task eq 'unjoin') {
					unlink $file;
					$sendtasks .= "\nStatus=UNJOIN $user\n";
				} elsif ($task eq 'reload') {
					$sendtasks .= "\nStatus=RELOAD $user\n";
				} elsif ($task eq 'wipe') {
					$sendtasks .= "\nStatus=WIPE $user\n";
				} elsif ($task eq 'sleep') {
					$sendtasks .= "\nStatus=SLEEP $user\n";
				} elsif ($task eq 'wake') {
					$sendtasks .= "\nStatus=WAKE $user\n";
				} else {
				     if ($task) {
                        $sendtasks .= "Status=$thetask\n";
                    }
				};
			}
            `echo "SENDING TASKS to $mac: $sendtasks" >> /var/log/stabile/steamExec.out` if ($sendtasks);
    		print $sendtasks if ($sendtasks);
		} else {
			print  "\nStatus=OK $mac\n";
			my $sleepafter = $idreg{'default'}->{'sleepafter'};
			$sleepafter = 60 * $sleepafter;
			print "Status=SLEEPAFTER ". $sleepafter . "\n";
		}
		print end_html(), "\n";
	}
	untie %register;
	untie %domreg;
	untie %imagereg;
	untie %idreg;

    if ($plogentry && $plogentry ne '' && $uistatus) {
        $uistatus = 'maintenance' if ($uistatus eq 'running' && $maintenance);
        $main::updateUI->({tab=>$uitab, user=>$user, uuid=>$uiuuid, status=>$uistatus, mac=>$mac, macname=>$macname}) unless ($status eq '--');
        $main::syslogit->($user, 'info', "$plogentry $uiuuid ($uitab, $uistatus)");
    }

} catch Error with {
	my $ex = shift;
	print "\n", "$ex->{-text} (line: $ex->{-line})", "\n";
} finally {
};

sub permitOpen {
    my ($user) = @_;
    my $permit;

    unless (tie %userreg,'Tie::DBI', {
        db=>'mysql:steamregister',
        table=>'users',
        key=>'username',
        autocommit=>0,
        CLOBBER=>1,
        user=>$dbiuser,
        password=>$dbipasswd}) {return 0};

    my $privileges = $userreg{$user}->{'privileges'};
    my $allowfrom = $userreg{$user}->{'allowfrom'};
    untie %userreg;

    my @allows = split(/,\s*/, $allowfrom);

    if ($privileges && (index($privileges,"r")!=-1 || index($privileges,"d")!=-1)) {
        ; # User is disabled or has only readonly access
    } elsif ($user) {
        my @regkeys = (tied %domreg)->select_where("user = '$user'");
        foreach my $k (@regkeys) {
            my $val = $domreg{$k};
        # Only include VM's belonging to current user
            if ($user eq $val->{'user'}) {
                # Only include drivers we have heard from in the last 20 secs
                #if ($current_time - ($val->{'timestamp'}) < 20) {
                    my $targetmac = $val->{'mac'};
                    my $targetip = $register{$targetmac}->{'ip'};
                    my $targetport = $val->{'port'};
                    if ($targetip && $targetport) {$permit .= " $targetip:$targetport";};
                #} else {
                #};
            }
        }
        $permit = " 192.168.0.254:8000" unless $permit;
    #    $main::syslogit->($user, 'info', "Allowed portforwarding for $user: $permit");

        open(TEMP1, "</etc/ssh/sshd_config") || (die "Problem reading sshd_config");
        open(TEMP2, ">/etc/ssh/sshd_config.new") || (die "Problem writing sshd_config");
        print TEMP2 "# Timestamp: $pretty_time\n";
        my $umatch = 0;
        my $allowusers;
        my $auser = $user;
        $auser =~ s/\@/\?/; # sshd_config does not support @'s in AllowUsers usernames
        if ($allowfrom) { # Only allow login from certain ip's
            $allowusers = "AllowUsers";
            foreach my $ip (@allows) {
                $ip = "$1*" if ($ip =~ /(\d+\.)0\.0\.0/);
                $ip = "$1*" if ($ip =~ /(\d+\.\d+\.)0\.0/);
                $ip = "$1*" if ($ip =~ /(\d+\.\d+\.\d+\.)0/);
                $allowusers .= " irigo-$auser\@$ip ";
            }
            $allowusers .= "\n";
        } else {
            $allowusers = "AllowUsers irigo-$auser\n"; # Allow from anywhere
        }

        my $matchuser = "irigo-$auser";
        $matchuser =~ tr/\?/./; # question marks don't work in regexp match
        while (<TEMP1>) {
            my $line = $_;

            if ($user && $line =~ m/Match User $matchuser/) {$umatch = 1;}
            elsif ($umatch && $line =~ m/Match User/) {$umatch = 0;}

            if ($line =~ m/AllowUsers irigo\@localhost/) {
                print TEMP2 $line;
                print TEMP2 "$allowusers";
                next;
            }
            if (!$umatch && !($line =~ /^AllowUsers $matchuser/) && !($line =~ m/^# Timestamp/)) {
                print TEMP2 $line;
            }
        }

        print TEMP2 <<END1;
Match User irigo-$user
ForceCommand /usr/local/bin/permitOpen $user 1
PermitOpen$permit
END1

;
    #ForceCommand /usr/bin/perl -e '\$|=1;while (1) { print scalar localtime() . "\\n";sleep 30}'
        close(TEMP1);
        close(TEMP2);
        rename("/etc/ssh/sshd_config", "/etc/ssh/sshd_config.old") || print "Status=ERROR Don't have permission to rename sshd_config";
        rename("/etc/ssh/sshd_config.new", "/etc/ssh/sshd_config") || print "Status=ERROR Don't have permission to rename sshd_config";
        eval {$output = `/etc/init.d/ssh restart`; 1;}  or do {print "Status=ERROR $@";};
    }
}

sub trim{
   my $string = shift;
   $string =~ s/^\s+|\s+$//g;
   return $string;
}

sub updateImageBilling {
    my ($user, $bpath, $status, $backupsize) = @_; # Update billing for specific image storage pool with either virtualsize and backupsize

    if ($backupsize) {
        $imagereg{$bpath}->{'backupsize'} = $backupsize;
    }
    return "No user" unless ($user);
    my $tenders = $Stabile::config->get('STORAGE_POOLS_ADDRESS_PATHS');
    my @tenderlist = split(/,\s*/, $tenders);
    my $tenderpaths = $Stabile::config->get('STORAGE_POOLS_LOCAL_PATHS') || "/mnt/stabile/images";
    my @tenderpathslist = split(/,\s*/, $tenderpaths);
    my $tendernames = $Stabile::config->get('STORAGE_POOLS_NAMES') || "Standard storage";
    my @tendernameslist = split(/,\s*/, $tendernames);
    my $storagepools = $Stabile::config->get('STORAGE_POOLS_DEFAULTS') || "0";
    my $storagepool = 0;
    if ($bpath =~ /\/mnt\/stabile\/node\//) {
        $storagepool = -1;
    } else {
        my @spl = split(/,\s*/, $storagepools);
        foreach my $p (@spl) {
            if ($tenderlist[$p] && $tenderpathslist[$p] && $tendernameslist[$p]) {
                my %pool = ("hostpath", $tenderlist[$p],
                            "path", $tenderpathslist[$p],
                            "name", $tendernameslist[$p],
                            "rdiffenabled", $rdiffenabledlist[$p],
                            "id", $p);
                $spools[$p] = \%pool;
                $storagepool = $p if ($bpath =~ /$tenderpathslist[$p]/)
            }
        }
    }

    my %billing;

    my @regkeys = (tied %imagereg)->select_where("user = '$user' AND storagepool = '$storagepool'");
    foreach my $k (@regkeys) {
        my $valref = $imagereg{$k};
        my %val = %{$valref}; # Deference and assign to new array, effectively cloning object
        $val{'virtualsize'} += 0;
        $val{'realsize'} += 0;
        $val{'backupsize'} += 0;

        if ($val{'user'} eq $user && $val{'storagepool'} == $storagepool) {
            $billing{$val{'storagepool'}}->{'virtualsize'} += $val{'virtualsize'};
            $billing{$val{'storagepool'}}->{'realsize'} += $val{'realsize'};
            $billing{$val{'storagepool'}}->{'backupsize'} += $val{'backupsize'};
        }
    }

    my %billingreg;
    my $monthtimestamp = timelocal(0,0,0,1,$mon,$year); #$sec,$min,$hour,$mday,$mon,$year

    unless (tie %billingreg,'Tie::DBI', {
        db=>'mysql:steamregister',
        table=>'billing_images',
        key=>'userstoragepooltime',
        autocommit=>0,
        CLOBBER=>3,
        user=>$dbiuser,
        password=>$dbipasswd}) {$main::syslogit->($user, 'info', "Status=Error Billing register could not be accessed")};

    my $b = $billing{$storagepool};
    my $virtualsize = $b->{'virtualsize'};
    my $realsize = $b->{'realsize'};
    my $backupsize = $b->{'backupsize'};
    my $startvirtualsizeavg = 0;
    my $startrealsizeavg = 0;
    my $startbackupsizeavg = 0;
    my $starttimestamp = $current_time;
    # No row found or something happened which justifies writing a new row
    if ($b->{'event'} || !$billingreg{"$user-$storagepool-$year-$month"}
    || ($b->{'virtualsize'} != $billingreg{"$user-$storagepool-$year-$month"}->{'virtualsize'})
    || ($b->{'realsize'} != $billingreg{"$user-$storagepool-$year-$month"}->{'realsize'})
    || ($b->{'backupsize'} != $billingreg{"$user-$storagepool-$year-$month"}->{'backupsize'})
    ) {
        my $inc = 0;
        if ($billingreg{"$user-$storagepool-$year-$month"}) {
            $startvirtualsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'virtualsizeavg'};
            $startrealsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'realsizeavg'};
            $startbackupsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'backupsizeavg'};
            $starttimestamp = $billingreg{"$user-$storagepool-$year-$month"}->{'timestamp'};
            $inc = $billingreg{"$user-$storagepool-$year-$month"}->{'inc'};
        # Copy the old row for archival purposes
#            my %bill = %{$billingreg{"$user-$storagepool-$year-$month"}};
#            $billingreg{"$user-$storagepool-$year-$month-$current_time"} = \%bill;
        }
        # Write a new row
        $billingreg{"$user-$storagepool-$year-$month"} = {
            virtualsize=>$virtualsize+0,
            realsize=>$realsize+0,
            backupsize=>$backupsize+0,
            virtualsizeavg=>$startvirtualsizeavg,
            realsizeavg=>$startrealsizeavg,
            backupsizeavg=>$startbackupsizeavg,
            timestamp=>$current_time,
            startvirtualsizeavg=>$startvirtualsizeavg,
            startrealsizeavg=>$startrealsizeavg,
            startbackupsizeavg=>$startbackupsizeavg,
            starttimestamp=>$starttimestamp,
            event=>"$status $bpath",
            inc=>$inc+1,
        };
    } else {
    # Update timestamp and averages
        $startvirtualsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'startvirtualsizeavg'};
        $startrealsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'startrealsizeavg'};
        $startbackupsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'startbackupsizeavg'};
        $starttimestamp = $billingreg{"$user-$storagepool-$year-$month"}->{'starttimestamp'};
        my $virtualsizeavg = ($startvirtualsizeavg*($starttimestamp - $monthtimestamp) + $virtualsize*($current_time - $starttimestamp)) /
                        ($current_time - $monthtimestamp);
        my $realsizeavg = ($startrealsizeavg*($starttimestamp - $monthtimestamp) + $realsize*($current_time - $starttimestamp)) /
                        ($current_time - $monthtimestamp);
        my $backupsizeavg = ($startbackupsizeavg*($starttimestamp - $monthtimestamp) + $backupsize*($current_time - $starttimestamp)) /
                        ($current_time - $monthtimestamp);

        $billingreg{"$user-$storagepool-$year-$month"}->{'virtualsizeavg'} = $virtualsizeavg;
        $billingreg{"$user-$storagepool-$year-$month"}->{'realsizeavg'} = $realsizeavg;
        $billingreg{"$user-$storagepool-$year-$month"}->{'backupsizeavg'} = $backupsizeavg;
        $billingreg{"$user-$storagepool-$year-$month"}->{'timestamp'} = $current_time;
    }
    untie %billingreg;
}
