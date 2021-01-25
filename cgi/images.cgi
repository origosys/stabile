#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license

package Stabile::Images;

use Error qw(:try);
use File::Basename;
use Data::UUID;
use Proc::Daemon;
use Time::Local;
#use Time::HiRes qw( time );
use Date::Format;
use Date::Parse;
use Getopt::Std;
#use Encode::Escape;
use File::Glob qw(bsd_glob);
use Sys::Guestfs;
use Data::Dumper;
use XML::Simple;
#use POSIX qw(strftime);
use Time::Piece;
use Config::Simple;
use lib dirname (__FILE__); # Allows us to source libraries from current directory no matter where we are called from
use Stabile;

$\ = ''; # Some of the above seems to set this to \n, resulting in every print appending a line feed

# Read in some settings from config
$backupdir = $Stabile::config->get('STORAGE_BACKUPDIR') || "/mnt/stabile/backups";
$backupdir = $1 if ($backupdir =~ /(.+)/); #untaint
my $tenders = $Stabile::config->get('STORAGE_POOLS_ADDRESS_PATHS');
my @tenderlist = split(/,\s*/, $tenders);
my $tenderpaths = $Stabile::config->get('STORAGE_POOLS_LOCAL_PATHS') || "/mnt/stabile/images";
my @tenderpathslist = split(/,\s*/, $tenderpaths);
my $tendernames = $Stabile::config->get('STORAGE_POOLS_NAMES') || "Standard storage";
my @tendernameslist = split(/,\s*/, $tendernames);
my $mountabletenders = $Stabile::config->get('STORAGE_POOLS_MOUNTABLE');
my @mountabletenderslist = split(/,\s*/, $mountabletenders);
my $storagepools = $Stabile::config->get('STORAGE_POOLS_DEFAULTS') || "0";
my $spoolsrdiffenabled = $Stabile::config->get('STORAGE_POOLS_RDIFF-BACKUP_ENABLED') || "0";
my @rdiffenabledlist = split(/,\s*/, $spoolsrdiffenabled);
my $rdiffenabled = $Stabile::config->get('RDIFF-BACKUP_ENABLED') || "0";
my $userrdiffenabled = $Stabile::config->get('RDIFF-BACKUP_USERS') || "0";
my $nodestorageovercommission = $Stabile::config->get('NODE_STORAGE_OVERCOMMISSION') || "1";
my $engineid = $Stabile::config->get('ENGINEID') || "";

my $valve_readlimit = $Stabile::config->get('VALVE_READ_LIMIT'); # e.g. 125829120 = 120 * 1024 * 1024 = 120 MB / s
my $valve_writelimit = $Stabile::config->get('VALVE_WRITE_LIMIT');
my $valve_iopsreadlimit = $Stabile::config->get('VALVE_IOPS_READ_LIMIT'); # e.g. 1000 IOPS
my $valve_iopswritelimit = $Stabile::config->get('VALVE_IOPS_WRITE_LIMIT');

my $valve001id = '995e86b7-ae85-4ae0-9800-320c1f59ae33';
my $stackspool = '/mnt/stabile/images001';

our %ahash; # A hash of accounts and associated privileges current user has access to
#our %options=();
# -a action -h help -f full list -p full update -u uuid -i image -m match pattern -k keywords -g args to gearman task
# -v verbose, include HTTP headers -s impersonate subaccount -t target [uuid or image]
#Getopt::Std::getopts("a:hfpu:i:g:m:k:vs:t:", \%options);

try {
    Init(); # Perform various initalization tasks
    process() if ($package); # Parse and process request. $package is not set if called as a library

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

sub Init {

    # Tie database tables to hashes
    unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>1}, $Stabile::dbopts)) ) {return "Unable to access user register"};
    unless ( tie(%register,'Tie::DBI', Hash::Merge::merge({table=>'images', key=>'path'}, $Stabile::dbopts)) ) {return "Unable to access image register"};
    unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks'}, $Stabile::dbopts)) ) {return "Unable to access network register"};
    unless ( tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', CLOBBER=>1}, $Stabile::dbopts)) ) {return "Unable to access image uuid register"};
    unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains'}, $Stabile::dbopts)) ) {return "Unable to access domain register"};

    # simplify globals initialized in Stabile.pm
    $tktuser = $tktuser || $Stabile::tktuser;
    $user = $user || $Stabile::user;
    $isadmin = $isdamin || $Stabile::isadmin;
    $sshcmd = $sshcmd || $Stabile::sshcmd;
    $disablesnat = $disablesnat || $Stabile::disablesnat;

    # Create aliases of functions
    *header = \&CGI::header;

    *Getimagesdevice = \&Liststoragedevices;
    *Getbackupdevice = \&Liststoragedevices;
    *Listimagesdevices = \&Liststoragedevices;
    *Listbackupdevices = \&Liststoragedevices;

    *do_save = \&privileged_action_async;
    *do_sync_save = \&privileged_action;
    *do_sync_clone = \&privileged_action;
    *do_updateregister = \&action;
    *do_fullupdateregister = \&action;
    *do_tablelistall = \&do_list;
    *do_tablelist = \&do_list;
    *Sync_save = \&Save;
    *Sync_clone = \&Clone;
    *do_help = \&action;

    *do_mount = \&privileged_action;
    *do_unmount = \&privileged_action;
    *do_activate = \&privileged_action;
    *do_publish = \&privileged_action;
    *do_release = \&privileged_action;
    *do_download = \&privileged_action;
    *do_linkmaster = \&privileged_action;
    *do_listbackups = \&privileged_action;
    *do_listcdroms = \&action;
    *do_listfiles = \&privileged_action;
    *do_getserverbackups = \&privileged_action;
    *do_listserverbackups = \&privileged_action;
    *Listserverbackups = \&Getserverbackups;
    *do_restorefiles = \&privileged_action;
    *do_remove = \&privileged_action;
    *do_removeuserimages = \&privileged_action;
    *do_updatedownloads = \&privileged_action;
    *do_master = \&privileged_action_async;
    *do_unmaster = \&privileged_action_async;
    *do_clone = \&privileged_action_async;
    *do_snapshot = \&privileged_action_async;
    *do_unsnap = \&privileged_action_async;
    *do_revert = \&privileged_action_async;
    *do_inject = \&privileged_action_async;
    *do_backup = \&privileged_action_async;
    *do_zbackup = \&privileged_action;
    *do_restore = \&privileged_action_async;
    *do_updatebackingfile = \&privileged_action;
    *do_updatebtime = \&privileged_action;
    *do_updateallbtimes = \&privileged_action;
    *do_initializestorage = \&privileged_action;
    *do_liststoragedevices = \&privileged_action;
    *do_listimagesdevices = \&privileged_action;
    *do_listbackupdevices = \&privileged_action;
    *do_getimagesdevice = \&privileged_action;
    *do_getbackupdevice = \&privileged_action;
    *do_setstoragedevice = \&privileged_action;

    *do_gear_save = \&do_gear_action;
    *do_gear_sync_save = \&do_gear_action;
    *do_gear_sync_clone = \&do_gear_action;
    *do_gear_mount = \&do_gear_action;
    *do_gear_unmount = \&do_gear_action;
    *do_gear_activate = \&do_gear_action;
    *do_gear_publish = \&do_gear_action;
    *do_gear_release = \&do_gear_action;
    *do_gear_download = \&do_gear_action;
    *do_gear_linkmaster = \&do_gear_action;
    *do_gear_listbackups = \&do_gear_action;
    *do_gear_listserverbackups = \&do_gear_action;
    *do_gear_getserverbackups = \&do_gear_action;
    *do_gear_listfiles = \&do_gear_action;
    *do_gear_restorefiles = \&do_gear_action;
    *do_gear_remove = \&do_gear_action;
    *do_gear_removeuserimages = \&do_gear_action;
    *do_gear_updatedownloads = \&do_gear_action;
    *do_gear_master = \&do_gear_action;
    *do_gear_unmaster = \&do_gear_action;
    *do_gear_clone = \&do_gear_action;
    *do_gear_snapshot = \&do_gear_action;
    *do_gear_unsnap = \&do_gear_action;
    *do_gear_revert = \&do_gear_action;
    *do_gear_inject = \&do_gear_action;
    *do_gear_backup = \&do_gear_action;
    *do_gear_zbackup = \&do_gear_action;
    *do_gear_restore = \&do_gear_action;
    *do_gear_updatebackingfile = \&do_gear_action;
    *do_gear_updatebtime = \&do_gear_action;
    *do_gear_updateallbtimes = \&do_gear_action;
    *do_gear_initializestorage = \&do_gear_action;
    *do_gear_liststoragedevices = \&do_gear_action;
    *do_gear_listimagesdevices = \&do_gear_action;
    *do_gear_listbackupdevices = \&do_gear_action;
    *do_gear_getimagesdevice = \&do_gear_action;
    *do_gear_getbackupdevice = \&do_gear_action;
    *do_gear_setstoragedevice = \&do_gear_action;

    *Fullupdateregister = \&Updateregister;

    @users; # global
    if ($fulllist) {
        @users = keys %userreg;
        push @users, "common";
    } else {
        @users = ($user, "common");
    }

    untie %userreg;

#    my $mounts = decode('ascii-escape', `/bin/cat /proc/mounts`);
    my $mounts = `/bin/cat /proc/mounts`;
    @spools;

    # Enumerate and define the storage pools a user has access to
    my @spl = split(/,\s*/, $storagepools);
    my $reloadnfs;
    foreach my $p (@spl) {
        if ($tenderlist[$p] && $tenderpathslist[$p] && $tendernameslist[$p]) {
            my %pool = ("hostpath", $tenderlist[$p],
                "path", $tenderpathslist[$p],
                "name", $tendernameslist[$p],
                "rdiffenabled", $rdiffenabledlist[$p],
                "mountable", ($tenderlist[$p] eq 'local') || $mountabletenderslist[$p] || '0', # local pools always mountable
                "lvm", 0+($tenderlist[$p] eq 'local' && ($mounts =~ m/\/dev\/mapper\/(\S+)-(\S+) $tenderpathslist[$p].+/g) ),
                "zfs", (($mounts =~ /(\S+) $tenderpathslist[$p] zfs/)?$1:''),
                "id", $p);
            $spools[$p] = \%pool;

            # Directory / mount point must exist
            unless (-d $tenderpathslist[$p]) {return "Status=Error $tenderpathslist[$p] could not be accessed"};

            # TODO: This section should be moved to pressurecontrol
            if ($tenderlist[$p] eq "local") {
                my $lpath = $tenderpathslist[$p];
                `mkdir "$lpath"` unless (-e $lpath);
                unless (`grep "$lpath 10" /etc/exports`) {
                    `echo "$lpath 10.0.0.0/255.255.255.0(sync,no_subtree_check,no_root_squash,rw)" >> /etc/exports`;
                    $reloadnfs = 1;
                }
            } elsif ($mounts =~ m/$tenderpathslist[$p]/i) {
                ; # do nothing
            } else {
                $main::syslogit->($user, 'info', "Mounting $tenderpathslist[$p] from $tenderlist[$p]");
                eval {
                    system("/bin/mount -o intr,noatime,nfsvers=3 $tenderlist[$p] $tenderpathslist[$p]");
                    1;} or {return "Status=Error $tenderpathslist[$p] could not be mounted"};
            }

            # Create user dir if it does not exist
            unless(-d "$tenderpathslist[$p]/$user"){
                umask "0000";
                mkdir "$tenderpathslist[$p]/$user" or {return "Status=Cannot create user dir for $user in  $tenderpathslist[$p]"};
            }
            unless(-d "$tenderpathslist[$p]/common"){
                umask "0000";
                mkdir "$tenderpathslist[$p]/common" or {return "Status=Cannot create common dir for $user in $tenderpathslist[$p]"};
            }
        }
    }
    `/usr/sbin/exportfs -r` if ($reloadnfs); #Reexport nfs shares

    # Create user's backupdir if it does not exist
    unless(-d "$backupdir/$user"){
        umask "0000";
        mkdir "$backupdir/$user" or {$postreply .= "Status=ERROR No backup dir $backupdir/$user\n"};
    }

}

sub getObj {
    my %h = %{@_[0]};
    my $status = $h{"status"};
    $console = 1 if $h{"console"};
    $api = 1 if $h{"api"};

    my $obj;
    $action = $action || $h{'action'};
    if ($action =~ /^clone|^sync_clone|^removeuserimages|^gear_removeuserimages|^activate|^gear_activate|^publish|^release|^download|^gear_publish|^gear_release|^zbackup|setimagesdevice|setbackupdevice|initializestorage|setstoragedevice/) {
        $obj = \%h;
        return $obj;
    }
    my $uuid = $h{"uuid"};
    if ($uuid eq 'this' && $curimg
        && ($register{$curimg}->{'user'} eq $user || $isadmin )) { # make an ugly exception
        $uuid = $register{$curimg}->{'uuid'};
    }
    my $objaction = lc $h{"action"};
    $status = "new" unless ($status || $h{'path'} || $uuid);
    if ($status eq "new") {
        $objaction = "";
    }
    if (!$uuid && $register{$h{'path'}} && ( $register{$h{'path'}}->{'user'} eq $user || $isadmin )) {
        $uuid = $register{$h{'path'}}->{'uuid'};
    }
    my $img = $imagereg{$uuid};
    $status = $img->{'status'} if ($imagereg{$uuid});
    if ($objaction eq 'buildsystem' && !$uuid && $h{'master'}) { # make another exception
        my $master = $h{'master'};
        foreach my $p (@spools) {
            my $dir = $p->{'path'};
            if ($master =~ /^$dir\/(common|$user)\/.+/ && $register{$master}) { # valid master image
                $uuid = $register{$master}->{'uuid'};
                last;
            }
            elsif ($register{"$dir/common/$master"}) { # valid master image
                $uuid = $register{"$dir/$user/$master"}->{'uuid'};
                last;
            }
            elsif ($register{"$dir/$user/$master"}) { # valid master image
                $uuid = $register{"$dir/$user/$master"}->{'uuid'};
                last;
            }
        }
    }
    my $path = '';
    $path = $img->{'path'} unless ($status eq "new"); # Only trust path from db /co
    my $dbobj = $register{$path} || {};

    return 0 unless (($path && $dbobj->{'user'} eq $user) || $isadmin || $status eq "new"); # Security check

    unless (($uuid && $imagereg{$uuid} && $status ne 'new') || ($status eq 'new' && !$imagereg{$uuid} && (!$uuid || length($uuid) == 36))) {
        $postreply .= "Status=ERROR Invalid image " . (($uuid)?" uuid: $uuid":"") . (($path)?" path: $path":"") . "\n";
        return 0;
    }
    if ($isadmin && $h{"status"}) {
        $status = $h{"status"} unless ($status eq "new");
    } else {
        $status = $dbobj->{'status'} unless ($status eq "new"); # Read status from db for existing images
    }
    my $virtualsize = $h{"virtualsize"} || $dbobj->{'virtualsize'};
    # allow shorthand size specifications
    $virtualsize = 1024 * $virtualsize if ($virtualsize =~ /k$/i);
    $virtualsize = 1024*1024* $virtualsize if ($virtualsize =~ /m$/i);
    $virtualsize = 1024*1024*1024* $virtualsize if ($virtualsize =~ /g$/i);
    $virtualsize = 10737418240 if ($status eq 'new' && !$virtualsize); # 10 GB

    $obj = {
        path           => $path,
        uuid           => $uuid,
        status         => $status,
        name           => $h{"name"} || $dbobj->{'name'}, # || 'New Image',
        size           => $h{"size"} || $dbobj->{'size'},
        realsize       => $dbobj->{'realsize'} || 0,
        virtualsize    => $virtualsize,
        ksize          => int($virtualsize / 1024),
        msize          => int($virtualsize / (1024 * 1024)),
        type           => $h{"type"} || $dbobj->{'type'} || 'qcow2',
        user           => $h{"user"} || $dbobj->{'user'},
        reguser        => $dbobj->{'user'},
        master         => $dbobj->{'master'},
        regstoragepool => $dbobj->{'storagepool'},
        storagepool   => (!$h{"storagepool"} && $h{"storagepool"} ne "0") ? $dbobj->{'storagepool'} : $h{"storagepool"},
        bschedule      => $h{"bschedule"} || $dbobj->{'bschedule'},
        notes          => $h{"notes"},
        installable    => ($installable && $installable ne "false") ? "true" : $h{"installable"},
        snap1          => $dbobj->{'snap1'},
        managementlink => $h{"managementlink"} || $dbobj->{'managementlink'},
        upgradelink    => $h{"upgradelink"} || $dbobj->{'upgradelink'},
        terminallink   => $h{"terminallink"} || $dbobj->{'terminallink'},
        image2         => $h{"image2"} || $dbobj->{'image2'},
        mac            => $h{"mac"} || $dbobj->{'mac'},
        backup         => $h{"backup"} || '',
        domains        => $dbobj->{'domains'} || '--',
        domainnames    => $dbobj->{'domainnames'} || '--'
    };
    # Handle restore of files
    $obj->{'restorepath'} = $h{'restorepath'} if ($h{'restorepath'});
    $obj->{'files'} = $h{'files'} if ($h{'files'});
    $obj->{'sync'} = 1 if ($h{'sync'});

    # Sanity checks
    if (
        ($obj->{name} && length $obj->{name} > 255)
            || ($obj->{virtualsize} && ($obj->{virtualsize}<1024 || $obj->{virtualsize} >1024**5))
            || ($obj->{master} && length $obj->{master} > 255)
            || ($obj->{bschedule} && length $obj->{bschedule} > 255)
            || ($path && length $path > 255)
            || ($obj->{image2} && length $obj->{image2} > 255)
    ) {
        $postreply .= "Status=ERROR Bad image data for: $obj->{name}\n";
        return 0;
    }
    # Security check
    if (($user ne $obj->{reguser} && $objaction ne 'clone' && $objaction ne 'buildsystem' && !$isadmin && $objaction))
    {
        $postreply .= "Status=ERROR No privs\n";
        return 0;
    }
    if ($status eq "new" && ($obj->{reguser} || -e $path)) {
        $postreply .= "Status=ERROR Image \"$obj->{name}\" already exists in $path\n";
        return 0;
    }
    if (!$path && $status ne "new") {
        $postreply .= "Status=ERROR Image $obj->{name} not found\n";
        return 0;
    }
    return $obj;
}

sub createNodeTask {
    my ($mac, $newtask, $wake) = @_;
    unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac'}, $Stabile::dbopts)) )
        {$postreply .= "Status=Error Node register could not be accessed"};

    if ($nodereg{$mac}->{'status'} =~ /asleep|inactive/  && !$wake) {
        $postreply .= "Status=Error Node $mac is asleep, not waking\n";
        return "Node is asleep, please wake first!";
    } else {
        my $tasks = $nodereg{$mac}->{'tasks'};
        $nodereg{$mac}->{'tasks'} = $tasks . "$newtask\n";
        tied(%nodereg)->commit;
    }
    untie %nodereg;
    return 0;
}

sub Recurse {
	my($path) = shift; # @_;
	my @files;
	## append a trailing / if it's not there
	$path .= '/' if($path !~ /\/$/);
	## loop through the files contained in the directory
	for my $eachFile (bsd_glob($path.'*')) {
	    next if ($eachFile =~ /\/fuel$/);
		## if the file is a directory
		if( -d $eachFile) {
			## pass the directory to the routine ( recursion )
			push(@files,Recurse($eachFile));
		} else {
			push(@files,$eachFile);
		}
	}
	return @files;
}

# If used with the -f switch ($fulllist) from console, all users images are updated in the db
# If used with the -p switch ($fullupdate), also updates status information (ressource intensive - runs through all domains)
sub Updateregister {
    my ($spath, $action) = @_;
    if ($help) {
        return <<END
GET:image,uuid:
If used with the -f switch ($fulllist) from console, all users images are updated in the db.
If used with the -p switch ($fullupdate), also updates status information (ressource intensive - runs through all domains)
END
    }
    return "Status=ERROR You must be an admin to do this!\n" unless ($isadmin);
    $fullupdate = 1 if ((!$fullupdate && $params{'fullupdate'}) || $action eq 'fullupdateregister');
    my $force = $params{'force'};
    my %userregister;
    my $res;
    # Update size information in db
    foreach my $u (@users) {
        foreach my $spool (@spools) {
            my $pooldir = $spool->{"path"};
            my $dir = "$pooldir/$u";
            my @thefiles = Recurse($dir);
            foreach my $f (@thefiles) {
                next if ($spath && $spath ne $f); # Only specific image being updated
                if ($f =~ /(.+)(-s\d\d\d\.vmdk$)/) {
                    `touch "$1.vmdk" 2>/dev/null` unless -e "$1.vmdk";
                } elsif ($f =~ /(.+)(-flat\.vmdk$)/) {
                    `touch "$1.vmdk" 2>/dev/null` unless -e "$1.vmdk";
                } elsif(-s $f && $f =~ /(\.vmdk$)|(\.img$)|(\.vhd$)|(\.qcow$)|(\.qcow2$)|(\.vdi$)|(\.iso$)/i) {
                    my($fname, $dirpath, $suffix) = fileparse($f, ("vmdk", "img", "vhd", "qcow", "qcow2", "vdi", "iso"));
                    my $uuid;
                    my $img = $register{$f};
                    $uuid = $img->{'uuid'};
            # Create a new uuid if we are dealing with a new file in the file-system
                    if (!$uuid) {
                        my $ug = new Data::UUID;
                        $uuid = $ug->create_str();
                    }
                    my $storagepool = $spool->{"id"};
            # Deal with sizes
                    my ($newmtime, $newbackupsize, $newsize, $newrealsize, $newvirtualsize) =
                        getSizes($f, $img->{'mtime'}, $img->{'status'}, $force);
                    my $size = $newsize || $img->{'size'};
                    my $realsize = $newrealsize || $img->{'realsize'};
                    my $virtualsize = $newvirtualsize || $img->{'virtualsize'};
                    my $mtime = $newmtime || $img->{'mtime'};
                    my $created = $img->{'created'} || $mtime;
                    my $name = $img->{'name'} || substr($fname,0,-1);

                    $register{$f} = {
                        path=>$f,
                        user=>$u,
                        type=>$suffix,
                        size=>$size,
                        realsize=>$realsize,
                        virtualsize=>$virtualsize,
                        backupsize=>$newbackupsize,
                        name=>$name,
                        uuid=>$uuid,
                    #    domains=>$domains,
                    #    domainnames=>$domainnames,
                        storagepool=>$storagepool,
                        backup=>"", # Only set in uservalues at runtime
                        created=>$created,
                        mtime=>$mtime
                    }
                }
            }
        }
    }
    # Update status information in db
#    my $mounts = decode('ascii-escape', `/bin/cat /proc/mounts`);
    my $mounts = `/bin/cat /proc/mounts`;
    unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
    foreach my $u (@users) {
        my @regkeys = (tied %register)->select_where("user = '$u'");
        foreach my $k (@regkeys) {
            my $valref = $register{$k};
            my $path = $valref->{'path'};
# Only update info for images the user has access to.
# Remove DB entries for images on removed nodes
            if ($valref->{'storagepool'}==-1 && $valref->{'mac'} && $valref->{'mac'} ne '--' && !$nodereg{$valref->{'mac'}}) {
                delete $register{$path}; # Clean up database, remove rows which don't have corresponding file
                $main::updateUI->({tab=>'images', user=>$u}) unless ($u eq 'common');
            } elsif ($valref->{'user'} eq $u && (defined $spools[$valref->{'storagepool'}]->{'id'} || $valref->{'storagepool'}==-1)) {
                my $path = $valref->{'path'};
                next if ($spath && $spath ne $path); # Only specific image being updated
                my $mounted = ($mounts =~ /$path/);
                my $domains;
                my $domainnames;
                my $regstatus = $valref->{'status'};
                my $status = $regstatus;
                if (!$status || $status eq '--') {
                    $status = 'unused';
                }
                if (-e $path || $valref->{'storagepool'}==-1 || -s "$path.meta") {
                # Deal with status
                    if ($valref->{'storagepool'}!=-1 && -s "$path.meta") {
                        my $metastatus;
                        $metastatus = `/bin/cat "$path.meta" 2>/dev/null`;
                        chomp $metastatus;

                        if ($metastatus =~ /status=(.+)&chunk=/) {
                            $status = $1;
                        } elsif ($metastatus =~ /status=(.+)&path2:(.+)=(.+)/) {
                        # A move operation has been completed - update status of both involved
                            $status = $1;
                            $register{$2}->{'status'} = $3;
                            unless ($userregister{$2}) { # If we have not yet parsed image, it is not yet in userregister, so put it there
                                my %mval = %{$register{$2}};
                                $userregister{$2} = \%mval;
                            }
                            $userregister{$2}->{'status'} = $3;
                        } elsif ($metastatus =~ /status=(\w+)/) {
                            $status = $1;
                        } else {
                        #    $status = $metastatus; # Do nothing - this meta file contains no status info
                        }
                    } elsif (
                            $status eq "restoring"
                            || $status eq "frestoring"
                            || ($status eq "mounted" && $mounted)
                            || $status eq "snapshotting"
                            || $status eq "unsnapping"
                            || $status eq "reverting"
                            || $status eq "moving"
                            || $status eq "converting"
                            || $status eq "cloning"
                            || $status eq "copying"
                            || $status eq "rebasing"
                            || $status eq "creating"
                            || $status eq "resizing"
                        ) { # When operation is done, status is updated by piston.cgi
                        ; # Do nothing
                    } elsif ($status =~ /.(backingup)/) { # When backup is done, status is updated by steamExec
                        if ($valref->{'storagepool'}==-1) {
                        #    unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
                            if ($nodereg{$valref->{'mac'}}) {
                                my $nodestatus = $nodereg{$valref->{'mac'}}->{status};
                                # If node is not available, it cannot be backing up...
                                if ($nodestatus eq 'inactive'
                                    || $nodestatus eq 'asleep'
                                    || $nodestatus eq 'shutoff'
                                ) {
                                    $valref->{'status'} = 'unused'; # Make sure we don't end here again in endless loop
                                    $rstatus = Updateregister(0, $path);
                                    $status = $rstatus if ($rstatus);
                                    $main::syslogit->($user, 'info', "Updated image status for aborted backup - $user, $path, $rstatus");
                                }
                            }
                            #untie %nodereg;
                        }

                    } elsif ($status eq 'uploading') {
                        $status = 'unused' unless (-s "$path.meta");

                    } elsif (!$status || $status eq 'unused' || $status eq 'active') {
                        if ($fullupdate) {
                            $status = "unused";
                            my @domregkeys;
                            if ($fulllist) {@domregkeys = keys %domreg;}
                            else {@domregkeys = (tied %domreg)->select_where("user = '$u'");}
                            foreach my $domkey (@domregkeys) {
                                my $dom = $domreg{$domkey};
                                my $img = $dom->{'image'};
                                my $img2 = $dom->{'image2'};
                                my $img3 = $dom->{'image3'};
                                my $img4 = $dom->{'image4'};
                                if ($path eq $img || $path eq $img2 || $path eq $img3 || $path eq $img4) {
                                    $status = "active";
                                    my $domstatus = $dom->{'status'};
                                    if ($domstatus eq "shutoff" || $domstatus eq "inactive") {$status = "used";}
                                    elsif ($domstatus eq "paused") {$status = "paused";}
                                    $domains = $dom->{'uuid'};
                                    $domainnames = $dom->{'name'};
                                };
                            }
                            $valref->{'domains'} = $domains ;
                            $valref->{'domainnames'} = $domainnames ;
                        } elsif ($valref->{'domains'} && $valref->{'domains'} ne '--'){
                            my $dom = $domreg{$valref->{'domains'}};
                            if ($dom) {
                                my $img = $dom->{'image'};
                                my $img2 = $dom->{'image2'};
                                my $img3 = $dom->{'image3'};
                                my $img4 = $dom->{'image4'};
                                if ($path eq $img || $path eq $img2 || $path eq $img3 || $path eq $img4) {
                                    $status = "active";
                                    my $domstatus = $dom->{'status'};
                                    if ($domstatus eq "shutoff" || $domstatus eq "inactive") {$status = "used";}
                                    elsif ($domstatus eq "paused") {$status = "paused";}
                                    $valref->{'domainnames'} = $dom->{'name'};
                                };
                            };
                        }
                    }
                    # Update info in db
                    $valref->{'status'} = $status ;
                    $res .= $status if ($spath);
                } else {
                    delete $register{$path}; # Clean up database, remove rows which don't have corresponding file
                    $main::updateUI->({tab=>'images', user=>$u}) unless ($u eq 'common');
                }
            }
        }
    }
    untie %nodereg;
    tied(%register)->commit;
    $res .= "Status=OK Updated image register for " . join(', ', @users) . "\n";
    return $res if ($res);
}

sub getVirtualSize {
    my $vpath = shift;
    my $macip = shift;
    my $qinfo;
    my($bname, $dirpath, $suffix) = fileparse($vpath, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));
    if ($suffix eq ".qcow2") {
        if ($macip) {
            $qinfo = `$sshcmd $macip /usr/bin/qemu-img info "$vpath"`;
        } else {
            $qinfo = `/usr/bin/qemu-img info "$vpath"`;
        }
        $qinfo =~ /virtual size:.*\((.+) bytes\)/g;
        return(int($1)); # report size of new image for billing purposes
    } elsif ($status eq ".vdi") {
        if ($macip) {
            $qinfo = `$sshcmd $macip /usr/bin/VBoxManage showhdinfo "$vpath"`;
        } else {
            $qinfo = `/usr/bin/VBoxManage showhdinfo "$vpath"`;
        }
        $qinfo =~ /Logical size:\s*(\d+) MBytes/g;
        return(int($1) * 1024 * 1024); # report size of new image for billing purposes
    } else {
        if ($macip) {
            return `$sshcmd $macip perl -e 'my @stat=stat("$vpath"); print $stat[7];'`;
        } else {
            my @stat = stat($vpath);
            return($stat[7]); # report size of new image for billing purposes
        }
    }
}

sub getSizes {
    my $f = shift;
    my $lmtime = shift;
    my $status = shift;
    my $force = shift;

    my @stat = stat($f);
    my $size = $stat[7];
    my $realsize = $stat[12] * 512;
    my $virtualsize = $size;
    my $backupsize = 0;
    my $mtime = $stat[9];
    my($fname, $dirpath, $suffix) = fileparse($f, ("vmdk", "img", "vhd", "qcow", "qcow2", "vdi", "iso"));

    my $subdir = "";
    if ($dirpath =~ /.+\/$buser(\/.+)?\//) {
        $subdir = $1;
    }
    my $bdu;
    if (-d "$backupdir/$user$subdir/$fname$suffix") {
        $bdu = `/usr/bin/du -bs "$backupdir/$user$subdir/$fname$suffix/"`;
        $bdu =~ /(\d+)\s+/;
        $backupsize = $1;
        #$main::syslogit->($user, 'info', $bdu);
    }
    my $ps = `/bin/ps ax`;

# Only fire up qemu-img etc. if image has been modified and is not being used
    if ((
        ($mtime - $lmtime)>300 &&
        ($status ne 'active' && $status ne 'downloading') &&
        !($ps =~ /$f/)) || $force
    ) {

# Special handling of vmdk's
        if ($suffix eq "vmdk") {
            my $qinfo = `/usr/bin/qemu-img info "$f"`;
            $qinfo =~ /virtual size:.*\((.+) bytes\)/g;
            $virtualsize = int($1);
            if ( -s ($dirpath . substr($fname,0,-1) . "-flat." . $suffix)) {
                my @fstatus = stat($dirpath . substr($fname,0,-1) . "-flat." . $suffix);
                my $fsize = $fstatus[7];
                my $frealsize = $fstatus[12] * 512;
                $size += $fsize;
                $virtualsize += $fsize;
                $realsize += $frealsize;
            } else {
#                $main::syslogit->($user, "info", "VMDK " . $dirpath . substr($fname,0,-1) . "-flat." . $suffix . " does not exist");
            }
            my $i = 1;
            while (@fstatus = stat($dirpath . substr($fname,0,-1) . "-s00$i." . $suffix)) {
                my $fsize = $fstatus[7];
                my $frealsize = $fstatus[12] * 512;
                $size += $fsize;
                #$virtualsize += $fsize;
                $realsize += $frealsize;

                my $cmdpath = $dirpath . substr($fname,0,-1) . "-s00$i." . $suffix;
                my $qinfo = `/usr/bin/qemu-img info "$cmdpath"`;
                $qinfo =~ /virtual size:.*\((.+) bytes\)/g;
                $virtualsize += int($1);

                $i++;
            }
# Get virtual size of qcow2 auto-grow volumes
        } elsif ($suffix eq "qcow2") {
            my $qinfo = `/usr/bin/qemu-img info "$f"`;
            $qinfo =~ /virtual size:.*\((.+) bytes\)/g;
            $virtualsize = int($1);
# Get virtual size of vdi auto-grow volumes
        } elsif ($suffix eq "vdi") {
            my $qinfo = `/usr/bin/VBoxManage showhdinfo "$f"`;
            $qinfo =~ /Logical size:\s*(\d+) MBytes/g;
            $virtualsize = int($1) * 1024 * 1024;
        }
# Actual used blocks times block size on disk, i.e. $realsize may be bigger than the
# logical size of the image file $size and the logical provisioned size of the disk $virtualsize
# in order to minimize confusion, we set $realsize to $size if this is the case
        $realsize = $size if ($realsize > $size);

        return ($mtime, $backupsize, $size, $realsize, $virtualsize);
    } else {
        return (0, $backupsize, $size, $realsize);
    }

}

sub getHypervisor {
	my $image = shift;
	# Produce a mapping of image file suffixes to hypervisors
	my %idreg;
    unless ( tie(%idreg,'Tie::DBI', Hash::Merge::merge({table=>'nodeidentities', key=>'identity'}, $Stabile::dbopts)) )
        {$postreply .= "Status=Error identity register could not be accessed"};

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

sub Getserverbackups {
    my ($domuuid, $action) = @_;
    if ($help) {
        return <<END
GET:uuid:
Lists the image backups associated with a server, i.e. the backups of all the images attached to a server.
A server UUID should be passed as parameter. A JSON object is returned. May be called as <b>getserverbackups</b>, in
which case a JSON object is returned, or as <b>listserverbackups</b>, in which case a string is returned.
END
    }
    my $res;
    my @sbackups;
    my $backuplist;

    if ($domreg{$domuuid} && (($domreg{$domuuid}->{'user'} eq $user) || $isadmin)) {
        push @sbackups, Listbackups($domreg{$domuuid}->{'image'}, 'getbackups');
        push @sbackups, Listbackups($domreg{$domuuid}->{'image2'}, 'getbackups') if ($domreg{$domuuid}->{'image2'} && $domreg{$domuuid}->{'image2'} ne '--');
        push @sbackups, Listbackups($domreg{$domuuid}->{'image3'}, 'getbackups') if ($domreg{$domuuid}->{'image3'} && $domreg{$domuuid}->{'image3'} ne '--');
        push @sbackups, Listbackups($domreg{$domuuid}->{'image4'}, 'getbackups') if ($domreg{$domuuid}->{'image4'} && $domreg{$domuuid}->{'image4'} ne '--');
    }
    foreach my $sbackup (@sbackups) {
        my @back = @{$sbackup};
        my $t = $back[0]->{time};
        my $epoch;
        my $z;
        if ($t eq '--') {
            $epoch = $t;
        } elsif ($t =~ /(z)/) {
#            my $time = Time::Piece->strptime($t, "%Y-%m-%d-%H-%M-%S (z)");
            my $time = Time::Piece->strptime($t, "%b %d %T %Y (z)");
            $epoch = $time->epoch;
            $z = ' (z)';
        } else {
            $t = $1 if ($t =~ /\* (.*)/);
            my $time = Time::Piece->strptime($t, "%b %d %T %Y");
            $epoch = $time->epoch;
        }
        $backuplist .= "$back[-1]->{name}$z/$epoch, " if (@back && $epoch);
    }
    $backuplist = substr($backuplist,0,-2);

    if ($action eq 'getserverbackups') {
        $res .= to_json(\@sbackups, {pretty=>1});
    } else {
        $res .= header() unless ($console);
        $res .= $backuplist;
    }
    return $res;

}

sub Listbackups {
    my ($curimg, $action) = @_;
    if ($help) {
        return <<END
GET:image:
List backups on file for the give image, which may be specified as path or uuid.
END
    }

    my $res;
    my $buser = $user;
    $curimg = '' unless ($register{$curimg}); # Image must exist
    $buser = $register{$curimg}->{'user'} if ($isadmin && $curimg);
    my @backups;
    my $subdir = "";
    if ($curimg && $curimg ne '--') {
        my($bname, $dirpath) = fileparse($curimg);
        if ($dirpath =~ /.+\/$buser(\/.+)?\//) {
            $subdir = $1;
        }
        my $sbname = "$subdir/$bname";
        $sbname =~ s/ /\\ /;
        $sbname = $1 if ($sbname =~ /(.+)/); # untaint
        foreach my $spool (@spools) {
            my $imgbasedir = $spool->{"path"};
            if (-d "$imgbasedir/.zfs/snapshot") {
                my $snaps = `/bin/ls -l --time-style=full-iso $imgbasedir/.zfs/snapshot/*/$buser$sbname 2> /dev/null`;
                my @snaplines = split("\n", $snaps);
                # -rw-r--r-- 1 root root 216174592 2012-02-19 17:51 /mnt/stabile/images/.zfs/snapshot/SNAPSHOT-20120106002116/cabo/Outlook2007.iso
                foreach $line (@snaplines) {
                    if ($line =~ /$imgbasedir\/.zfs\/snapshot\/SNAPSHOT-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\/$buser$subdir\/$bname$/) {
                        my $timestamp = timelocal($6,$5,$4,$3,$2-1,$1); #$sec,$min,$hour,$mday,$mon,$year
                        my $t = localtime($timestamp)->strftime("%b %e %H:%M:%S %Y");
                        # my %incr = ("increment", "SNAPSHOT-$1$2$3$4$5$6", "time", "$1-$2-$3-$4-$5-$6 (z)", "pool", $imgbasedir);
                        my %incr = ("increment", "SNAPSHOT-$1$2$3$4$5$6", "time", "$t (z)", "pool", $imgbasedir);
                        unshift (@backups, \%incr);
                    };
                }
            }
        }
        # Also include ZFS snapshots transferred from nodes
        $imgbasedir = "/stabile-backup";
        my $snaps = `/bin/ls -l --time-style=full-iso $imgbasedir/node-*/.zfs/snapshot/*/$buser$sbname 2> /dev/null`;
        my @snaplines = split("\n", $snaps);
        foreach $line (@snaplines) {
            if ($line =~ /($imgbasedir\/node-.+)\/.zfs\/snapshot\/SNAPSHOT-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\/$buser$subdir\/$bname$/) {
                my $timestamp = timelocal($7,$6,$5,$4,$3-1,$2); #$sec,$min,$hour,$mday,$mon,$year
                my $t = localtime($timestamp)->strftime("%b %e %H:%M:%S %Y");
                # my %incr = ("increment", "SNAPSHOT-$2$3$4$5$6$7", "time", "$2-$3-$4-$5-$6-$7 (z)", "pool", $1);
                my %incr = ("increment", "SNAPSHOT-$2$3$4$5$6$7", "time", "$t (z)", "pool", $1);
                unshift (@backups, \%incr);
            };
        }
        my $bpath = "$backupdir/$buser$subdir/$bname";
        $bpath = $1 if ($bpath =~ /(.+)/); # untaint
        if (-d "$bpath") {
            my $rdiffs = `/usr/bin/rdiff-backup -l "$bpath"`;
            my @mlines = split("\n", $rdiffs);
            my $curmirror;
            foreach my $line (@mlines) {
                if ($line =~ /\s+increments\.(\S+)\.dir\s+\S\S\S (.+)$/) {
                    my %incr = ("increment", $1, "time", $2);
                    if (-e "$bpath/rdiff-backup-data/increments/$bname.$1.diff.gz"
                    ) {
                        unshift (@backups, \%incr);
                    }
                };
                if ($line =~ /Current mirror: \S\S\S (.+)$/) {
                    $curmirror = $1;
                };
            }
            if ($curmirror) {
                my %incr = ("increment", "mirror", "time", "* $curmirror");
                unshift @backups, \%incr;
            }
            my %incr = ("increment", "--", "time", "--", "name", $bname);
            push @backups, \%incr;
        } else {
            my %incr = ("increment", "--", "time", "--", "name", $bname);
            push @backups, \%incr;
        }
    }

    if ($action eq 'getbackups') {
        return \@backups;
    } elsif ($console) {
        my $t2 = Text::SimpleTable->new(28,28);
        $t2->row('increment', 'time');
        $t2->hr;
        foreach my $fref (@backups) {
            $t2->row($fref->{'increment'}, scalar localtime( $fref->{'time'} )) unless ($fref->{'increment'} eq '--');
        }
        return $t2->draw;
    } else {
        $res .= header('application/json');
        my $json_text = to_json(\@backups, {pretty=>1});
        $res .= qq|{"identifier": "increment", "label": "time", "items": $json_text }|;
        return $res;
    }
}

# Get the timestamp of latest backup of an image
sub getBtime {
    my $curimg = shift;
    my $buser = shift || $user;
    return unless ($buser eq $user || $isadmin);
    $buser = 'common' if ($register{$curimg}->{user} eq 'common' && $isadmin);
    my $subdir = "";
    my $lastbtimestamp;
    my($bname, $dirpath) = fileparse($curimg);
    if ($dirpath =~ /.+\/$buser(\/.+)?\//) {
        $subdir = $1;
    }

    #require File::Spec;
    #my $devnull = File::Spec->devnull();

    foreach my $spool (@spools) {
        my $imgbasedir = $spool->{"path"};
        if (-d "$imgbasedir/.zfs/snapshot") {
            my $sbname = "$subdir/$bname";
            $sbname =~ s/ /\\ /;
            my $cmd = qq|/bin/ls -l --time-style=full-iso $imgbasedir/.zfs/snapshot/*/$buser$sbname 2>/dev/null|;
            my $snaps = `$cmd`;
            my @snaplines = split("\n", $snaps);
            foreach $line (@snaplines) {
                if ($line =~ /$imgbasedir\/.zfs\/snapshot\/SNAPSHOT-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\/$buser$subdir\/$bname$/) {
                    my $timestamp = timelocal($6,$5,$4,$3,$2-1,$1); #$sec,$min,$hour,$mday,$mon,$year
                    $lastbtimestamp = $timestamp if ($timestamp > $lastbtimestamp);
                };
            }
        }
    }
    # Also include ZFS snapshots transferred from nodes
    $imgbasedir = "/stabile-backup";
    my $snaps = `/bin/ls -l --time-style=full-iso $imgbasedir/node-*/.zfs/snapshot/*/$buser/$bname 2> /dev/null`;
    my @snaplines = split("\n", $snaps);
    foreach $line (@snaplines) {
        if ($line =~ /$imgbasedir\/node-.+\/.zfs\/snapshot\/SNAPSHOT-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\/$buser$subdir\/$bname$/) {
            my $timestamp = timelocal($6,$5,$4,$3,$2-1,$1); #$sec,$min,$hour,$mday,$mon,$year
            $lastbtimestamp = $timestamp if ($timestamp > $lastbtimestamp);
        };
    }
    my $bpath = "$backupdir/$buser$subdir/$bname";
    $bpath = $1 if ($bpath =~ /(.+)/);
    if (-d "$bpath") {
        my $rdiffs = `/usr/bin/rdiff-backup --parsable-output -l "$bpath"`;
        my @mlines = split("\n", $rdiffs);
        foreach my $line (@mlines) {
            if ($line =~ /(\d+) (\S+)$/) {
                my $timestamp = $1;
                $lastbtimestamp = $timestamp if ($timestamp > $lastbtimestamp);
            };
        }
    }
    return $lastbtimestamp;
}

sub Unmount {
    my $path = shift;
	my $action = shift;
    if ($help) {
        return <<END
GET:image: Unmounts a previously mounted image.
END
    }
    my($bname, $dirpath, $suffix) = fileparse($path, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));
    my $mountpath = "$dirpath.$bname$suffix";
#    my $mounts = decode('ascii-escape', `/bin/cat /proc/mounts`);
    my $mounts = `/bin/cat /proc/mounts`;
    my $mounted = ($mounts =~ /$mountpath/);

#    eval {`/bin/umount "$mountpath"` if ($mounted); 1;}
#    eval {`/bin/fusermount -u "$mountpath"` if ($mounted); 1;}
#        or do {$postreply .= "Status=ERROR Problem mounting image $@\n";};

    if ($mounted) {
        $cmd = qq|/bin/fusermount -u "$mountpath" 2>&1|;
        my $mes = qx($cmd);
        my $xc = $? >> 8;
        $main::syslogit->($user, 'info', "Unmounted $curimg $xc");
        if ($xc) {
            $postreply .= "Status=ERROR Problem unmounting image ($mes). ";
            return $postreply;
        }
    }
#    my $mounts2 = decode('ascii-escape', `/bin/cat /proc/mounts`);
    my $mounts2 = `/bin/cat /proc/mounts`;
    my $mounted2 = ($mounts2 =~ /$mountpath/);
    eval {`/bin/rmdir "$mountpath"` if (!$mounted2 && -e $mountpath); 1;}
        or do {$postreply .= "Status=ERROR Problem removing mount point $@\n";};

    if ($mounted) {
        if ($mounted2) {
            $postreply .= "Status=ERROR Unable to unmount $register{$path}->{'name'}\n";
            return $postreply;
        } else {
            $postreply .= "Status=OK Unmounted image $register{$path}->{'name'}\n";
            return $postreply;
        }
    } else {
        $postreply .= "Status=OK Image $register{$path}->{'name'} not mounted\n";
        return $postreply;
    }
}

sub unmountAll {
    my @mounts = split(/\n/, `/bin/cat /proc/mounts`);
    foreach my $mount (@mounts) {
        foreach my $spool (@spools) {
            my $pooldir = $spool->{"path"};
            if ($mount =~ /($pooldir\/$user\/\S+) / || ($mount =~ /($pooldir\/common\/\S+) / && $isadmin)) {
#                $mountpath = decode('ascii-escape', $1);
                $mountpath =  $1;
                $rpath = $mountpath;
                $rpath =~ s/\/\./\//;
                my $processes = `/bin/ps`;
#                if ($register{$rpath} && !($processes =~ /steamExec.+$rpath/)) {
                    $postreply .= "Status=OK Unmounting $rpath\n";
                    Unmount($rpath);
#                }
            }
        }
    }
    return;
}

sub Mount {
    my $path = shift;
	my $action = shift;
    if ($help) {
        return <<END
GET:image:
Tries to mount an image on admin server for listfiles/restorefiles operations.
END
    }
    my($bname, $dirpath, $suffix) = fileparse($path, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));
    my $mountpath = "$dirpath.$bname$suffix";
#    my $mounts = decode('ascii-escape', `/bin/cat /proc/mounts`);
    my $mounts = `/bin/cat /proc/mounts`;
    my $mounted = ($mounts =~ /$mountpath/);
    if ($mounted) {
        unless (`ls "$mountpath"`) { # Check if really mounted
            Unmount($path);
            $mounted = 0;
        }
    }

    if ($mounted) {
        $postreply .= "Status=OK Image $register{$path}->{'name'} already mounted\n";
        return $postreply;
    } else {
        `/bin/mkdir "$mountpath"` unless (-e "$mountpath");
        `/bin/chown www-data:www-data  "$mountpath"`;
        my $cmd;

        if (lc $suffix eq '.iso') {
            #eval {`/bin/mount -o allow_other,ro,loop "$path" "$mountpath"`; 1;}
            #eval {`/usr/bin/fuseiso -n "$path" "$mountpath" -o user=www-data`; 1;}
            eval {`/usr/bin/fuseiso -n "$path" "$mountpath" -o allow_other`; 1;}
            or do {
                $postreply .= header('text/html', '500 Internal Server Error') unless ($console);
                $postreply .= "Status=ERROR Problem mounting image $@\n";
                return $postreply;
            };
        } else {
            $cmd = qq|/usr/bin/guestmount --ro -o allow_other -a "$path" "$mountpath" -i 2>&1|;
            my $mes = qx($cmd);
            my $xc = $? >> 8;
            $main::syslogit->($user, 'info', "Mounted $curimg $xc");
            if ($xc) {
                $postreply = header('text/html', '500 Internal Server Error') . $postreply unless ($console);
                chomp $mes;
                $postreply .= "Status=Error Problem mounting image ($mes).\n$cmd\n";
                return $postreply;
            }
        }

        my $mounts2;
        for (my $i=0; $i<5; $i++) {
#            $mounts2 = decode('ascii-escape', `/bin/cat /proc/mounts`);
            $mounts2 = `/bin/cat /proc/mounts`;
            next if ( $mounts2 =~ /$mountpath/);
            sleep 2;
        }
        if ( $mounts2 =~ /$mountpath/) {
            $postreply .= "Status=OK Mounted image $register{$path}->{'name'}\n";
            return $postreply;
        } else {
            $postreply .= header('text/html', '500 Internal Server Error') unless ($console);
            $postreply .= "Status=ERROR Giving up mounting image $register{$path}->{'name'}\n";
            return $postreply;
        }
    }
}

sub Updatebackingfile {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET:image:
END
    }
    my $f = $img || $curimg;
    return "Status=Error Image $f not found\n" unless (-e $f);
    my $vinfo = `qemu-img info "$f"`;
    my $master = $1 if ($vinfo =~ /backing file: (.+)/);
    return "Status=Error Image $f does not use a backing file\n" unless ($master);
    return "Status=OK $master exists, no changes to $f.\n" if (-e $master); # Master OK
    (my $fname, my $fdir) = fileparse($f);
    return "Status=OK $master exists in $fdir. No changes to $f.\n" if (-e "$fdir/$master"); # Master OK
    # Master not immediately found, look for it
    (my $master, my $mdir) = fileparse($master);
    my @busers = @users;
    push (@busers, $billto) if ($billto); # We include images from 'parent' user
    foreach my $u (@busers) {
        foreach my $spool (@spools) {
            my $pooldir = $spool->{"path"};
            my $masterpath = "$pooldir/$u/$master";
            if (-e $masterpath) {
                my $cmd = qq|qemu-img rebase -f qcow2 -u -b "$masterpath" "$f"|;
                $postreply .= "Status=OK found $masterpath, rebasing from $mdir to $pooldir/$u ";
                $postreply .= `$cmd` . "\n";
                last;
            }
        }
    }
    $postreply .= "Status=Error $master not found in any user dir. You must provide this backing file to use this image.\n" unless ($postreply);
    return $postreply;
}

# List files in a mounted image. Mount image if not mounted.
sub Listfiles {
    my ($curimg, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image,path:
Try to mount the file system on the given image, and list the files from the given path in the mounted file system.
The image must contain a bootable file system, in order to locate a mount point.
END
    }
    my $res;
    my $curpath = $obj->{'restorepath'};
    $res .= header('application/json') unless ($console);

    my($bname, $dirpath, $suffix) = fileparse($curimg, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));
    my $mountpath = "$dirpath.$bname$suffix";
	my @files;
	my @dirs;
    my $mounted = (Mount($curimg) =~ /\w=OK/);

    if ($mounted) {
        my @patterns = ('');
        $curpath .= '/' unless ($curpath =~ /\/$/);
        $mountpath .= "$curpath";
        if (-d $mountpath) { # We are listing a directory
            # loop through the files contained in the directory
            @patterns = ('*', '.*');
        }
        foreach $pat (@patterns) {
            for my $f (bsd_glob($mountpath.$pat)) {
                my %fhash;
                ($bname, $dirpath) = fileparse($f);
                my @stat = stat($f);
                my $size = $stat[7];
                my $realsize = $stat[12] * 512;
                my $mtime = $stat[9];

                $fhash{'name'} = $bname;
                $fhash{'mtime'} = $mtime;
                ## if the file is a directory
                if( -d $f) {
                    $fhash{'size'} = 0;
                    $fhash{'fullpath'} = $f . '/';
                    $fhash{'path'} = $curpath . $bname . '/';
                    push(@dirs, \%fhash) unless ($bname eq '.' || $bname eq '..');
                } else {
                    $fhash{'size'} = $size;
                    $fhash{'fullpath'} = $f;
                    $fhash{'path'} = $curpath . $bname;
                    push(@files, \%fhash);
                }
            }
        }

        if ($console) {
            my $t2 = Text::SimpleTable->new(48,16,28);
            $t2->row('name', 'size', 'mtime');
            $t2->hr;
            foreach my $fref (@dirs) {
                $t2->row($fref->{'name'}, $fref->{'size'}, scalar localtime( $fref->{'mtime'} )) unless ($bname eq '.' || $bname eq '..');
            }
            foreach my $fref (@files) {
                $t2->row($fref->{'name'}, $fref->{'size'}, scalar localtime( $fref->{'mtime'} ) ) unless ($bname eq '.' || $bname eq '..');
            }
            return $t2->draw;
        } else {
            my @comb = (@dirs, @files);
            $res .= to_json(\@comb, {pretty => 1});
        }
    } else {
        $res .= qq|{"status": "Error", "message": "Image not mounted. Mount first."}|;
    }
    return $res;
}

sub Restorefiles {
    my ($path, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image,files:
Restores files from the given path in the given image to a newly created ISO image. The given image must be mountable.
END
    }
    my $res;
    $curfiles = $obj->{'files'};
    $path = $path || $curimg;

    return "Status=ERROR Your account does not have the necessary privileges\n" if ($isreadonly);
    return "Status=ERROR You must specify which files you want to restore\n" unless ($curfiles);

    my $name = $register{$path}->{'name'};
    my($bname, $dirpath, $suffix) = fileparse($path, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));
    my $mountpath = "$dirpath.$bname$suffix";
#    my $mounts = decode('ascii-escape', `/bin/cat /proc/mounts`);
    my $mounts = `/bin/cat /proc/mounts`;
    my $mmounts = `/bin/df`;
    my $mounted = ($mounts =~ /$mountpath/ && $mmounts =~ /$mountpath/);
    my $restorepath = "$dirpath$bname.iso";

    if (-e $restorepath) {
        my $i = 1;
        while (-e "$dirpath$bname.$i.iso") {$i++;}
        $restorepath = "$dirpath$bname.$i.iso";
    }

    my $uistatus = "frestoring";
    if ($mounted && $curfiles) {
        my $ug = new Data::UUID;
        my $newuuid = $ug->create_str();
        $register{$restorepath} = {
                            uuid=>$newuuid,
                            status=>$uistatus,
                            name=>"Files from: $name",
                            size=>0,
                            realsize=>0,
                            virtualsize=>0,
                            type=>"iso",
                            user=>$user
                        };

        eval {
                my $oldstatus = $register{$path}->{'status'};
#                my $cmd = qq|steamExec $user $uistatus $oldstatus "$path" "$curfiles"|;
#                my $cmdres = `$cmd`;
            if ($mounted) {
                $res .= "Restoring files to: /tmp/restore/$user/$bname$suffix -> $restorepath\n";
                $res .= `/bin/echo $status > "$restorepath.meta"`;

                `/bin/mkdir -p "/tmp/restore/$user/$bname$suffix"` unless (-e "/tmp/restore/$user/$bname$suffix");
                my @files = split(/:/, uri_unescape($curfiles));
                foreach $f (@files) {
                    if (-e "$mountpath$f" && chdir($mountpath)) {
                        $f = substr($f,1) if ($f =~ /^\//);
                        eval {`/usr/bin/rsync -aR --sparse "$f" /tmp/restore/$user/$bname$suffix`; 1;}
                            or do {$e=1; $res .= "ERROR Problem restoring files $@\n";};
                    } else {
                        $res .= "Status=Error $f not found in $mountpath\n";
                    }
                }
                if (chdir "/tmp/restore/$user/$bname$suffix") {
                    eval {$res .= `/usr/bin/genisoimage -o "$restorepath" -iso-level 4 .`; 1;}
                        or do {$e=1; $res .= "Status=ERROR Problem restoring files $@\n";};
                    $res .= `/bin/rm -rf /tmp/restore/$user/$bname$suffix`;
                    $res .= "Status=OK Restored files from /tmp/restore/$user/$bname$suffix to $restorepath\n";
                } else {
                    $res .= "Status=ERROR Unable to chdir to /tmp/restore/$user/$bname$suffix\n";
                }
                $main::updateUI->({tab=>"images", user=>$user, type=>"update"});

                # Update billing
                my $newvirtualsize = getVirtualSize($restorepath);
                unlink "$restorepath.meta";
                $res .= Unmount($path);
                $register{$restorepath}->{'status'} = 'unused';
                $register{$restorepath}->{'virtualsize'} = $newvirtualsize;
                $register{$restorepath}->{'realsize'} = $newvirtualsize;
                $register{$restorepath}->{'size'} = $newvirtualsize;
                $postmsg = "OK - restored your files into a new ISO.";
            } else {
                $res .= "Status=Error You must mount image on $mountpath before restoring\n";
            }
            $res .=  "Status=OK $uistatus files from $name to iso, $newuuid, $cmd\n";
            $main::syslogit->($user, "info", "$uistatus files from $path to iso, $newuuid");
            1;
        } or do {$res .= "Status=ERROR $@\n";}

    } else {
        $res .= "Status=ERROR Image not mounted, mount before restoring: ". $curfiles ."\n";
    }
    return $res;
}

sub trim{
   my $string = shift;
   $string =~ s/^\s+|\s+$//g;
   return $string;
}

sub overQuotas {
    my $inc = shift;
    my $onnode = shift;
	my $usedstorage = 0;
	my $overquota = 0;
    return $overquota if ($Stabile::userprivileges =~ /a/); # Don't enforce quotas for admins

	my $storagequota = ($onnode)?$Stabile::usernodestoragequota:$Stabile::userstoragequota;
	if (!$storagequota) { # 0 or empty quota means use defaults
        $storagequota = (($onnode)?$Stabile::config->get('NODESTORAGE_QUOTA'):$Stabile::config->get('STORAGE_QUOTA')) + 0;
	}
    return $overquota if ($storagequota == -1); # -1 means no quota

    my @regkeys = (tied %register)->select_where("user = '$user'");
    foreach my $k (@regkeys) {
        my $val = $register{$k};
		if ($val->{'user'} eq $user) {
		    $usedstorage += $val->{'virtualsize'} if ((!$onnode &&  $val->{'storagepool'}!=-1) || ($onnode &&  $val->{'storagepool'}==-1));
		}
	}
    #print header(), "$package, $Stabile::Systems::userstoragequota, $onnode, $usedstorage, $inc, $storagequota, " . $storagequota*1024*1024; exit;
	return $overquota;
}

sub overStorage {
    my ($reqstor, $spool, $mac) = @_;
    my $storfree;
    if ($spool == -1) {
        if ($mac) {
            unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
            $storfree = $nodereg{$mac}->{'storfree'};
            $storfree = $storfree *1024 * $nodestorageovercommission;
            untie %nodereg;
        } else {
            return 1;
        }
    } else {
        my $storpath = $spools[$spool]->{'path'};
        $storfree = `df $storpath`;
        $storfree =~ m/(\d\d\d\d+)(\s+)(\d\d*)(\s+)(\d\d+)(\s+)(\S+)/i;
        my $stortotal = $1;
        my $storused = $3;
        $storfree = $5 *1024;
    }
    return ($reqstor > $storfree);
}

sub updateBilling {
    my $event = shift;
    my %billing;

    my @regkeys = (tied %register)->select_where("user = '$user'");
    foreach my $k (@regkeys) {
        my $valref = $register{$k};
        my %val = %{$valref}; # Deference and assign to new array, effectively cloning object
        $val{'virtualsize'} += 0;
        $val{'realsize'} += 0;
        $val{'backupsize'} += 0;

        if ($val{'user'} eq $user && (defined $spools[$val{'storagepool'}]->{'id'} || $val{'storagepool'}==-1)) {
            $billing{$val{'storagepool'}}->{'virtualsize'} += $val{'virtualsize'};
            $billing{$val{'storagepool'}}->{'realsize'} += $val{'realsize'};
            $billing{$val{'storagepool'}}->{'backupsize'} += $val{'backupsize'};
        }
    }

    my %billingreg;

    unless (tie %billingreg,'Tie::DBI', {
            db=>'mysql:steamregister',
            table=>'billing_images',
            key=>'userstoragepooltime',
            autocommit=>0,
            CLOBBER=>3,
            user=>$dbiuser,
            password=>$dbipasswd}) {throw Error::Simple("Stroke=Error Billing register (images) could not be accessed")};

    my $monthtimestamp = timelocal(0,0,0,1,$mon,$year); #$sec,$min,$hour,$mday,$mon,$year

    unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'billing_images', key=>'userstoragepooltime'}, $Stabile::dbopts)) )
        {throw Error::Simple("Status=Error Billing register could not be accessed")};

    my %pool = ("hostpath", "--",
                "path", "--",
                "name", "local",
                "rdiffenabled", 1,
                "id", -1);
    my @bspools = @spools;
    push @bspools, \%pool;

    foreach my $spool (@bspools) {
        my $storagepool = $spool->{"id"};
        my $b = $billing{$storagepool};
        my $virtualsize = $b->{'virtualsize'} +0;
        my $realsize = $b->{'realsize'} +0;
        my $backupsize = $b->{'backupsize'} +0;

# Setting default start averages for use when no row found under the assumption that we entered a new month
        my $startvirtualsizeavg = 0;
        my $virtualsizeavg = 0;
        my $startrealsizeavg = 0;
        my $realsizeavg = 0;
        my $startbackupsizeavg = 0;
        my $backupsizeavg = 0;
        my $starttimestamp = $current_time;
# We have proably entered a new month if less than 4 hours since change of month, since this is run hourly
        if ($current_time - $monthtimestamp < 4*3600) {
            $starttimestamp = $monthtimestamp;
            $startvirtualsizeavg = $virtualsizeavg = $virtualsize;
            $startrealsizeavg = $realsizeavg = $realsize;
            $startbackupsizeavg = $backupsizeavg = $backupsize;
        }
        # Update existing row
        if ($billingreg{"$user-$storagepool-$year-$month"}) {
            if (
                ($virtualsize != $billingreg{"$user-$storagepool-$year-$month"}->{'virtualsize'})
                || ($realsize != $billingreg{"$user-$storagepool-$year-$month"}->{'realsize'})
                || ($backupsize != $billingreg{"$user-$storagepool-$year-$month"}->{'backupsize'})
            )
            {
            # Sizes changed, update start averages and time, i.e. move the marker
            # Averages and start averages are the same when a change has occurred
                $startvirtualsizeavg = $virtualsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'virtualsizeavg'};
                $startrealsizeavg = $realsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'realsizeavg'};
                $startbackupsizeavg = $backupsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'backupsizeavg'};
                $starttimestamp = $current_time;
            } else {
            # Update averages and timestamp when no change on existing row
                $startvirtualsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'startvirtualsizeavg'};
                $startrealsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'startrealsizeavg'};
                $startbackupsizeavg = $billingreg{"$user-$storagepool-$year-$month"}->{'startbackupsizeavg'};
                $starttimestamp = $billingreg{"$user-$storagepool-$year-$month"}->{'starttimestamp'};

                $virtualsizeavg = ($startvirtualsizeavg*($starttimestamp - $monthtimestamp) + $virtualsize*($current_time - $starttimestamp)) /
                                ($current_time - $monthtimestamp);
                $realsizeavg = ($startrealsizeavg*($starttimestamp - $monthtimestamp) + $realsize*($current_time - $starttimestamp)) /
                                ($current_time - $monthtimestamp);
                $backupsizeavg = ($startbackupsizeavg*($starttimestamp - $monthtimestamp) + $backupsize*($current_time - $starttimestamp)) /
                                ($current_time - $monthtimestamp);
            }
            # Update sizes in DB
                $billingreg{"$user-$storagepool-$year-$month"}->{'virtualsize'} = $virtualsize;
                $billingreg{"$user-$storagepool-$year-$month"}->{'realsize'} = $realsize;
                $billingreg{"$user-$storagepool-$year-$month"}->{'backupsize'} = $backupsize;
            # Update start averages
                $billingreg{"$user-$storagepool-$year-$month"}->{'startvirtualsizeavg'} = $startvirtualsizeavg;
                $billingreg{"$user-$storagepool-$year-$month"}->{'startrealsizeavg'} = $startrealsizeavg;
                $billingreg{"$user-$storagepool-$year-$month"}->{'startbackupsizeavg'} = $startbackupsizeavg;
            # Update current averages with values just calculated
                $billingreg{"$user-$storagepool-$year-$month"}->{'virtualsizeavg'} = $virtualsizeavg;
                $billingreg{"$user-$storagepool-$year-$month"}->{'realsizeavg'} = $realsizeavg;
                $billingreg{"$user-$storagepool-$year-$month"}->{'backupsizeavg'} = $backupsizeavg;
            # Update time stamps and inc
                $billingreg{"$user-$storagepool-$year-$month"}->{'timestamp'} = $current_time;
                $billingreg{"$user-$storagepool-$year-$month"}->{'starttimestamp'} = $starttimestamp;
                $billingreg{"$user-$storagepool-$year-$month"}->{'inc'}++;

        # Write new row
        } else {
            $billingreg{"$user-$storagepool-$year-$month"} = {
                virtualsize=>$virtualsize+0,
                realsize=>$realsize+0,
                backupsize=>$backupsize+0,

                virtualsizeavg=>$virtualsizeavg,
                realsizeavg=>$realsizeavg,
                backupsizeavg=>$backupsizeavg,

                startvirtualsizeavg=>$startvirtualsizeavg,
                startrealsizeavg=>$startrealsizeavg,
                startbackupsizeavg=>$startbackupsizeavg,

                timestamp=>$current_time,
                starttimestamp=>$starttimestamp,
                event=>$event,
                inc=>1,
            };
        }
    }
    tied(%billingreg)->commit;
    untie %billingreg;
}

sub Removeuserimages {
    my ($path, $action, $obj) = @_;
    if ($help) {
        return <<END
GET::
Removes all images belonging to a user from storage, i.e. completely deletes the image and its backups (be careful).
END
    }

    $postreply = removeUserImages($user) unless ($isreadonly);
    return $postreply;
}

sub removeUserImages {
    my $username = shift;
    return unless ($username && ($isadmin || $user eq $username) && !$isreadonly);
    $user = $username;
    foreach my $path (keys %register) {
        if ($register{$path}->{'user'} eq $user) {
            $postreply .=  "Removing " . ($preserveimagesonremove?"(preserving) ":"") . " $username image $register{$path}->{'name'}, $uuid" . ($console?'':'<br>') . "\n";
            Remove($path, 'remove', 0, $preserveimagesonremove);
        }
    }
    $postreply .= "Status=Error No storage pools!\n" unless (@spools);
    foreach my $spool (@spools) {
        my $pooldir = $spool->{"path"};
        unless (-e $pooldir) {
            $postreply .= "Status=Error Storage $pooldir, $spool->{name} does not exist\n" unless (@spools);
            next;
        }

        $postreply .= "Status=OK Removing user dir $pooldir/$username ";
        $postreply .= `/bin/rm "$pooldir/$username/.htaccess"` if (-e "$pooldir/$username/.htaccess");
        $postreply .= `/bin/rmdir --ignore-fail-on-non-empty "$pooldir/$username/fuel"` if (-e "$pooldir/$username/fuel");
        $postreply .= `/bin/rmdir --ignore-fail-on-non-empty "$pooldir/$username"` if (-e "$pooldir/$username");
        $postreply .= "\n";
    }

    unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};

    foreach $mac (keys %nodereg) {
        $macip = $nodereg{$mac}->{'ip'};
        my $esc_path = "/mnt/stabile/node/$username";
        $esc_path =~ s/([ ])/\\$1/g;
        if (!$preserveimagesonremove) {
            `$sshcmd $macip "/bin/rmdir $esc_path"`;
            $postreply .= "Status=OK Removing node user dir /mnt/stabile/node/$username on node $mac\n";
        }
    }
    untie %nodereg;

    return $postreply;
}

sub Remove {
    my ($path, $action, $obj, $preserve) = @_;
    if ($help) {
        return <<END
DELETE:image:
Removes an image from storage, i.e. completely deletes the image and its backups (be careful).
END
    }
    $path = $imagereg{$path}->{'path'} if ($imagereg{$path}); # Check if we were passed a uuid
    $path = $curimg if (!$path && $register{$curimg});
    if (!$path && $curimg && !($curimg =~ /\//) ) { # Allow passing only image name if we are deleting an app master
        my $dspool = $stackspool;
        $dspool = $spools[0]->{'path'} unless ($engineid eq $valve001id);
        if ($curimg =~ /\.master.qcow2$/ && $register{"$dspool/$user/$curimg"}) {
            $path = "$dspool/$user/$curimg";
        } elsif ($isadmin && $curimg =~ /\.master.qcow2$/ && $register{"$dspool/common/$curimg"}) {
            $path = "$dspool/common/$curimg";
        }
    }
    utf8::decode($path);

    my $img = $register{$path};
    my $status = $img->{'status'};
    my $mac = $img->{'mac'};
    my $name = $img->{'name'};
    my $uuid = $img->{'uuid'};
    utf8::decode($name);
    my $type = $img->{'type'};
    my $username = $img->{'user'};

    unless ($username && ($isadmin || $user eq $username) && !$isreadonly) {
        return qq|[]|;
#        $postmsg = "Cannot delete image";
#        $postreply .= "Status=Error $postmsg\n";
#        return $postreply;
    }

    $uistatus = "deleting";
    if ($status eq "unused" || $status eq "uploading" || $path =~ /(.+)\.master\.$type/) {
        my $haschildren = 0;
        my $master = ($img->{'master'} && $img->{'master'} ne '--')?$img->{'master'}:'';
        my $usedmaster = '';
        my $child;
        my @regvalues = values %register;
        foreach my $valref (@regvalues) {
            if ($valref->{'master'} eq $path) {
                $haschildren = 1;
                $child = $valref->{'name'};
            #    last;
            }
            if ($master) {
                $usedmaster = 1 if ($valref->{'master'} eq $master && $valref->{'path'} ne $path); # Check if another image is also using this master
            }
        }
        if ($master && !$usedmaster) {
            $register{$master}->{'status'} = 'unused';
            $main::syslogit->($user, "info", "Freeing master $master");
        }

        if ($haschildren) {
            $postmsg = "Cannot delete image. This image is used as master by: $child";
            $postreply .= "Status=Error $postmsg\n";
        } else {
            if ($mac && $path =~ /\/mnt\/stabile\/node\//) {
                unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return "Status=Error Cannot connect to DB\n";};
                $macip = $nodereg{$mac}->{'ip'};
                my $wakenode = ($nodereg{$mac}->{'status'} eq 'asleep' || $nodereg{$mac}->{'status'} eq 'waking');

                if ($wakenode) {
                    my $tasks = $nodereg{$mac}->{'tasks'};
                    my $upath = URI::Escape::uri_escape($path);
                    $tasks .= "REMOVE $upath $user\n";
                    $nodereg{$mac}->{'tasks'} = $tasks;
                    tied(%nodereg)->commit;
                    $postmsg = "We are waking up the node your image $name is on - it will be removed shortly";
                    if ($nodereg{$mac}->{'status'} eq 'asleep') {
                        require "$Stabile::basedir/cgi/nodes.cgi";
                        $Stabile::Nodes::console = 1;
                        Stabile::Nodes::wake($mac);
                    }
                    $register{$path}->{'status'} = $uistatus;
                } else {
                    my $esc_path = $path;
                    $esc_path =~ s/([ ])/\\$1/g;
                    if ($preserve) {
                        `$sshcmd $macip "/bin/mv $esc_path $esc_path.bak"`;
                    } else {
                        `$sshcmd $macip "/usr/bin/unlink $esc_path"`;
                    }
                    `$sshcmd $macip "/usr/bin/unlink $esc_path.meta"`;
                    delete $register{$path};
                }
                untie %nodereg;

            } else {
                if ($preserve) {
                    `/bin/mv "$path" "$path.bak"`;
                } else {
                    unlink $path;
                }
                if (substr($path,-5) eq '.vmdk') {
                    if ( -s (substr($path,0,-5) . "-flat.vmdk")) {
                        my $flat = substr($path,0,-5) . "-flat.vmdk";
                        if ($preserve) {
                            `/bin/mv $flat "$flat.bak"`;
                        } else {
                            unlink($flat);
                        }
                    } elsif ( -e (substr($path,0,-5) . "-s001.vmdk")) {
                        my $i = 1;
                        my $rmpath = substr($path,0,-5);
                        while (-e "$rmpath-s00$i.vmdk") {
                            if ($preserve) {
                                `/bin/mv "$rmpath-s00$i.vmdk" "$rmpath-s00$i.vmdk.bak"`;
                            } else {
                                unlink("$rmpath-s00$i.vmdk");
                            }
                            $i++;
                        }
                    }
                }
                unlink "$path.meta" if (-e "$path.meta");
                delete $register{$path};
            }

            my $subdir = "";
            my($bname, $dirpath) = fileparse($path);
            if ($dirpath =~ /.+\/$buser(\/.+)?\//) {
                $subdir = $1;
            }
            my $bpath = "$backupdir/$user$subdir/$bname";
            $bpath = $1 if ($bpath =~ /(.+)/);
            # Remove backup of image if it exists
            if (-d "$bpath") {
                `/bin/rm -rf "$bpath"`;
            }

#            $postmsg = "Deleted image $name ($path, $uuid, $mac)";
            $postreply =  "[]";
#            $postreply .=  "Status=deleting OK $postmsg\n";
            updateBilling("delete $path");
            $main::syslogit->($user, "info", "$uistatus $type image: $name: $path");
            if ($status eq 'downloading') {
                my $daemon = Proc::Daemon->new(
                    work_dir => '/usr/local/bin',
                    exec_command => qq|pkill -f "$path"|
                ) or do {$postreply .= "Status=ERROR $@\n";};
                my $pid = $daemon->Init();
            }
            sleep 1;
        }
    } else {
        $postmsg = "Cannot delete $type image with status: $status";
        $postreply .= "Status=ERROR $postmsg\n";
    }
    return $postreply;
}

# Clone image $path to destination storage pool $istoragepool, possibly changing backup schedule $bschedule
sub Clone {
    my ($path, $action, $obj, $istoragepool, $imac, $name, $bschedule, $buildsystem, $managementlink, $appid, $wait, $vcpu) = @_;
    if ($help) {
        return <<END
GET:image,name,storagepool,wait:
Clones an image. In the case of cloning a master image, a child is produced.
Only cloning to same storagepool is supported, with the exception of cloning to nodes (storagepool -1).
If you want to perform the clone synchronously, set wait to 1;
END
    }
    $postreply = "" if ($buildsystem);
    return "Status=Error no valid user\n" unless ($user);

    unless ($register{$path} && ($register{$path}->{'user'} eq $user
                || $register{$path}->{'user'} eq 'common'
                || $register{$path}->{'user'} eq $billto
                || $isadmin)) {
        $postreply .= "Status=ERROR Cannot clone!\n";
        return;
    }
    $istoragepool = $istoragepool || $obj->{storagepool};
    $name = $name || $obj->{name};
    $wait = $wait || $obj->{wait};
    my $status = $register{$path}->{'status'};
    my $type = $register{$path}->{'type'};
    my $master = $register{$path}->{'master'};
    my $notes = $register{$path}->{'notes'};
    my $image2 = $register{$path}->{'image2'};
    my $snap1 = $register{$path}->{'snap1'};
    $managementlink = $register{$path}->{'managementlink'} unless ($managementlink);
    $appid = $register{$path}->{'appid'} unless ($appid);
    my $upgradelink = $register{$path}->{'upgradelink'} || '';
    my $terminallink = $register{$path}->{'terminallink'} || '';
    my $version = $register{$path}->{'version'} || '';
    my $regmac = $register{$path}->{'mac'};

    my $virtualsize = $register{$path}->{'virtualsize'};
    my $dindex = 0;

    my($bname, $dirpath, $suffix) = fileparse($path, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));
    $path =~ /(.+)\.$type/;
    my $namepath = $1;
    if ($namepath =~ /(.+)\.master/) {
        $namepath = $1;
    }
    if ($namepath =~ /(.+)\.clone\d+/) {
        $namepath = $1;
    }
    if ($namepath =~ /.+\/common\/(.+)/) { # Support one subdir
        $namepath = $1;
    } elsif ($namepath =~ /.+\/$user\/(.+)/) { # Support one subdir
        $namepath = $1;
    } elsif ($namepath =~ /.+\/(.+)/) { # Extract only the name
        $namepath = $1;
    }

    # Find unique path in DB across storage pools
    my $upath;
    my $npath = "/mnt/stabile/node/$user/$namepath"; # Also check for uniqueness on nodes
    my $i = 1;
    foreach my $spool (@spools) {
        $upath = $spool->{'path'} . "/$user/$namepath";
        while ($register{"$upath.clone$i.$type"} || $register{"$npath.clone$i.$type"}) {$i++;};
    }

    $upath = "$spools[$istoragepool]->{'path'}/$user/$namepath";

    my $iname = $register{$path}->{'name'};
    $iname = "$name" if ($name); # Used when name supplied when building a system
    $iname =~ /(.+)( \(master\))/;
    $iname = $1 if $2;
    $iname =~ /(.+)( \(clone\d*\))/;
    $iname = $1 if $2;
    $iname =~ /(.+)( \(child\d*\))/;
    $iname = $1 if $2;
    my $ippath = $path;
    my $macip;
    my $ug = new Data::UUID;
    my $newuuid = $ug->create_str();
    my $wakenode;
    my $identity;

    # We only support cloning images to nodes - not the other way round
    if ($imac && $regmac && $imac ne $regmac) {
        $postreply .= "Status=ERROR Cloning from a node not supported\n";
        return $postreply;
    }

    if ($istoragepool==-1) {
    # Find the ip address of target node
        ($imac, $macip, $dindex, $wakenode, $identity) = locateNode($virtualsize, $imac, $vcpu);
        if ($identity eq 'local_kvm') {
            $postreply .= "Status=OK Cloning to local node with index $dindex\n";
            $istoragepool = 0; # cloning to local node
        } elsif (!$macip) {
            $postreply .= "Status=ERROR Unable to locate node with sufficient storage for image\n";
            $postmsg = "Unable to locate node for image!";
            $main::updateUI->({tab=>"images", user=>$user, type=>"message", message=>$postmsg});
            return $postreply;
        } else {
            $postreply .= "Status=OK Cloning to $macip with index $dindex\n";
            $ippath = "$macip:$path";
            $upath = "/mnt/stabile/node/$user/$namepath";
        }
    }
    my $ipath = "$upath.clone$i.$type";

    if ($bschedule eq 'daily7' || $bschedule eq 'daily14') {
         $bschedule = "manually" if ($istoragepool!=-1 && (!$spools[$istoragepool]->{'rdiffenabled'} || !$spools[$istoragepool]->{'lvm'}));
    } elsif ($bschedule ne 'manually') {
        $bschedule = '';
    }

# Find storage pool with space
    my $foundstorage = 1;
    if (overStorage($virtualsize, $istoragepool, $imac)) {
        $foundstorage = 0;
        foreach my $p (@spools) {
            if (overStorage($virtualsize, $p->{'id'}, $imac)) {
                ;
            } else {
                $istoragepool = $p->{'id'};
                $foundstorage = 1;
                last;
            }
        }
    }

# We allow multiple clone operations on master images
    if ($status ne "used" && $status ne "unused" && $status ne "paused" && $path !~ /(.+)\.master\.$type/) {
        $postreply .= "Status=ERROR Please shut down your virtual machine before cloning\n";

    } elsif ($type eq 'vmdk' && (-e "$dirpath$bname-s001$suffix" || -e "$dirpath$bname-flat$suffix")) {
        $postreply .= "Status=ERROR Cannot clone this image - please convert first!\n";

    } elsif (overQuotas($virtualsize, ($istoragepool==-1))) {
        $postreply .= "Status=ERROR Over quota (". overQuotas($virtualsize, ($istoragepool==-1)) . ") cloning: $name\n";

    } elsif (!$foundstorage) {
        $postreply .= "Status=ERROR Not enough storage ($virtualsize) in destination pool $istoragepool $imac cloning: $name\n";

    } elsif ($wakenode && !($path =~ /(.+)\.master\.$type/)) { # For now we dont support simply copying images on sleeping nodes
        $postreply .= "Status=ERROR We are waking up the node your image $name is on, please try again later\n";
        require "$Stabile::basedir/cgi/nodes.cgi";
        $Stabile::Nodes::console = 1;
        Stabile::Nodes::wake($imac);
    } elsif ($type eq "img" || $type eq "qcow2" || $type eq "vmdk") {
        my $masterimage2 = $register{"$path"}->{'image2'};
    # Cloning a master produces a child
        if ($type eq "qcow2" && $path =~ /(.+)\.master\.$type/) {
            $uistatus = "cloning";
    # VBoxManage probably does a more efficient job at cloning than simply copying
        } elsif ($type eq "vdi" || $type eq "vhd") {
            $uistatus = "vcloning";
    # Cloning another child produces a sibling with the same master
        } else {
            $uistatus = "copying";
        }
        $uipath = $path;
        eval {
            $register{$ipath} = {
                uuid=>$newuuid,
                master=>($uistatus eq 'cloning')?$path:$master,
                name=>"$iname (clone$i)",
                notes=>$notes,
                image2=>$image2,
                snap1=>($uistatus eq 'copying')?$snap1:'',
                storagepool=>$istoragepool,
                status=>$uistatus,
                mac=>($istoragepool == -1)?$imac:"",
                size=>0,
                realsize=>0,
                virtualsize=>$virtualsize,
                bschedule=>$bschedule,
                type=>"qcow2",
                created=>$current_time,
                user=>$user
            };
            $register{$ipath}->{'managementlink'} = $managementlink if ($managementlink);
            $register{$ipath}->{'appid'} = $appid if ($appid);
            $register{$ipath}->{'upgradelink'} = $upgradelink if ($upgradelink);
            $register{$ipath}->{'terminallink'} = $terminallink if ($terminallink);
            $register{$ipath}->{'version'} = $version if ($version);
            $register{$path}->{'status'} = $uistatus;
            my $dstatus = ($buildsystem)?'bcloning':$uistatus;
            if ($wakenode) { # We are waking a node for clone operation, so ask movepiston to do the work
                unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
                my $tasks = $nodereg{$imac}->{'tasks'};
                $upath = URI::Escape::uri_escape($ipath);
                $tasks .= "BCLONE $upath $user\n";
                $nodereg{$imac}->{'tasks'} = $tasks;
                tied(%nodereg)->commit;
                untie %nodereg;
            } elsif ($wait) {
                my $cmd = qq|steamExec $user $dstatus $status "$ippath" "$ipath"|;
                $cmd = $1 if ($cmd =~ /(.+)/);
                `$cmd`;
            } else {
                my $daemon = Proc::Daemon->new(
                        work_dir => '/usr/local/bin',
                        exec_command => "perl -U steamExec $user $dstatus $status \"$ippath\" \"$ipath\""
                    ) or do {$postreply .= "Status=ERROR $@\n";};
                my $pid = $daemon->Init();
            }
            $postreply .= "Status=$uistatus OK $uistatus to: $iname (clone$i)" . ($isadmin? " -> $ipath ":"") . "\n";
            $postreply .= "Status=OK uuid: $newuuid\n"; # if ($console || $api);
            $postreply .= "Status=OK path: $ipath\n"; # if ($console || $api);
            $postreply .= "Status=OK mac: $imac\n"; # if ($console || $api);
            $postreply .= "Status=OK wakenode: $wakenode\n"; # if ($console || $api);
            $main::syslogit->($user, "info", "$uistatus $wakenode $type image: $name $uuid to $ipath");
            1;
        } or do {$postreply .= "Status=ERROR $@\n";}

    } else {
        $postreply .= "Status=ERROR Not a valid type: $type\n";
    }
    tied(%register)->commit;
    $main::updateUI->({tab=>"images", user=>$user, type=>"update"});
    return $postreply;
}


# Link master image to fuel
sub Linkmaster {
    my ($mpath, $action) = @_;
    if ($help) {
        return <<END
GET:image:
Link master image to fuel
END
    }
    my $res;

    return "Your account does not have the necessary privileges\n" if ($isreadonly);
    return "Please specify master image to link\n" unless ($mpath);

    unless ($mpath =~ /^\//) { # We did not get an absolute path, look for it in users storagepools
        foreach my $p (@spools) {
            my $dir = $p->{'path'};
            my $cpath = "$dir/common/$mpath";
            my $upath = "$dir/$user/$mpath";
            if (-e $cpath) {
                $mpath = $cpath;
                last;
            } elsif (-e $upath) {
                $mpath = $upath;
                last;
            }
        }
    }
    my $img = $register{$mpath};
    $mpath = $img->{"path"};
    $imguser = $img->{"user"};
    if (!$mpath || ($imguser ne $user && $imguser ne 'common' && !$isadmin)) {
        $postreply = qq|{"status": "Error", "message": "No privs. or not found @_[0]"}|;
        return $postreply;
    }
    my $status = $img->{"status"};
    my $type = $img->{"type"};
    $mpath =~ /(.+)\/(.+)\.master\.$type$/;
    my $namepath = $2;
    my $msg;
    if ($status ne "unused" && $status ne "used") {
        $res .= qq|{"status": "Error", "message": "Only used and unused images may be linked ($status, $mpath)."}|;
    } elsif (!( $mpath =~ /(.+)\.master\.$type$/ ) ) {
        $res .= qq|{"status": "Error", "message": "You can only link master images"}|;
    } elsif ($type eq "qcow2") {
        my $pool = $img->{'storagepool'};
        `chmod 444 "$mpath"`;
        my $linkpath = $tenderpathslist[$pool] . "/$user/fuel/$namepath.link.master.$type";
        my $fuellinkpath = "/mnt/fuel/pool$pool/$namepath.link.master.$type";
        if (-e $tenderpathslist[$pool] . "/$user/fuel") { # master should be on fuel-enabled storage
            unlink ($linkpath) if (-e $linkpath);
            `ln "$mpath" "$linkpath"`;
        } else {
            foreach my $p (@spools) {
                my $dir = $p->{'path'};
                my $poolid = $p->{'id'};
                if (-e "$dir/$user/fuel") {
                    $linkpath = "$dir/$user/fuel/$namepath.copy.master.$type";
                    $fuellinkpath = "/mnt/fuel/pool$poolid/$namepath.copy.master.$type";
                    unlink ($linkpath) if (-e $linkpath);
                    `cp "$mpath" "$linkpath"`;
                    $msg = "Different file systems, master copied";
                    last;
                }
            }
        }
        $res .= qq|{"status": "OK", "message": "$msg", "path": "$fuellinkpath", "linkpath": "$linkpath", "masterpath": "$mpath"}|;
    } else {
        $res .= qq|{"status": "Error", "message": "You can only link qcow2 images"}|;
    }
    $postreply = $res;
    return $res;
}

# Link master image to fuel
sub unlinkMaster {
    my $mpath = shift;
    unless ($mpath =~ /^\//) { # We did not get an absolute path, look for it in users storagepools
        foreach my $p (@spools) {
            my $dir = $p->{'path'};
            my $upath = "$dir/$user/fuel/$mpath";
            if (-e $upath) {
                $mpath = "/mnt/fuel/pool$p->{id}/$mpath";
                last;
            }
        }
    }

    $mpath =~ /\/pool(\d+)\/(.+)\.link\.master\.qcow2$/;
    my $pool = $1;
    my $namepath = $2;
    if (!( $mpath =~ /\/pool(\d+)\/(.+)\.link\.master\.qcow2$/ ) ) {
        $postreply = qq|{"status": "Error", "message": "You can only unlink linked master images ($mpath)"}|;
    } else {
        my $linkpath = $tenderpathslist[$pool] . "/$user/fuel/$namepath.link.master.qcow2";
        if (-e $linkpath) {
            `chmod 644 "$linkpath"`;
            `rm "$linkpath"`;
            $postreply = qq|{"status": "OK", "message": "Link removed", "path": "/mnt/fuel/pool$pool/$namepath.qcow2", "linkpath": "$linkpath"}|;
        } else {
            $postreply = qq|{"status": "Error", "message": "Link $linkpath does not exists."}|;
        }
    }
}

#sub do_getstatus {
#    my ($img, $action) = @_;
#    if ($help) {
#        return <<END
#GET::
#END
#    }
#    # Allow passing only image name if we are dealing with an app master
#    my $dspool = $stackspool;
#    my $masteruser = $params{'masteruser'};
#    my $destuser = $params{'destuser'};
#    my $destpath;
#    $dspool = $spools[0]->{'path'} unless ($engineid eq $valve001id);
#    if (!$register{$img} && $img && !($img =~ /\//) && $masteruser) {
#        if ($img =~ /\.master\.qcow2$/ && $register{"$dspool/$masteruser/$img"}) {
#            if ($ismanager || $isadmin
#                || ($userreg{$masteruser}->{'billto'} eq $user)
#            ) {
#                $img = "$dspool/$masteruser/$img";
#            }
#        }
#    }
#    my $status = $register{$img}->{'status'};
#    if ($status) {
#        my $iuser = $register{$img}->{'user'};
#        # First check if user is allowed to access image
#        if ($iuser ne $user && $iuser ne 'common' && $userreg{$iuser}->{'billto'} ne $user) {
#            $status = '' unless ($isadmin || $ismanager);
#        }
#        if ($destuser) { # User is OK, now check if destination exists
#            my ($dest, $folder) = fileparse($img);
#            $destpath = "$dspool/$destuser/$dest";
#            $status = 'exists' if ($register{$destpath} || -e ($destpath));
#        }
#    }
#    my $res;
#    $res .= $Stabile::q->header('text/plain') unless ($console);
#    $res .= "$status";
#    return $res;
#}

# sub do_move {
#     my ($uuid, $action) = @_;
#     if ($help) {
#         return <<END
# GET:image,destuser,masteruser:
# Move image to a different storage pool or user
# END
#     }
#     return "Your account does not have the necessary privileges\n" if ($isreadonly);
#     Move($curimg, $params{'user'});
#     return $postreply;
# }

sub Move {
    my ($path, $iuser, $istoragepool, $mac, $force) = @_;
    # Allow passing only image name if we are deleting an app master
    my $dspool = $stackspool;
    my $masteruser = $params{'masteruser'};
    $dspool = $spools[0]->{'path'} unless ($engineid eq $valve001id);
    unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
    if (!$register{$path} && $path && !($path =~ /\//) && $masteruser) {
        if ($path =~ /\.master\.qcow2$/ && $register{"$dspool/$masteruser/$path"}) {
            if ($ismanager || $isadmin
                || ($userreg{$masteruser}->{'billto'} eq $user && $iuser eq $user)
                || ($masteruser eq $user && $userreg{$iuser}->{'billto'} eq $user)
            ) {
                $path = "$dspool/$masteruser/$path";
            }
        }
    }
    my $regimg = $register{$path};
    $istoragepool = ($istoragepool eq '0' || $istoragepool)? $istoragepool: $regimg->{'storagepool'};
    $mac = $mac || $regimg->{'mac'};
    my $bschedule = $regimg->{'bschedule'};
    my $name = $regimg->{'name'};
    my $status = $regimg->{'status'};
    my $type = $regimg->{'type'};
    my $reguser = $regimg->{'user'};
    my $regstoragepool = $regimg->{'storagepool'};
    my $virtualsize = $regimg->{'virtualsize'};

    my $newpath;
    my $newdirpath;
    my $oldpath = $path;
    my $newuser = $reguser;
    my $newstoragepool = $regstoragepool;
    my $haschildren;
    my $child;
    my $macip;
    my $alreadyexists;
    my $subdir;
#    $subdir = $1 if ($path =~ /\/$reguser(\/.+)\//);
    $subdir = $1 if ($path =~ /.+\/$reguser(\/.+)?\//);
    my $restpath;
    $restpath = $1 if ($path =~ /.+\/$reguser\/(.+)/);

    if ($type eq "qcow2" && $path =~ /(.+)\.master\.$type/) {
        my @regkeys = (tied %register)->select_where("master = '$path'");
        foreach my $k (@regkeys) {
            my $val = $register{$k};
            if ($val->{'master'} eq $path) {
                $haschildren = 1;
                $child = $val->{'name'};
                last;
            }
        }
    }
    if (!$register{$path}) {
        $postreply .= "Status=ERROR Unable to move $path (invalid path, $path, $masteruser)\n" unless ($istoragepool eq '--' || $regstoragepool eq '--');
    } elsif ($type eq 'vmdk' && -s (substr($path,0,-5) . "-flat.vmdk") || -s (substr($path,0,-5) . "-s001.vmdk")) {
        $postreply .= "Status=Error Cannot move this image. Please convert before moving\n";
# Moving an image to a different users dir
    } elsif ($iuser ne $reguser && ($status eq "unused" || $status eq "used")) {
        unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
        my @accounts = split(/,\s*/, $userreg{$tktuser}->{'accounts'});
        my @accountsprivs = split(/,\s*/, $userreg{$tktuser}->{'accountsprivileges'});
        %ahash = ($tktuser, $userreg{$tktuser}->{'privileges'} || 'r' ); # Include tktuser in accounts hash
        for my $i (0 .. scalar @accounts)
        {
            next unless $accounts[$i];
            $ahash{$accounts[$i]} = $accountsprivs[$i] || 'u';
        }

        if ((($isadmin || $ismanager ) && $iuser eq 'common') # Check if user is allowed to access account
                || ($isadmin && $userreg{$iuser})
                || ($user eq $engineuser)
                || ($userreg{$iuser}->{'billto'} eq $user)
                || ($ahash{$iuser} && !($ahash{$iuser} =~ /r/))
        ) {
            if ($haschildren) {
                $postreply .= "Status=Error Cannot move image. This image is used as master by: $child\n";
            } else {
                if ($regstoragepool == -1) { # The image is located on a node
                    my $uprivs = $userreg{$iuser}->{'privileges'};
                    if ($uprivs =~ /[an]/) {
                        unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
                        $macip = $nodereg{$mac}->{'ip'};
                        untie %nodereg;
                        $oldpath = "$macip:/mnt/stabile/node/$reguser/$restpath";
                        $newdirpath = "/mnt/stabile/node/$iuser/$restpath";
                        $newpath = "$macip:$newdirpath";
                        $newuser = $iuser;
                        $newstoragepool = $istoragepool;
                # Check if image already exists in target dir
                        $alreadyexists = `ssh -l irigo -i /var/www/.ssh/id_rsa_www -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no $macip "perl -e 'print 1 if -e q{/mnt/stabile/node/$iuser/$restpath}'"`;
                    } else {
                        $postreply .= "Status=Error Target account $iuser cannot use node storage\n";
                    }
                } else {
                    my $reguser = $userreg{$iuser};
                    my $upools = $reguser->{'storagepools'} || $Stabile::config->get('STORAGE_POOLS_DEFAULTS') || "0";
                    my @nspools = split(/, ?/, $upools);
                    my %ispools = map {$_=>1} @nspools; # Build a hash with destination users storagepools
                    if ($ispools{$regstoragepool}) { # Destination user has access to image's storagepool
                        $newpath = "$spools[$regstoragepool]->{'path'}/$iuser/$restpath";
                    } else {
                        $newpath = "$spools[0]->{'path'}/$iuser/$restpath";
                    }
                    $newdirpath = $newpath;
                    $newuser = $iuser;
            # Check if image already exists in target dir
                    $alreadyexists = -e $newpath;
                }
            }
        } else {
            $postreply .= "Status=Error Cannot move image to account $iuser $ahash{$iuser} - not allowed\n";
        }
# Moving an image to a different storage pool
    } elsif ($istoragepool ne '--' &&  $regstoragepool ne '--' && $istoragepool ne $regstoragepool
            && ($status eq "unused" || $status eq "used" || $status eq "paused")) {

        my $dindex;
        my $wakenode;
        if ($istoragepool == -1 && $regstoragepool != -1) {
            ($mac, $macip, $dindex, $wakenode) = locateNode($virtualsize, $mac);
        }

        $main::syslogit->($user, "info", "Moving $name from $regstoragepool to $istoragepool $macip $wakenode");

        if ($haschildren) {
            $postreply .= "Status=ERROR Unable to move $name (has children)\n";
        } elsif ($wakenode) {
            $postreply .= "Status=ERROR All available nodes are asleep moving $name, waking $mac, please try again later\n";
            require "$Stabile::basedir/cgi/nodes.cgi";
            $Stabile::Nodes::console = 1;
            Stabile::Nodes::wake($mac);
        } elsif (overStorage($virtualsize, $istoragepool+0, $mac)) {
            $postreply .= "Status=ERROR Out of storage in destination pool $istoragepool $mac moving: $name\n";
        } elsif (overQuotas($virtualsize, ($istoragepool==-1))) {
            $postreply .= "Status=ERROR Over quota (". overQuotas($virtualsize, ($istoragepool==-1)) . ") moving: $name\n";
        } elsif ($istoragepool == -1 && $regstoragepool != -1 && $path =~ /\.master\.$type/) {
            $postreply .= "Status=ERROR Unable to move $name (master images are not supported on node storage)\n";
    # Moving to node
        } elsif ($istoragepool == -1 && $regstoragepool != -1) {
            if (index($privileges,"a")!=-1 || index($privileges,"n")!=-1) { # Privilege "n" means user may use node storage
                if ($macip) {
                    $newdirpath = "/mnt/stabile/node/$reguser/$restpath";
                    $newpath = "$macip:$newdirpath";
                    $newstoragepool = $istoragepool;
            # Check if image already exists in target dir
                    $alreadyexists = `ssh -l irigo -i /var/www/.ssh/id_rsa_www -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no $macip "perl -e 'print 1 if -e q{/mnt/stabile/node/$reguser/$restpath}'"`;
                } else {
                    $postreply .= "Status=ERROR Unable to move $name (not enough space)\n";
                }
            } else {
                $postreply .= "Status=ERROR Unable to move $name (no node)\n";
            }
    # Moving from node
        } elsif ($regstoragepool == -1 && $istoragepool != -1 && $spools[$istoragepool]) {
            if (index($privileges,"a")!=-1 || index($privileges,"n")!=-1 && $mac) { # Privilege "n" means user may use node storage
                unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
                $macip = $nodereg{$mac}->{'ip'};
                untie %nodereg;
                $newpath = "$spools[$istoragepool]->{'path'}/$reguser/$restpath";
                $newdirpath = $newpath;
                $oldpath = "$macip:/mnt/stabile/node/$reguser/$restpath";
                $newstoragepool = $istoragepool;
        # Check if image already exists in target dir
                $alreadyexists = -e $newpath;
            } else {
                $postreply .= "Status=ERROR Unable to move $name - select node\n";
            }
        } elsif ($spools[$istoragepool]) { # User has access to storagepool
            $newpath = "$spools[$istoragepool]->{'path'}/$reguser/$restpath";
            $newdirpath = $newpath;
            $newstoragepool = $istoragepool;
            $alreadyexists = -e $newpath && -s $newpath;
        } else {
            $postreply .= "Status=ERROR Cannot move image. This image is used as master by: $child\n";
        }
    } else {
        $postreply .= "Status=ERROR Unable to move $path (bad status or pool $status, $reguser, $iuser, $regstoragepool, $istoragepool)\n" unless ($istoragepool eq '--' || $regstoragepool eq '--');
    }
    untie %userreg;

    if ($alreadyexists && !$force) {
        $postreply = "Status=ERROR Image \"$name\" already exists in destination\n";
        return $postreply;
    }
# Request actual move operation
    elsif ($newpath) {
        if ($newstoragepool == -1) {
            my $diruser = $iuser || $reguser;
            `ssh -l irigo -i /var/www/.ssh/id_rsa_www -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no $macip "/bin/mkdir -v /mnt/stabile/node/$diruser"`; # rsync will create the last dir if needed
        }
        if ($subdir && $istoragepool != -1) {
            my $fulldir = "$spools[$istoragepool]->{'path'}/$reguser$subdir";
            `/bin/mkdir -p "$fulldir"` unless -d $fulldir;
        }
        $uistatus = "moving";
        my $ug = new Data::UUID;
        my $tempuuid = $ug->create_str();

        $register{$path}->{'status'} = $uistatus;
        $register{$newdirpath} = \%{$register{$path}}; # Clone db entry

        if ($bschedule eq 'daily7' || $bschedule eq 'daily14') {
             $bschedule = "manually" if (!$spools[$regstoragepool]->{'rdiffenabled'} || !$spools[$regstoragepool]->{'lvm'});
        } elsif ($bschedule ne 'manually') {
            $bschedule = '';
        }

        $register{$path}->{'uuid'} = $tempuuid; # Use new temp uuid for old image
        $register{$newdirpath}->{'storagepool'} = $newstoragepool;
        if ($newstoragepool == -1) {
            $register{$newdirpath}->{'mac'} = $mac;
        } else {
            $register{$newdirpath}->{'mac'} = '';
        }
        $register{$newdirpath}->{'user'} = $newuser;
        tied(%register)->commit;
        if ($status eq "used" || $status eq "paused") {
            my $domuuid = $register{$path}->{'domains'};
            my $dom = $domreg{$domuuid};
            if ($dom->{'image'} eq $oldpath) {
                $dom->{'image'} = $newdirpath;
            } elsif ($dom->{'image2'} eq $oldpath) {
                $dom->{'image2'} = $newdirpath;
            } elsif ($dom->{'image3'} eq $oldpath) {
                $dom->{'image3'} = $newdirpath;
            } elsif ($dom->{'image4'} eq $oldpath) {
                $dom->{'image4'} = $newdirpath;
            }
            $dom->{'mac'} = $mac if ($newstoragepool == -1);
            if ($dom->{'system'} && $dom->{'system'} ne '--') {
                unless (tie(%sysreg,'Tie::DBI', Hash::Merge::merge({table=>'systems'}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access systems register"}|; return $res;};
                my $sys = $sysreg{$dom->{'system'}};
                $sys->{'image'} = $newdirpath;
                untie %sysreg;
            }
        }
        my $cmd = qq|/usr/local/bin/steamExec $user $uistatus $status "$oldpath" "$newpath"|;
        `$cmd`;
        $main::syslogit->($user, "info", "$uistatus $type image $name ($oldpath -> $newpath) ($regstoragepool -> $istoragepool) ($register{$newdirpath}->{uuid})");
        return "$newdirpath\n";
    } else {
        return $postreply;
    }

}

sub locateNode {
    my ($virtualsize, $mac, $vcpu) = @_;
    $vcpu = $vcpu || 1;
    unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac'}, $Stabile::dbopts)) ) {return 0};
    my $macip;
    my $dmac;
    my $dindex;
    my $asleep;
    my $identity;
    if ($mac && $mac ne "--") { # A node was specified
        if (1024 * $nodestorageovercommission * $nodereg{$mac}->{'storfree'} > $virtualsize && $nodereg{$mac}->{'status'} eq 'running') {
            $macip = $nodereg{$mac}->{'ip'};
            $dmac = $mac;
        }
    } else { # Locate a node

        require "$Stabile::basedir/cgi/servers.cgi";
        $Stabile::Servers::console = 1;
        my ($temp1, $temp2, $temp3, $temp4, $ahashref) = Stabile::Servers::locateTargetNode();
        my @avalues = values %$ahashref;
        my @sorted_values = (sort {$b->{'index'} <=> $a->{'index'}} @avalues);

        foreach $node (@sorted_values) {
            if (
                (1024 * $nodestorageovercommission * $node->{'storfree'} > $virtualsize)
                && ($node->{'cpuindex'} > $vcpu)
                && !($node->{'maintenance'})
                && ($node->{'status'} eq 'running' || $node->{'status'} eq 'asleep' || $node->{'status'} eq 'waking')
                && ($node->{'index'} > 0)
            #    && (!($node->{'identity'} =~ /^local/))
            ) {
                $macip = $node->{'ip'};
                $dmac = $node->{'mac'};
                $dindex = $node->{'index'};
                $asleep = ($node->{'status'} eq 'asleep' || $node->{'status'} eq 'waking');
                $identity = $node->{'identity'};
                last;
            }
        }
    }
    untie %nodereg;
    return ($dmac, $macip, $dindex, $asleep, $identity);
}

sub do_getimagestatus {
    my ($image, $action) = @_;
    if ($help) {
        return <<END
GET:image:
Check if image already exists. Pass image name including suffix.
END
    }
    my $res;
    $imagename = $params{'name'} || $image;
    foreach my $spool (@spools) {
        my $ipath = $spool->{'path'} . "/$user/$imagename";
        if ($register{$ipath}) {
            $res .= "Status=OK Image $ipath found with status $register{$ipath}->{'status'}\n";
        } elsif (-f "$ipath" && -s "$ipath") {
            $res .= "Status=OK Image $ipath found on disk, please wait for it to be updated in DB\n";
        }
    }
    $res .= "Status=ERROR Image $image not found\n" unless ($res);
    return $res;;
}

# Check if image already exists.
# Pass image name including suffix.
sub imageExists {
    my $imagename = shift;
    foreach my $spool (@spools) {
        my $ipath = $spool->{'path'} . "/$user/$imagename";
        if ($register{$ipath}) {
            return $register{$ipath}->{'status'} || 1;
        } elsif (-e "$ipath") {
            return 1
        }
    }
    return '';
}

# Pass image name including suffix.
# Returns incremented name of an image which does not already exist.
sub getValidName {
    my $imagename = shift;
    my $name = $imagename;
    my $type;
    if ($imagename =~ /(.+)\.(.+)/) {
        $name = $1;
        $type = $2;
    }
    if (imageExists($imagename)) {
        my $i = 1;
        while (imageExists("$name.$i.$type")) {$i++;};
        $imagename = "$name.$i.$type";
    }
    return $imagename;
}

# Print list of available actions on objects
sub do_plainhelp {
    my $res;
    $res .= header('text/plain') unless $console;
    $res .= <<END
* new [size="size", name="name"]: Creates a new image
* clone: Creates new clone of an image. A clone of a master image is a child of the master. A clone of a child or regular
image is a regular copy.
* convert: Creates a copy of a non-qcow2 image in qcow2 format
* snapshot: Takes a qcow2 snapshot of the image. Server can not be running.
* unsnap: Removes a qcow2 snapshot.
* revert: Applies a snapshot, reverting the image to the state it was in, when the snapshot was taken.
* master: Turns an image into a master image which child images may be cloned from. Image can not be in use.
* unmaster: Turns a master image into a regular image, which can not be used to clone child images from.
* backup: Backs up an image using rdiff-backup. Rdiff-backup must be enabled in admin server configuration. This is a
very expensive operation, since typically the entire image must be read.
* buildsystem [master="master image"]: Constructs one or optionally multiple servers, images and networks and assembles
them in one app.
* restore [backup="backup"]: Restores an image from a backup. The restore is named after the backup.
* delete: Deletes an image. Use with care. Image can not be in use.
* mount: Mounts an image for restorefiles and listfiles operations.
* unmount: Unmounts an image
END
    ;
    return $res;
}

# Print list of images
# Showing a single image is also handled by specifying uuid or path in $curuuid or $curimg
# When showing a single image a single action may be performed on image
sub do_list {
    my ($img, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image,uuid:
Lists all the images a user has access to. This is also the default action for the endpoint, so if no action is specified this is what you get.
The returned list may be filtered by specifying storagepool, type, name, path or uuid, like e.g.:

<a href="/stabile/images/type:user" target="_blank">/stabile/images/type:user</a>
<a href="/stabile/images/name:test* AND storagepool:shared" target="_blank">/stabile/images/name:test* AND storagepool:shared</a>
<a href="/stabile/images/storagepool:shared AND path:test*" target="_blank">/stabile/images/storagepool:shared AND path:test*</a>
<a href="/stabile/images/name:* AND storagepool:all AND type:usercdroms" target="_blank">/stabile/images/name:* AND storagepool:all AND type:usercdroms</a>
<a href="/stabile/images/[uuid]" target="_blank">/stabile/images/[uuid]</a>

storagepool may be either of: all, node, shared
type may be either of: user, usermasters, commonmasters, usercdroms

May also be called as tablelist or tablelistall, for use by stash.

END
    }
    my $res;
    my $filter;
    my $storagepoolfilter;
    my $typefilter;
    my $pathfilter;
    my $uuidfilter;
    $curimg = $img if ($img);
    if ($curimg && ($isadmin || $register{$curimg}->{'user'} eq $user || $register{$curimg}->{'user'} eq 'common') ) {
        $pathfilter = $curimg;
    } elsif ($uripath =~ /images(\.cgi)?\/(\?|)(name|storagepool|type|path)/) {
        $filter = $3 if ($uripath =~ /images(\.cgi)?\/.*name(:|=)(.+)/);
        $filter = $1 if ($filter =~ /(.*) AND storagepool/);
        $filter = $1 if ($filter =~ /(.*) AND type/);
        $filter = $1 if ($filter =~ /(.*)\*$/);
        $storagepoolfilter = $2 if ($uripath =~ /images(\.cgi)?\/.*storagepool:(\w+)/);
        $typefilter = $2 if ($uripath =~ /images(\.cgi)?\/.*type:(\w+)/);
        $typefilter = $2 if ($uripath =~ /images(\.cgi)?\/.*type=(\w+)/);
        $pathfilter = $2 if ($uripath =~ /images(\.cgi)?\/.*path:(.+)/);
        $pathfilter = $2 if ($uripath =~ /images(\.cgi)?\/.*path=(.+)/);
    } elsif ($uripath =~ /images(\.cgi)?\/(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})\/?(\w*)/) {
        $uuidfilter = $2;
        $curaction = lc $3;
    }
    $uuidfilter = $options{u} unless $uuidfilter;

    if ($uuidfilter && $curaction) {
        if ($imagereg{$uuidfilter}) {
            $curuuid = $uuidfilter;
            my $obj = getObj(%params);
            # Now perform the requested action
            my $objfunc = "obj_$curaction";
            if (defined &$objfunc) { # If a function named objfunc exists, call it
                $res = $objfunc->($obj);
                chomp $postreply;
                unless ($res) {
                    $res .= qq|{"status": "OK", "message": "$postreply"}|;
                    $res = join(", ", split("\n", $res));
                }
                unless ($curaction eq 'download') {
                    $res = header('application/json; charset=UTF8') . $res unless ($console);
                }
            } else {
                $res .= header('application/json') unless $console;
                $res .= qq|{"status": "Error", "message": "Unknown image action: $curaction"}|;
            }
        } else {
            $res .= header('application/json') unless $console;
            $res .= qq|{"status": "Error", "message": "Unknown image $uuidfilter"}|;
        }
        return $res;
    }


    my %userregister; # User specific register

    $res .= header('application/json; charset=UTF8') unless $console;
    unless (tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>1}, $Stabile::dbopts)) ) {$res .= qq|{"status": "Error": "message": "Unable to access user register"}|; return $res;};

    my @busers = @users;
    my @billusers = (tied %userreg)->select_where("billto = '$user'");
    push (@busers, $billto) if ($billto && $billto ne '--'); # We include images from 'parent' user
    push (@busers, @billusers) if (@billusers); # We include images from 'child' users
    untie %userreg;
    unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
    foreach my $u (@busers) {
        my @regkeys = (tied %register)->select_where("user = '$u'");
        foreach my $k (@regkeys) {
            my $valref = $register{$k};
            # Only update info for images the user has access to.
            if ($valref->{'user'} eq $u && (defined $spools[$valref->{'storagepool'}]->{'id'} || $valref->{'storagepool'}==-1)) {
                # Only list installable master images from billto account
                next if ($billto && $u eq $billto && ($valref->{'type'} ne 'qcow2' || $valref->{'installable'} ne 'true'));
                my $path = $valref->{'path'};
                my %val = %{$valref}; # Deference and assign to new array, effectively cloning object
                my $spool = $spools[$val{'storagepool'}];
                # Skip images which are in DB e.g. because of change of storage pool difinitions
                next unless ($val{'storagepool'}==-1 || $val{'path'} =~ /$spool->{'path'}/);
                $val{'virtualsize'} += 0;
                $val{'realsize'} += 0;
                $val{'size'} += 0;
                #$val{'lvm'} = 0+( (($spools[$val{'storagepool'}]->{"hostpath"} eq "local") && $spools[$val{'storagepool'}]->{"rdiffenabled"}) || $val{'storagepool'}==-1);
                if ($val{'storagepool'}==-1) {
                    my $node = $nodereg{$val{'mac'}};
                    $val{'lvm'} = 0+($node->{stor} eq 'lvm');
                } else {
                    $val{'lvm'} = 0+$spool->{"lvm"};
                }
                # If image has a master, update the master with child info.
                # This info is specific to each user, so we don't store it in the db
                if ($valref->{'master'} && $register{$valref->{'master'}} && ((grep $_ eq $valref->{'user'}, @users))) {
                    $register{$valref->{'master'}}->{'status'} = 'used';
                    unless ($userregister{$val{'master'}}) { # If we have not yet parsed master, it is not yet in userregister, so put it there
                        my %mval = %{$register{$val{'master'}}};
                        $userregister{$val{'master'}} = \%mval;
                    }
                    #   $userregister{$val{'master'}}->{'user'} = $u;
                    $userregister{$val{'master'}}->{'status'} = 'used';
                    if ($val{'domains'}) {
                        $userregister{$val{'master'}}->{'domainnames'} .= ", " if ($userregister{$val{'master'}}->{'domainnames'});
                        $userregister{$val{'master'}}->{'domainnames'} .= $val{'domainnames'};
                        $userregister{$val{'master'}}->{'domainnames'} .= " (".$val{'user'}.")" if (index($privileges,"a")!=-1);

                        $userregister{$val{'master'}}->{'domains'} .= ", " if ($userregister{$val{'master'}}->{'domains'});
                        $userregister{$val{'master'}}->{'domains'} .= $val{'domains'};
                    }
                }
                my $status = $valref->{'status'};
                if ($rdiffenabled && ($userrdiffenabled || index($privileges,"a")!=-1) &&
                    ( ($spools[$valref->{'storagepool'}]->{'rdiffenabled'} &&
                        ($spools[$valref->{'storagepool'}]->{'lvm'} || $status eq 'unused' || $status eq 'used' || $status eq 'paused') )
                        || $valref->{'storagepool'}==-1 )
                ) {
                    $val{'backup'} = "" ;
                } else {
                    $val{'backup'} = "disabled" ;
                }
                $val{'status'} = 'backingup' if ($status =~ /backingup/);
                $userregister{$path} = \%val unless ($userregister{$path});
            }
        }
    }
    untie(%nodereg);

    my @uservalues;
    if ($filter || $storagepoolfilter || $typefilter || $pathfilter || $uuidfilter) { # List filtered images
        foreach $uvalref (values %userregister) {
            my $fmatch;
            my $smatch;
            my $tmatch;
            my $pmatch;
            my $umatch;
            $fmatch = 1 if (!$filter || $uvalref->{'name'}=~/$filter/i);
            $smatch = 1 if (!$storagepoolfilter || $storagepoolfilter eq 'all'
                || ($storagepoolfilter eq 'node' && $uvalref->{'storagepool'}==-1)
                || ($storagepoolfilter eq 'shared' && $uvalref->{'storagepool'}>=0)
            );
            $tmatch = 1 if (!$typefilter || $typefilter eq 'all'
                || ($typefilter eq 'user' && $uvalref->{'user'} eq $user
                # && $uvalref->{'type'} ne 'iso'
                # && $uvalref->{'path'} !~ /\.master\.qcow2$/
                    )
                || ($typefilter eq 'usermasters' && $uvalref->{'user'} eq $user && $uvalref->{'path'} =~ /\.master\.qcow2$/)
                || ($typefilter eq 'usercdroms' && $uvalref->{'user'} eq $user && $uvalref->{'type'} eq 'iso')
                || ($typefilter eq 'commonmasters' && $uvalref->{'user'} ne $user && $uvalref->{'path'} =~ /\.master\.qcow2$/)
                || ($typefilter eq 'commoncdroms' && $uvalref->{'user'} ne $user && $uvalref->{'type'} eq 'iso')
            );
            $pmatch = 1 if ($pathfilter && $uvalref->{'path'}=~/$pathfilter/i);
            $umatch = 1 if ($uvalref->{'uuid'} eq $uuidfilter);
            if ((!$pathfilter &&!$uuidfilter && $fmatch && $smatch && $tmatch) || $pmatch) {
                push @uservalues,$uvalref if ($uvalref->{'uuid'});
            } elsif ($umatch && $uvalref->{'uuid'}) {
                push @uservalues,$uvalref;
                last;
            }
        }
    } else {
        @uservalues = values %userregister;
    }

    # Sort @uservalues
    my $sort = 'status';
    $sort = $2 if ($uripath =~ /sort\((\+|\-)(\S+)\)/);
    my $reverse;
    $reverse = 1 if ($1 eq '-');
    if ($reverse) { # sort reverse
        if ($sort =~ /realsize|virtualsize|size/) {
            @uservalues = (sort {$b->{$sort} <=> $a->{$sort}} @uservalues); # Sort as number
        } else {
            @uservalues = (sort {$b->{$sort} cmp $a->{$sort}} @uservalues); # Sort as string
        }
    } else {
        if ($sort =~ /realsize|virtualsize|size/) {
            @uservalues = (sort {$a->{$sort} <=> $b->{$sort}} @uservalues); # Sort as number
        } else {
            @uservalues = (sort {$a->{$sort} cmp $b->{$sort}} @uservalues); # Sort as string
        }
    }

    if ($uuidfilter || $curimg) {
        if (scalar @uservalues > 1) { # prioritize user's own images
            foreach my $val (@uservalues) {
                if ($val->{'user'} eq 'common') {
                    next;
                } else {
                    $json_text = to_json($val, {pretty => 1});
                }
            }
        } else {
            $json_text = to_json($uservalues[0], {pretty => 1}) if (@uservalues);
        }
    } else {
        $json_text = to_json(\@uservalues, {pretty => 1}) if (@uservalues);
    }
    $json_text = "{}" unless $json_text;
    $json_text =~ s/""/"--"/g;
    $json_text =~ s/null/"--"/g;
    $json_text =~ s/"notes" {0,1}: {0,1}"--"/"notes":""/g;
    $json_text =~ s/"installable" {0,1}: {0,1}"(true|false)"/"installable":$1/g;

    if ($action eq 'tablelist' || $action eq 'tablelistall') {
        my $t2 = Text::SimpleTable->new(36,26,5,20,14,10,7);
        $t2->row('uuid', 'name', 'type', 'domainnames', 'virtualsize', 'user', 'status');
        $t2->hr;
        my $pattern = $options{m};
        foreach $rowref (@uservalues){
            next unless ($action eq 'tablelistall' || $rowref->{'user'} eq $user);
            if ($pattern) {
                my $rowtext = $rowref->{'uuid'} . " " . $rowref->{'name'} . " " . $rowref->{'type'} . " " . $rowref->{'domainnames'}
                    . " " .  $rowref->{'virtualsize'} . " " . $rowref->{'user'} . " " . $rowref->{'status'};
                $rowtext .= " " . $rowref->{'mac'} if ($isadmin);
                next unless ($rowtext =~ /$pattern/i);
            }
            $t2->row($rowref->{'uuid'}, $rowref->{'name'}, $rowref->{'type'}, $rowref->{'domainnames'}||'--',
                $rowref->{'virtualsize'}, $rowref->{'user'}, $rowref->{'status'});
        }
        $res .= $t2->draw;
    } elsif ($console) {
        $res .= Dumper(\@uservalues);
    } else {
        $res .= $json_text;
    }
    return $res;
}

# Internal action for looking up a uuid or part of a uuid and returning the complete uuid
sub do_uuidlookup {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET:image,path:
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
                && ($register{$uuid}->{'uuid'} =~ /^$u/ || $register{$uuid}->{'name'} =~ /^$u/)) {
                $ruuid = $register{$uuid}->{'uuid'};
                last;
            }
        }
        if (!$ruuid && $isadmin) { # If no match and user is admin, do comprehensive lookup
            foreach $uuid (keys %register) {
                if ($register{$uuid}->{'uuid'} =~ /^$u/ || $register{$uuid}->{'name'} =~ /^$u/) {
                    $ruuid = $register{$uuid}->{'uuid'};
                    last;
                }
            }
        }
    }
    $res .= "$ruuid\n" if ($ruuid);
    return $res;
}

# Internal action for showing a single image
sub do_uuidshow {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET:image,path:
END
    }
    my $res;
    $res .= header('text/plain') unless $console;
    my $u = $options{u};
    $u = $curuuid unless ($u || $u eq '0');
    if ($u || $u eq '0') {
        foreach my $uuid (keys %register) {
            if (($register{$uuid}->{'user'} eq $user || $register{$uuid}->{'user'} eq 'common' || index($privileges,"a")!=-1)
                && $register{$uuid}->{'uuid'} =~ /^$u/) {
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

sub do_updatebilling {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET:image,path:
END
    }
    my $res;
    $res .= header('text/plain') unless ($console);
    updateBilling($params{"event"});
    $res .= "Status=OK Updated billing for $user\n";
    return $res;
}

# If used with the -f switch ($fulllist) from console, all users images are updated in the db
# If used with the -p switch ($fullupdate), also updates status information (ressource intensive - runs through all domains)
sub dont_updateregister {
    my ($img, $action) = @_;
    my $res;
    if ($help) {
        return <<END
GET:image,path:
END
    }
    return "Status=ERROR You must be an admin to do this!\n" unless ($isadmin);
    $fullupdate = 1 if ((!$fullupdate && $params{'fullupdate'}) || $action eq 'fullupdateregister');
    my $force = $params{'force'};
    Updateregister($force);
    $res .= "Status=OK Updated image register for " . join(', ', @users) . "\n";
}

sub do_urlupload {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET:image,path:
END
    }
    my $res;
    $res .= header('application/json') unless ($console);
    if ($params{'probe'} && $params{'url'}) {
        my $url = $params{'url'};
        my $cmd = qq!curl -kIL "$url" 2>&1!;
        my $headers = `$cmd`;
        my $filename;
        my $filesize = 0;
        $filename = $1 if ($headers =~ /content-disposition: .+filename="(.+)"/i);
        $filesize = $1 if ($headers =~ /content-length: (\d+)/i);
        my $ok;
        if (!$filename) {
            my $cmd = qq[curl -kIL "$url" 2>&1 | grep -i " 200 OK"];
            $ok =  `$cmd`; chomp $ok;
            $filename = `basename "$url"` if ($ok);
            chomp $filename;
        }
        if ($filename =~ /\S+\.(vmdk|img|vhd|qcow|qcow2|vdi|iso)$/) {
            $filename = $2 if ($filename =~ /(=|\?)(.+)/);
            $filename = $2 if ($filename =~ /(=|\?)(.+)/);
            $filename = getValidName($filename);
            my $filepath = $spools[0]->{'path'} . "/$user/$filename";
            $res .= qq|{"status": "OK", "name": "$filename", "message": "200 OK", "size": $filesize, "path": "$filepath"}|;
        } else {
            $res .= qq|{"status": "ERROR", "message": "An image file cannot be downloaded from this URL.", "url": "$url"}|;
        }
    } elsif ($params{'path'} && $params{'url'} && $params{'name'} && defined $params{'size'}) {
        my $imagepath = $params{'path'};
        my $imagename = $params{'name'};
        my $imagesize = $params{'size'};
        my $imageurl = $params{'url'};
        if (-e $imagepath) {
            $res .= qq|{"status": "ERROR", "message": "An image file with this name already exists on the server.", "name": "$imagename"}|;
        } elsif ($imagepath !~ /^$spools[0]->{'path'}\/$user\/.+/) {
            $res .= qq|{"status": "ERROR", "message": "Invalid path"}|;
        } elsif (overQuotas($virtualsize)) {
            $res .= qq|{"status": "ERROR", "message": "Over quota (". overQuotas($virtualsize) . ") uploading: $imagename"}|;
        } elsif (overStorage($imagesize, 0)) {
            $res .= qq|{"status": "ERROR", "message": "Out of storage in destination pool uploading: $imagename"}|;
        } elsif ($imagepath =~ /^$spools[0]->{'path'}.+\.(vmdk|img|vhd|qcow|qcow2|vdi|iso)$/) {
            my $imagetype = $1;
            my $ug = new Data::UUID;
            my $newuuid = $ug->create_str();
            my $name = $imagename;
            $name = $1 if ($name =~ /(.+)\.(vmdk|img|vhd|qcow|qcow2|vdi|iso)$/);
            $register{$imagepath} = {
                uuid => $newuuid,
                path => $imagepath,
                name => $name,
                user => $user,
                type => $imagetype,
                virtualsize => $imagesize,
                realsize => $imagesize,
                size => $imagesize,
                storagepool => 0,
                status => 'uploading'
            };
            `/bin/echo uploading > "$imagepath.meta"`;
            eval {
                my $daemon = Proc::Daemon->new(
                    work_dir => '/usr/local/bin',
                    exec_command => "perl -U steamExec $user urluploading unused \"$imagepath\" \"$imageurl\""
                ) or do {$postreply .= "Status=ERROR $@\n";};
                my $pid = $daemon->Init();
                $main::syslogit->($user, "info", "urlupload $imageurl, $imagepath");
                1;
            } or do {$res .= qq|{"status": "ERROR", "message": "ERROR $@"}|;};

            $res .= qq|{"status": "OK", "name": "$imagename", "message": "Now uploading", "path": "$imagepath"}|;
        }
    } elsif ($params{'path'} && $params{'getsize'}) {
        my $imagepath = $params{'path'};
        if (!(-e $imagepath)) {
            $res .= qq|{"status": "ERROR", "message": "Image not found.", "path": "$imagepath"}|;
        } elsif ($imagepath !~ /^$spools[0]->{'path'}\/$user\/.+/) {
            $res .= qq|{"status": "ERROR", "message": "Invalid path"}|;
        } else {
            my @stat = stat($imagepath);
            my $imagesize = $stat[7];
            $res .= qq|{"status": "OK", "size": $imagesize, "path": "imagepath"}|;
        }
    }
    return $res;
}

sub do_upload {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
POST:image,path:
END
    }
    my $res;
    $res .= header("text/html") unless ($console);

    my $uname = $params{'name'};

    my($name, $dirpath, $suffix) = fileparse($uname, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));

    $name = $1 if ($name =~ /^\.+(.*)/); # Don't allow hidden files
    #        my $f = lc $name;
    my $f = $name;
    $f = $spools[0]->{'path'} . "/$user/$f$suffix";

    my $chunk = int($params{'chunk'});
    my $chunks = int($params{'chunks'});

    if ($chunk == 0 && -e $f) {
        $res .= qq|Error: File already exists $name|;
    } else {
        open (FILE, ">>$f");

        if ($params{'file'}) {
            my $uh = $Stabile::q->upload("file");
            while ( <$uh> ) {
                print FILE;
            }
            close FILE;

            if ($chunk == 0) {
                `/usr/local/bin/steamExec updateimagestatus "$f" uploading`;
            }
            if ($chunk >= ($chunks - 1) ) { # Done
                unlink("$f.meta");
                `/usr/local/bin/steamExec updateimagestatus "$f" unused`;
            } else {
                my $upload_meta_data = "status=uploading&chunk=$chunk&chunks=$chunks";
                `echo "$upload_meta_data" > "$f.meta"`;
            }
            $res .= qq|OK: Chunk $chunk uploaded of $name|;
        } else {
            $res .= qq|OK: No file $name.|;
        }
    }
    return $res;
}

# .htaccess files are created hourly, giving the image user access
# when download is clicked by another user (in @users, so with permission), this user is also given access until .htaccess is rewritten
sub Download {
    my ($f, $action, $argref) = @_;
    #    my ($name, $managementlink, $upgradelink, $terminallink, $version) = @{$argref};
    if ($help) {
        return <<END
GET:image:
Returns http redirection with URL to download image
END
    }
    my %uargs = %{$argref};
    $f = $uargs{'image'} unless ($f);
    $baseurl = $uargs{'baseurl'} || $baseurl;
    my $res;
    my $uf =  URI::Escape::uri_unescape($f);
    if (! $f) {
        $res .= header('text/html', '500 Internal Server Error') unless ($console);
        $res .= "Status=ERROR You must specify an image.\n";
    }
    my $txt = <<EOT
order deny,allow
AuthName "Download"
AuthType None
TKTAuthLoginURL $baseurl/login/
TKTAuthIgnoreIP on
deny from all
Satisfy any
require user $user
require user $tktuser
Options -Indexes
EOT
    ;
    my $fid;
    my $fpath;
    foreach my $p (@spools) {
        foreach my $suser (@users) {
            my $dir = $p->{'path'};
            my $id = $p->{'id'};
            if (-d "$dir/$suser" && $uf =~ /\/$suser\//) {
                if ($uf =~ /$dir\/(.+)\/(.+)/) {
                    my $filename = $2;
                    utf8::encode($filename);
                    utf8::decode($filename);
                    $fpath = "$1/" . URI::Escape::uri_escape($filename);
                    #$fpath = "$1/" . $filename;
                    `chmod o+rw "$uf"`;
                    `/bin/echo "$txt" > "$dir/$suser/.htaccess"`;
                    `chmod 644 "$dir/$suser/.htaccess"`;
                    `/bin/mkdir "$Stabile::basedir/download"` unless (-e "$Stabile::basedir/download");
                    `/bin/ln -s "$dir" "$Stabile::basedir/download/$id"` unless (-e "$Stabile::basedir/download/$id");
                    $fid = $id;
                    last;
                }
            }
        }
    }
    if (($fid || $fid eq '0') && $fpath && -e "$f") {
        my $fileurl = "$baseurl/download/$fid/$fpath";
        if ($console) {
            $res .= "$fileurl\n";
        } else {
            $res .= "Status: 302 Moved\nLocation: $fileurl\n\n";
            $res .= "$fileurl\n";
        }
    } else {
        $res .= header('text/html', '500 Internal Server Error') unless ($console);
        $res .= "Status=ERROR File not found $f, $fid, $fpath, $uargs{image}\n";
    }
    return $res;
}


sub Liststoragedevices {
    my ($image, $action) = @_;
    if ($help) {
        return <<END
GET::
Returns available physical disks and partitions.
Partitions currently used for holding backup and primary images directories are marked as such.
May also be called as 'getimagesdevice', 'getbackupdevice', 'listimagesdevices' or 'listbackupdevices'.
END
    }
    unless ($isadmin || ($user eq $engineuser)) {
        return '' if ($action eq 'getimagesdevice' || $action eq 'getbackupdevice');
        return qq|[]|;
    }
    my %devs;
    # Check if we have unmounted ZFS file systems
#    if (`grep "stabile-images" /etc/stabile/config.cfg` && !(`df` =~ /stabile-images/)) {
    if (!(`df` =~ /stabile-images/)) {
        `zpool import stabile-images`;
        `zfs mount stabile-images`;
        `zfs mount stabile-images/images`;
    }
    if (!(`df` =~ /stabile-backup/)) {
        `zpool import stabile-backup`;
        `zfs mount stabile-backup`;
        `zfs mount stabile-backup/images`;
        `zfs mount stabile-backup/backup`;
    }
    # Add active and mounted filesystems
    my %filesystems;
    $cmd = q/LANG=en df -hT | tr -s ' ' ',' | jq -nR '[( input | split(",") ) as $keys | ( inputs | split(",") ) as $vals | [ [$keys, $vals] | transpose[] | {key:.[0],value:.[1]} ] | from_entries ]'/;
    my $json = `$cmd`;
    my $jobj = JSON::from_json($json);
    my $rootdev;
    my $backupdev;
    my $imagesdev;
    foreach my $fs (sort {$a->{'Filesystem'} cmp $b->{'Filesystem'}} @{$jobj}) {
        # Note that physical disk devicess in general may be either disks, partitions with regular file systems (like ext4) or zfs pools, which may contain many file systems
        if ($fs->{Filesystem} =~ /\/dev\/(.+)/) {
            my $name = $1;
            if ($name =~ /mapper\/(\w+-)(.+)/) {
                $name = "$1$2";
            }
            $fs->{Name} = $name;
            delete $fs->{on};
            my $mp = $fs->{Mounted};
            if ($fs->{Mounted} eq '/') {
                $rootdev = $name;
            } else {
                if ($backupdir =~ /^$fs->{Mounted}/) {
                    next if ($action eq 'listimagesdevices'); # Current backup dev is not available as images dev
                    $fs->{isbackupdev} = 1;
                    $backupdev = $name;
                    return $name if ($action eq 'getbackupdevice');
                }
                if ($tenderpathslist[0] =~ /^$fs->{Mounted}/) {
                    next if ($action eq 'listbackupdevices'); # Current images dev is not available as backup dev
                    $fs->{isimagesdev} = 1;
                    $imagesdev = $name;
                    return $name if ($action eq 'getimagesdevice');
                }
            }
            $fs->{dev} = $name;
            $fs->{nametype} = "$name ($fs->{Type} - " .  ($mp?$mp:"not mounted") . " $fs->{Size})";
            $filesystems{$name} = $fs;
        } elsif ( $fs->{Type} eq 'zfs') {
            my $name = $fs->{Filesystem};
            if ($name =~ /(.+)\/(.+)/) { # only include zfs pools but look for use as backup and images
                if ($fs->{Mounted} eq $backupdir) {
                    if ($action eq 'listimagesdevices') {
                        delete $filesystems{$1}; # not available for images - used for backup
                    } else {
                        $filesystems{$1}->{isbackupdev} = 1;
                        $backupdev = $name;
                    }
                    return $filesystems{$1}->{Name} if ($action eq 'getbackupdevice');
                }
                if ($fs->{Mounted} eq $tenderpathslist[0]) {
                    if ($action eq 'listbackupdevices') {
                        delete $filesystems{$1}; # not available for backup - used for images
                    } else {
                        $filesystems{$1}->{isimagesdev} = 1;
                        $imagesdev = $name;
                    }
                    return $filesystems{$1}->{Name} if ($action eq 'getimagesdevice');
                }
                next;
            }
            $fs->{Name} = $name;
            $fs->{nametype} = "$name ($fs->{Type} $fs->{Size})";
            delete $fs->{on};
            $filesystems{$name} = $fs;
        }
    }
    if ($action eq 'getbackupdevice' || $action eq 'getimagesdevice') {
        return $rootdev;
    }
    $filesystems{$rootdev}->{isbackupdev} = 1 unless ($backupdev);
    $filesystems{$rootdev}->{isimagesdev} = 1 unless ($imagesdev);
    # Lowercase keys
    foreach my $k (keys %filesystems) {
        my %hash = %{$filesystems{$k}};
        %hash = map { lc $_ => $hash{$_} } keys %hash;
        $filesystems{$k} = \%hash;
    }
    # Identify physical devices used for zfs
    $cmd = "zpool list -vH";
    my $zpools = `$cmd`;
    my $zdev;
    my %zdevs;

    # Now parse the rather strange output with every other line representing physical dev
    foreach my $line (split "\n", $zpools) {
        my ($zname, $zsize, $zalloc) = split "\t", $line;
        if (!$zdev) {
            if ($zname =~ /stabile-/) {
                $zdev = {
                    name=>$zname,
                    size=>$zsize,
                    alloc=>$zalloc
                }
            }
        } else {
            my $dev = $zsize;
            $zdev->{dev} = $dev;
            if ( $filesystems{$zdev->{name}}) {
                if (
                    ($action eq 'listimagesdevices' && $zdev->{name} =~ /backup/) ||
                        ($action eq 'listbackupdevices' && $zdev->{name} =~ /images/)
                ) {
                    delete $filesystems{$zdev->{name}}; # Don't include backup devs in images listing and vice-versa
                } else {
                    if ($filesystems{$zdev->{name}}->{dev}) {
                        $filesystems{$zdev->{name}}->{dev} .= " $dev";
                    } else {
                        $filesystems{$zdev->{name}}->{dev} = $dev;
                    }
        #            $filesystems{$zdev->{name}}->{nametype} =~ s/zfs/zfs pool/;
                }
            }
            $zdevs{$dev} = $zdev->{name};
        #    $zdev = '';
        }
    }

    # Add blockdevices
    $cmd = q|lsblk --json|;
    my $json2 = `$cmd`;
    my $jobj2 = JSON::from_json($json2);
    foreach my $fs (@{$jobj2->{blockdevices}}) {
        my $rootdev = $1 if ($fs->{name} =~ /([A-Za-z]+)\d*/);
        if ($fs->{children}) {
            foreach my $fs2 (@{$fs->{children}}) {
                if ($filesystems{$fs2->{name}}) {
                    $filesystems{$fs2->{name}}->{blocksize} = $fs2->{size};
                } elsif (!$zdevs{$fs2->{name}} && !$zdevs{$rootdev}) { # Don't add partitions already used for ZFS
                    next if (($action eq 'listimagesdevices' || $action eq 'listbackupdevices') && $fs2->{mountpoint} eq '/');
                    my $mp = $fs2->{mountpoint};
                    $filesystems{$fs2->{name}} = {
                        name=>$fs2->{name},
                        blocksize=>$fs2->{size},
                        mountpoint=>$mp,
                        type=>$fs2->{type},
                        nametype=> "$fs2->{name} ($fs2->{type} - " . ($mp?$mp:"not mounted") . " $fs2->{size})",
                        dev=>$fs2->{name}
                    }
                }
            }
        } elsif (!$zdevs{$fs->{name}}) { # Don't add disks already used for ZFS
            my $mp = $fs->{mountpoint};
            next if ($fs->{type} eq 'rom');
            $filesystems{$fs->{name}} = {
                name=>$fs->{name},
                blocksize=>$fs->{size},
                mountpoint=>$fs->{mountpoint},
                type=>$fs->{type},
                nametype=> "$fs->{name} ($fs->{type} - " . ($mp?$mp:"not mounted") . " $fs->{size})",
            }
        }
    }

    # Identify physical devices used for lvm
    $cmd = "pvdisplay -c";
    my $pvs = `$cmd`;
    my @backupdevs; my @imagesdevs;
    foreach my $line (split "\n", $pvs) {
        my ($pvdev, $vgname) = split ":", $line;
        $pvdev = $1 if ($pvdev =~ /\s+(\S+)/);
        $pvdev = $1 if ($pvdev =~ /\/dev\/(\S+)/);
        if ($filesystems{"$vgname-backupvol"}) {
            push @backupdevs, $pvdev unless ($action eq 'listimagesdevices');
        } elsif ($filesystems{"$vgname-imagesvol"}) {
            push @imagesdevs, $pvdev unless ($action eq 'listbackupdevices');
        }
        if (@backupdevs) {
            $filesystems{"$vgname-backupvol"}->{dev} = join(" ", @backupdevs);
            $filesystems{"$vgname-backupvol"}->{nametype} = $filesystems{"$vgname-backupvol"}->{name} . " (lvm with " . $filesystems{"$vgname-backupvol"}->{type} . " on " . join(" ", @backupdevs) . " " . $filesystems{"$vgname-backupvol"}->{size} . ")";
        }
        if (@imagesdevs) {
            $filesystems{"$vgname-imagesvol"}->{dev} = join(" ", @imagesdevs);
            $filesystems{"$vgname-imagesvol"}->{nametype} = $filesystems{"$vgname-imagesvol"}->{name} . " (lvm with " . $filesystems{"$vgname-imagesvol"}->{type} . " on " . join(" ", @imagesdevs) . " " . $filesystems{"$vgname-imagesvol"}->{size} . ")";
        }
        delete $filesystems{$pvdev} if ($filesystems{$pvdev}); # Don't also list as physical device
    }
    my $jsonreply;
    if ($action eq 'getbackupdevice' || $action eq 'getimagesdevice') {
        return ''; # We should not get here
    } elsif ($action eq 'listimagesdevices') {
        $jsonreply .= qq|{"identifier": "name", "label": "nametype", "action": "$action", "items": |;
        my @vals = sort {$b->{'isimagesdev'} cmp $a->{'isimagesdev'}} values %filesystems;
        $jsonreply .= JSON->new->canonical(1)->pretty(1)->encode(\@vals);
        $jsonreply .= "}";
    } elsif ($action eq 'listbackupdevices') {
        $jsonreply .= qq|{"identifier": "name", "label": "nametype", "action": "$action", "items": |;
        my @vals = sort {$b->{'isbackupdev'} cmp $a->{'isbackupdev'}} values %filesystems;
        $jsonreply .= JSON->new->canonical(1)->pretty(1)->encode(\@vals);
        $jsonreply .= "}";
    } else {
        $jsonreply .= JSON->new->canonical(1)->pretty(1)->encode(\%filesystems);
    }
    return $jsonreply;
}

sub do_liststoragepools {
    my ($image, $action) = @_;
    if ($help) {
        return <<END
GET:dojo:
Returns available storage pools. If parameter dojo is set, JSON is padded for Dojo use.
END
    }
    my %npool = (
        "hostpath", "node",
        "path", "--",
        "name", "On node",
        "rdiffenabled", 1,
        "id", "-1");
    my @p = @spools;
    # Present node storage pool if user has sufficient privileges
    if (index($privileges,"a")!=-1 || index($privileges,"n")!=-1) {
        @p = (\%npool);
        push @p, @spools;
    }

    my $jsonreply;
    $jsonreply .= "{\"identifier\": \"id\", \"label\": \"name\", \"items\":" if ($params{'dojo'});
    $jsonreply .= to_json(\@p, {pretty=>1});
    $jsonreply .= "}" if ($params{'dojo'});
    return $jsonreply;
}

# List images available for attaching to server
sub do_listimages {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET:image,image1:
List images available for attaching to server. This is different from [list] since images must be unused and e.g. master images cannot be attached to a server.
An image may be passed as parameter. This image is assumed to be already attached to the server, so it is included, even though it is not unused.
If image1 is passed, we assume user is selecting an optional second image for the server, and an empty entry is included in the response, in order for the user to select "no image".
END
    }
    my $res;
    $res .= header('application/json') unless ($console);
    my $curimg1 = URI::Escape::uri_unescape($params{'image1'});
    my @filteredfiles;
    my @curusers = @users;
    # If an admin user is looking at a server not belonging to him, allow him to see the server
    # users images
    if ($isadmin && $img && $img ne '--' && $register{$img} && $register{$img}->{'user'} ne $user) {
        @curusers = ($register{$img}->{'user'}, "common");
    }

    foreach my $u (@curusers) {
        my @regkeys = (tied %register)->select_where("user = '$u'");
        foreach my $k (@regkeys) {
            my $val = $register{$k};
            if ($val->{'user'} eq $u && (defined $spools[$val->{'storagepool'}]->{'id'} || $val->{'storagepool'}==-1)) {
                my $f = $val->{'path'};
                next if ($f =~ /\/images\/dummy.qcow2/);
                my $itype = $val->{'type'};
                if ($itype eq "vmdk" || $itype eq "img" || $itype eq "vhd" || $itype eq "qcow" || $itype eq "qcow2" || $itype eq "vdi") {
                    my $hit = 0;
                    if ($f =~ /(.+)\.master\.$itype/) {$hit = 1;} # don't list master images for user selections
                    if ($f =~ /(.+)\/common\//) {$hit = 1;} # don't list common images for user selections
                    my $dbstatus = $val->{'status'};
                    if ($dbstatus ne "unused") {$hit = 1;} # Image is in a transitional state - do not use
                    if ($hit == 0 || $img eq $f) {
                        my $hypervisor = ($itype eq "vmdk" || $itype eq "vhd" || $itype eq "vdi")?"vbox":"kvm";
                        my $notes = $val->{'notes'};
                        $notes = "" if $notes eq "--";
                        my %img = ("path", $f, "name", $val->{'name'}, "hypervisor", $hypervisor, "notes", $notes,
                            "uuid", $val->{'uuid'}, "master", $val->{'master'}, "managementlink", $val->{'managementlink'}||"",
                            "upgradelink", $val->{'upgradelink'}||"", "terminallink", $val->{'terminallink'}||"", "version", $val->{'version'}||"",
                            "appid", $val->{'appid'}||"");
                        push @filteredfiles, \%img;
                    }
                }
            }
        }
    }
    my %img = ("path", "--", "name", "--", "hypervisor", "kvm,vbox");
    if ($curimg1) {
        push @filteredfiles, \%img;
    }
    my $json_text = to_json(\@filteredfiles, {pretty=>1});
    $res .= qq/{"identifier": "path", "label": "name", "items": $json_text }/;
    return $res;
}

sub Listcdroms {
    my ($image, $action) = @_;
    if ($help) {
        return <<END
GET::
Lists the CD roms a user has access to.
END
    }
    my $res;
    $res .= header('application/json') unless ($console);
    my @filteredfiles;
    foreach my $u (@users) {
        my @regkeys = (tied %register)->select_where("user = '$u'");
        foreach my $k (@regkeys) {
            my $val = $register{$k};
            my $f = $val->{'path'};
            if ($val->{'user'} eq $u && (defined $spools[$val->{'storagepool'}]->{'id'} || $val->{'storagepool'}==-1)) {
                my $itype = $val->{'type'};
                if ($itype eq "iso" || $itype eq "toast") {
                    $notes = $val->{'notes'} || '';
                    if ($u eq $user) {
                        $installable = "true";
                    #    $notes = "This CD/DVD may work just fine, however it has not been tested to work with Irigo Servers.";
                    } else {
                        $installable = $val->{'installable'} || 'false';
                    #    $notes = "This CD/DVD has been tested to work with Irigo Servers." unless $notes;
                    }
                    my %img = ("path", $f, "name", $val->{'name'}, "installable", $installable, "notes", $notes);
                    push @filteredfiles, \%img;
                }
            }
        }
    }
    my %ioimg = ("path", "virtio", "name", "-- VirtIO disk (dummy) --");
    push @filteredfiles, \%ioimg;
    my %dummyimg = ("path", "--", "name", "-- No CD --");
    push @filteredfiles, \%dummyimg;
    #        @filteredfiles = (sort {$a->{'name'} cmp $b->{'name'}} @filteredfiles); # Sort by status
    my $json_text = to_json(\@filteredfiles, {pretty=>1});
    $res .= qq/{"identifier": "path", "label": "name", "items": $json_text }/;
    return $res;
}

sub do_listmasterimages {
    my ($image, $action) = @_;
    if ($help) {
        return <<END
GET::
Lists master images available to the current user.
END
    }
    my $res;
    $res .= header('application/json') unless ($console);

    my @filteredfiles;
    my @busers = @users;
    push (@busers, $billto) if ($billto); # We include images from 'parent' user

    foreach my $u (@busers) {
        my @regkeys = (tied %register)->select_where("user = '$u'");
        foreach my $k (@regkeys) {
            my $valref = $register{$k};
            my $f = $valref->{'path'};
            if ($valref->{'user'} eq $u && (defined $spools[$valref->{'storagepool'}]->{'id'} || $valref->{'storagepool'}==-1)) {
                # Only list installable master images from billto account
                next if ($billto && $u eq $billto && $valref->{'installable'} ne 'true');

                my $itype = $valref->{'type'};
                if ($itype eq "qcow2" && $f =~ /(.+)\.master\.$itype/) {
                    my $installable;
                    my $status = $valref->{'status'};
                    my $notes;
                    if ($u eq $user) {
                        $installable = "true";
                        $notes = "This master image may work just fine, however it has not been tested to work with Stabile.";
                    } else {
                        $installable = $valref->{'installable'};
                        $notes = $valref->{'notes'};
                        $notes = "This master image has been tested to work with Irigo Servers." unless $notes;
                    }
                    my %img = (
                        "path", $f,
                        "name", $valref->{'name'},
                        "installable", $installable,
                        "notes", $notes,
                        "managementlink", $valref->{'managementlink'}||"",
                        "upgradelink", $valref->{'upgradelink'}||"",
                        "terminallink", $valref->{'terminallink'}||"",
                        "image2", $valref->{'image2'}||"",
                        "version", $valref->{'version'}||"",
                        "appid", $valref->{'appid'}||"",
                        "status", $status,
                        "user", $valref->{'user'}
                    );
                    push @filteredfiles, \%img;
                }
            }
        }
    }
    my %img = ("path", "--", "name", "--", "installable", "true", "status", "unused");
    push @filteredfiles, \%img;
    my $json_text = to_json(\@filteredfiles);
    $res .= qq/{"identifier": "path", "label": "name", "items": $json_text }/;
    return $res;
}

sub Updatebtime {
    my ($img, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
END
    }
    my $res;
    $curimg = $curimg || $img;
    my $imguser = $register{$curimg}->{'user'};
    if ($isadmin || $imguser eq $user) {
        my $btime;
        $btime = getBtime($curimg, $imguser) if ($imguser);
        if ($btime) {
            $register{$curimg}->{'btime'} = $btime ;
            $res .= "Status=OK $curimg has btime: " . scalar localtime( $btime ) . "\n";
        } else {
            $res .= "Status=OK $curimg has no btime\n";
        }
    } else {
        $res .= "Status=Error no access to $curimg\n";
    }
    return $res;
}

sub Updateallbtimes {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET::
END
    }
    if ($isadmin) {
        foreach my $path (keys %register) {
            my $imguser = $register{$path}->{'user'};
            my $btime = getBtime($path, $imguser);
            if ($btime) {
                $register{$path}->{'btime'} = $btime ;
                $postreply .= "Status=OK $register{$path}->{'name'} ($path) has btime: " . scalar localtime( $btime ) . "\n";
            } else {
                $postreply .= "Status=OK $register{$path}->{'name'} ($path) has no btime\n";
            }
        }
    } else {
        $postreply .= "Status=ERROR you are not allowed to do this.\n";
    }
    return $postreply;
}

# Activate image from fuel
sub Activate {
    my ($curimg, $action, $argref) = @_;
    if ($help) {
        return <<END
GET:image, name, managementlink, upgradelink, terminallink, force:
Activate an image from fuel storage, making it available for regular use.
END
    }
    my %uargs = %{$argref};
    my $name = URI::Escape::uri_unescape($uargs{'name'});
    my $managementlink = URI::Escape::uri_unescape($uargs{'managementlink'});
    my $upgradelink = URI::Escape::uri_unescape($uargs{'upgradelink'});
    my $terminallink = URI::Escape::uri_unescape($uargs{'terminallink'});
    my $version = URI::Escape::uri_unescape($uargs{'version'}) || '1.0b';
    my $image2 =  URI::Escape::uri_unescape($uargs{'image2'});
    my $force = $uargs{'force'};

    return "Status=ERROR image must be in fuel storage ($curimg)\n" unless ($curimg =~ /^\/mnt\/fuel\/pool(\d+)\/(.+)/);
    my $pool = $1;
    my $ipath = $2;
    return "Status=ERROR image is not a qcow2 image ($curimg, $ipath)\n" unless ($ipath =~ /(.+\.qcow2$)/);
    my $npath = $1;
    my $ppath = '';
    if ($npath =~ /(.*\/)(.+\.qcow2$)/) {
        $npath = $2;
        $ppath = $1;
    }
    my $imagepath = $tenderpathslist[$pool] . "/$user/fuel/$ipath";
    my $newpath = $tenderpathslist[$pool] . "/$user/$npath";
    return "Status=ERROR image not found ($imagepath)\n" unless (-e $imagepath);
    return "Status=ERROR image already exists in destination ($newpath)\n" if (-e $newpath && !$force);
    return "Status=ERROR image is in use ($newpath)\n" if (-e $newpath && $register{$newpath} && $register{$newpath}->{'status'} ne 'unused');

    my $virtualsize = `qemu-img info "$imagepath" | sed -n -e 's/^virtual size: .*(//p' | sed -n -e 's/ bytes)//p'`;
    chomp $virtualsize;
    my $master = `qemu-img info "$imagepath" | sed -n -e 's/^backing file: //p' | sed -n -e 's/ (actual path:.*)\$//p'`;
    chomp $master;

    # Now deal with image2
    my $newpath2 = '';
    if ($image2) {
        $image2 = "/mnt/fuel/pool$pool/$ppath$image2" unless ($image2 =~ /^\//);
        return "Status=ERROR image2 must be in fuel storage ($image2)\n" unless ($image2 =~ /^\/mnt\/fuel\/pool$pool\/(.+)/);
        $ipath = $1;
        return "Status=ERROR image is not a qcow2 image\n" unless ($ipath =~ /(.+\.qcow2$)/);
        $npath = $1;
        $npath = $1 if ($npath =~ /.*\/(.+\.qcow2$)/);
        my $image2path = $tenderpathslist[$pool] . "/$user/fuel/$ipath";
        $newpath2 = $tenderpathslist[$pool] . "/$user/$npath";
        return "Status=ERROR image2 not found ($image2path)\n" unless (-e $image2path);
        return "Status=ERROR image2 already exists in destination ($newpath2)\n" if (-e $newpath2 && !$force);
        return "Status=ERROR image2 is in use ($newpath2)\n" if (-e $newpath2 && $register{$newpath2} && $register{$newpath2}->{'status'} ne 'unused');

        my $virtualsize2 = `qemu-img info "$image2path" | sed -n -e 's/^virtual size: .*(//p' | sed -n -e 's/ bytes)//p'`;
        chomp $virtualsize2;
        my $master2 = `qemu-img info "$image2path" | sed -n -e 's/^backing file: //p' | sed -n -e 's/ (actual path:.*)\$//p'`;
        chomp $master2;
        if ($register{$master2}) {
            $register{$master2}->{'status'} = 'used';
        }
        `mv "$image2path" "$newpath2"`;
        if (-e $newpath2) {
            my $ug = new Data::UUID;
            my $newuuid = $ug->create_str();
            unless ($name) {
                $name = $npath if ($npath);
                $name = $1 if ($name =~ /(.+)\.(qcow2)$/);
            }
            $register{$newpath2} = {
                uuid => $newuuid,
                path => $newpath2,
                master => $master2,
                name => "$name (data)",
                user => $user,
                storagepool => $pool,
                type => 'qcow2',
                status => 'unused',
                version => $version,
                virtualsize => $virtualsize2
            };
            $postreply .= "Status=OK Activated data image $newpath2, $name (data), $newuuid\n";
        } else {
            $postreply .=  "Status=ERROR Unable to activate $image2path, $newpath2\n";
        }
    }

    # Finish up primary image
    if ($register{$master}) {
        $register{$master}->{'status'} = 'used';
    }
    `mv "$imagepath" "$newpath"`;
    if (-e $newpath) {
        my $ug = new Data::UUID;
        my $newuuid = $ug->create_str();
        unless ($name) {
            $name = $npath if ($npath);
            $name = $1 if ($name =~ /(.+)\.(qcow2)$/);
        }
        $register{$newpath} = {
            uuid => $newuuid,
            path => $newpath,
            master => $master,
            name => $name,
            user => $user,
            storagepool => $pool,
            image2 => $newpath2,
            type => 'qcow2',
            status => 'unused',
            installable => 'true',
            managementlink => $managementlink || '/stabile/pipe/http://{uuid}:10000/stabile/',
            upgradelink => $upgradelink,
            terminallink => $terminallink,
            version => $version,
            virtualsize => $virtualsize
        };
        $postreply .=  "Status=OK Activated $newpath, $name, $newuuid\n";
    } else {
        $postreply .=  "Status=ERROR Unable to activate $imagepath to $newpath\n";
    }
    return $postreply;
}

sub Publish {
    my ($uuid, $action, $parms) = @_;
    if ($help) {
        return <<END
GET:image,appid,appstore,force:
Publish a stack to registry. Set [force] if you want to force overwrite images in registry - use with caution.
END
    }
    my $res;
    $uuid = $parms->{'uuid'} if ($uuid =~ /^\// || !$uuid);
    my $force = $parms->{'force'};

    if ($isreadonly) {
        $res .= "Status=ERROR Your account does not have the necessary privilege.s\n";
    } elsif (!$uuid || !$imagereg{$uuid}) {
        $res .= "Status=ERROR At least specify activated master image uuid [uuid or path] to publish.\n";
    } elsif ($imagereg{$uuid}->{'user'} ne $user && !$isadmin) {
        $res .= "Status=ERROR Your account does not have the necessary privileges.\n";
    } elsif ($imagereg{$uuid}->{'path'} =~ /.+\.master\.qcow2$/) {
        if ($engineid eq $valve001id) { # On valve001 - check if meta file exists
            if (-e $imagereg{$uuid}->{'path'} . ".meta") {
                $res .= "On valve001. Found meta file $imagereg{$uuid}->{'path'}.meta\n";
                my $appid = `cat $imagereg{$uuid}->{'path'}.meta | sed -n -e 's/^APPID=//p'`;
                chomp $appid;
                if ($appid) {
                    $parms->{'appid'} = $appid;
                    $register{$imagereg{$uuid}->{'path'}}->{'appid'} = $appid;
                    tied(%register)->commit;
                }
            }
        # On valve001 - move image to stacks
            if ($imagereg{$uuid}->{'storagepool'} ne '0') {
                $res .= "Status=OK Moving image: " . Move($imagereg{$uuid}->{'path'}, $user, 0) . "\n";
            } else {
                $res .= "Status=OK Image is already available in registry\n";
            }
        } else {
        #    $console = 1;
        #    my $link = Download($imagereg{$uuid}->{'path'});
        #    chomp $link;
        #    $parms->{'downloadlink'} = $link; # We now upload instead
        #    $res .= "Status=OK Asking registry to download $parms->{'APPID'} image: $link\n";
            if ($appstores) {
                $parms->{'appstore'} = $appstores;
            } elsif ($appstoreurl =~ /www\.(.+)\//) {
                $parms->{'appstore'} = $1;
                $res .= "Status=OK Adding registry: $1\n";
            }
        }

        my %imgref = %{$imagereg{$uuid}};
        $parms = Hash::Merge::merge($parms, \%imgref);
        my $postdata = to_json($parms);
        my $postres = $main::postToOrigo->($engineid, 'publishapp', $postdata);
        $res .= $postres;
        my $appid;
        $appid = $1 if ($postres =~ /appid: (\d+)/);
        my $path = $imagereg{$uuid}->{'path'};
        if ($appid) {
            $register{$path}->{'appid'} = $appid if ($register{$path});
            $res .= "Status=OK Received appid $appid for $path, uploading image to registry, hang on...\n";
            my $upres .= $main::uploadToOrigo->($engineid, $path, $force);
            $res .= $upres;
            my $image2 = $register{$path}->{'image2'} if ($register{$path});
            if ($upres =~ /Status=OK/ && $image2 && $image2 ne '--') { # Stack has a data image
                $res .= $main::uploadToOrigo->($engineid, $image2, $force);
            }
        } else {
            $res .= "Status=Error Did not get an appid\n";
        }
    } else {
        $res .= "Status=ERROR You can only publish a master image.\n";
    }
    return $res;
}

sub Release {
    my ($uuid, $action, $parms) = @_;
    if ($help) {
        return <<END
GET:image,appid,appstore,force,unrelease:
Releases a stack in the registry, i.e. moves it from being a private stack only owner and owner's users can see and use to being a public stack, everyone can use. Set [force] if you want to force overwrite images in registry - use with caution.
END
    }
    my $res;
    $uuid = $parms->{'uuid'} if ($uuid =~ /^\// || !$uuid);
    my $force = $parms->{'force'};
    my $unrelease = $parms->{'unrelease'};

    if (!$uuid || !$imagereg{$uuid}) {
        $res .= "Status=ERROR At least specify master image uuid [uuid or path] to release.\n";
    } elsif (!$isadmin) {
        $res .= "Status=ERROR Your account does not have the necessary privileges.\n";
    } elsif ($imagereg{$uuid}->{'path'} =~ /.+\.master\.qcow2$/ && $imagereg{$uuid}->{'appid'}) {
        my $action = 'release';
        my $targetuser = 'common';
        if ($unrelease) {
            $action = 'unrelease';
            $targetuser = $user;
        }
        if ($appstores) {
            $parms->{'appstore'} = $appstores;
        } elsif ($appstoreurl =~ /www\.(.+)\//) {
            $parms->{'appstore'} = $1;
            $res .= "Status=OK Adding registry: $1\n";
        }
        $parms->{'appid'} = $imagereg{$uuid}->{'appid'};
        $parms->{'force'} = $force if ($force);
        $parms->{'unrelease'} = $unrelease if ($unrelease);
        my $postdata = to_json($parms);
        my $postres = $main::postToOrigo->($engineid, 'releaseapp', $postdata);
        $res .= $postres;
        my $appid;
        $appid = $1 if ($postres =~ /Status=OK Moved (\d+)/);
        my $path = $imagereg{$uuid}->{'path'};
        if ($appid) {
            $res.= "Now moving local stack to $targetuser\n";
            # First move data image
            my $image2 = $register{$path}->{'image2'} if ($register{$path});
            my $newimage2 = $image2;
            if ($image2 && $image2 ne '--' && $register{$image2}) { # Stack has a data image
                if ($unrelease) {
                    $newimage2 =~ s/common/$register{$image2}->{'user'}/;
                } else {
                    $newimage2 =~ s/$register{$image2}->{'user'}/common/;
                }
                $register{$path}->{'image2'} = $newimage2;
                tied(%register)->commit;
                $res .= Move($image2, $targetuser, '', '', 1);
            }
            # Move image
            $res .= Move($path, $targetuser, '', '', 1);
            $res .= "Status=OK $action $appid\n";
        } else {
            $res .= "Status=Error $action failed\n";
        }
    } else {
        $res .= "Status=ERROR You can only $action a master image that has been published.\n";
    }
    return $res;
}

sub do_unlinkmaster {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET:image,path:
END
    }
    my $res;
    $res .= header('text/html') unless ($console);
    if ($isreadonly) {
        $res .= "Your account does not have the necessary privileges\n";
    } elsif ($curimg) {
        $res .= unlinkMaster($curimg) . "\n";
    } else {
        $res .= "Please specify master image to link\n";
    }
    return $res;
}

# Simple action for unmounting all images
sub do_unmountall {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET:image,path:
END
    }
    return "Your account does not have the necessary privileges\n" if ($isreadonly);
    my $res;
    $res .= header('text/plain') unless ($console);
    $res .= "Unmounting all images for $user\n";
    unmountAll();
    $res .= "\n$postreply" if ($postreply);
    return $res;
}

sub Updatedownloads {
    my ($img, $action) = @_;
    if ($help) {
        return <<END
GET:image,path:
END
    }
    my $res;
    $res .= header('text/html') unless ($console);
    my $txt1 = <<EOT
Options -Indexes
EOT
    ;
    `/bin/mkdir "$Stabile::basedir/download"` unless (-e "$Stabile::basedir/download");
    $res .= "Writing .htaccess: -> $Stabile::basedir/download/.htaccess\n";
    unlink("$Stabile::basedir/download/.htaccess");
    `chown www-data:www-data "$Stabile::basedir/download"`;
    `/bin/echo "$txt1" | sudo -u www-data tee "$Stabile::basedir/download/.htaccess"`; #This ugliness is needed because of ownership issues with Synology NFS
    `chmod 644 "$Stabile::basedir/download/.htaccess"`;
    foreach my $p (@spools) {
        my $dir = $p->{'path'};
        my $id = $p->{'id'};
        `/bin/rm "$Stabile::basedir/download/$id"; /bin/ln -s "$dir" "$Stabile::basedir/download/$id"`;
        $res .= "Writing .htaccess: $id -> $dir/.htaccess\n";
        unlink("$dir/.htaccess");
        `/bin/echo "$txt1" | tee "$dir/.htaccess"`;
        `chown www-data:www-data "$dir/.htaccess"`;
        `chmod 644 "$dir/.htaccess"`;
    }

    unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};

    foreach my $username (keys %userreg) {
        my $require = '';
        my $txt = <<EOT
order deny,allow
AuthName "Download"
AuthType None
TKTAuthLoginURL $baseurl/auth/login.cgi
TKTAuthIgnoreIP on
deny from all
Satisfy any
require user $username
Options -Indexes
EOT
        ;
        foreach my $p (@spools) {
            my $dir = $p->{'path'};
            my $id = $p->{'id'};
            if (-d "$dir/$username") {
                $res .= "Writing .htaccess: $id -> $dir/$username/.htaccess\n";
                unlink("$dir/$username/.htaccess");
                `/bin/echo "$txt1" | sudo -u www-data tee $dir/$username/.htaccess`;
            }
        }
    }
    untie %userreg;
    return $res;
}

sub do_listpackages($action) {
    my ($image, $action) = @_;
    if ($help) {
        return <<END
GET:image:
Tries to mount and list software packages installed on the operating system on an image. The image must be mountable and contain a valid operating system.
END
    }
    my $res;
    $res .= header('text/plain') unless ($console);

    my $mac = $register{$image}->{'mac'};
    my $macip;
    if ($mac && $mac ne '--') {
        unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
        $macip = $nodereg{$mac}->{'ip'};
        untie %nodereg;
    }
    $image =~ /(.+)/; $image = $1;
    my $apps;

    if ($macip && $macip ne '--') {
        my $cmd = qq[eval \$(/usr/bin/guestfish --ro -a "$image" --i --listen); ]; # sets $GUESTFISH_PID shell var
        $cmd .= qq[root="\$(/usr/bin/guestfish --remote inspect-get-roots)"; ];
        $cmd .= qq[guestfish --remote inspect-list-applications "\$root"; ];
        $cmd .= qq[guestfish --remote inspect-get-product-name "\$root"; ];
        $cmd .= qq[guestfish --remote exit];
        $cmd = "$sshcmd $macip '$cmd'";
        $apps = `$cmd`;
    } else {
        my $cmd;
        #        my $pid = open my $cmdpipe, "-|",qq[/usr/bin/guestfish --ro -a "$image" --i --listen];
        $cmd .= qq[eval \$(/usr/bin/guestfish --ro -a "$image" --i --listen); ];
        # Start listening guestfish
        my $daemon = Proc::Daemon->new(
            work_dir => '/usr/local/bin',
            setuid => 'www-data',
            exec_command => $cmd
        ) or do {$postreply .= "Status=ERROR $@\n";};
        my $pid = $daemon->Init();
        while ($daemon->Status($pid)) {
            sleep 1;
        }
        # Find pid of the listening guestfish
        my $pid2;
        my $t = new Proc::ProcessTable;
        foreach $p ( @{$t->table} ){
            my $pcmd = $p->cmndline;
            if ($pcmd =~ /guestfish.+$image/) {
                $pid2 = $p->pid;
                last;
            }
        }

        my $cmd2;
        if ($pid2) {
            $cmd2 .= qq[root="\$(/usr/bin/guestfish --remote=$pid2 inspect-get-roots)"; ];
            $cmd2 .= qq[guestfish --remote=$pid2 inspect-list-applications "\$root"; ];
            $cmd2 .= qq[guestfish --remote=$pid2 inspect-get-product-name "\$root"; ];
            $cmd2 .= qq[guestfish --remote=$pid2 exit];
        }
        $apps = `$cmd2`;
    }
    if ($console) {
        $res .= $apps;
    } else {
        my @packages;
        my @packages2;
        open my $fh, '<', \$apps or die $!;
        my $i;
        while (<$fh>) {
            if ($_ =~ /\[(\d+)\]/) {
                push @packages2, $packages[$i];
                $i = $1;
            } elsif ($_ =~ /(\S+): (.+)/ && $2) {
                $packages[$i]->{$1} = $2;
            }
        }
        close $fh or die $!;
        $res .= to_json(\@packages, {pretty => 1});
    }
    return $res;
}

sub Inject {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
Tries to inject drivers into a qcow2 image with a Windows OS installed on it. Image must not be in use.
END
    }
    $uistatus = "injecting";
    my $path = $obj->{path} || $curimg;
    my $status = $obj->{status};
    my $esc_localpath = shell_esc_chars($path);

    # Find out if we are dealing with a Windows image
    my $xml = `bash -c '/usr/bin/virt-inspector -a "$esc_localpath"'`;
    #my $xml = `bash -c '/usr/bin/virt-inspector -a "$esc_localpath"' 2>&1`;
    # $res .= $xml . "\n";
    my $xmlref;
    my $osname;
    $xmlref = XMLin($xml) if ($xml =~ /^<\?xml/);
    $osname = $xmlref->{operatingsystem}->{name} if ($xmlref);
    if ($xmlref && $osname eq 'windows') {
        my $upath = $esc_localpath;
        # We need write privileges
        $res .= `chmod 666 "$upath"`;
        # First try to merge storage registry keys into Windows registry. If not a windows vm it simply fails.
        $res .= `bash -c 'cat /usr/share/stabile/mergeide.reg | /usr/bin/virt-win-reg --merge "$upath"' 2>&1`;
        # Then try to merge the critical device keys. This has been removed in win8 and 2012, so will simply fail for these.
        $res .= `bash -c 'cat /usr/share/stabile/mergeide-CDDB.reg | /usr/bin/virt-win-reg --merge "$upath"' 2>&1`;
        if ($res) { debuglog($res); $res = ''; }

        # Try to copy viostor.sys into image
        my @winpaths = (
            '/Windows/System32/drivers',
            '/WINDOWS/system32/drivers/viostor.sys',
            '/WINDOWS/System32/drivers/viostor.sys',
            '/WINNT/system32/drivers/viostor.sys'
        );
        foreach my $winpath (@winpaths) {
            my $lscmd = qq|bash -c 'virt-ls -a "$upath" "$winpath"'|;
            my $drivers = `$lscmd`;
            if ($drivers =~ /viostor/i) {
                $postreply .= "Status=OK viostor already installed in $winpath in $upath\n";
                $main::syslogit->($user, "info", "viostor already installed in $winpath in $upath");
                last;
            } elsif ($drivers) {
                my $cmd = qq|bash -c 'guestfish -i -a "$upath" upload /usr/share/stabile/VIOSTOR.SYS $winpath/viostor.sys' 2>&1|;
                my $error = `$cmd`;
                if ($error) {
                    $postreply .= "Status=ERROR Problem injecting virtio drivers into $upath: $error\n";
                    $main::syslogit->($user, "info", "Error injecting virtio drivers into $upath: $error");
                } else {
                    $postreply .= "Status=$status Injected virtio drivers into $upath";
                    $main::syslogit->($user, "info", "Injected virtio drivers into $upath");
                }
                last;
            } else {
                $postreply .= "Status=ERROR No drivers found in $winpath\n";
            }
        }

    } else {
        $postreply .= "Status=ERROR No Windows OS found in $osname image, not injecting drivers.\n";
        $main::syslogit->($user, "info", "No Windows OS found ($osname) in image, not injecting drivers.");
    }
    my $msg = $postreply;
    $msg = $1 if ($msg =~ /\w+=\w+ (.+)/);
    chomp $msg;
    $main::updateUI->({tab=>"images", user=>$user, type=>"update", uuid=>$obj->{'uuid'}, status=>$status, message=>$msg});
    $postreply .=  "Status=OK $uistatus $obj->{type} image: $obj->{name}\n";
    $main::syslogit->($user, "info", "$uistatus $obj->{type} image: $obj->{name}: $uuid");
    return $postreply;
}

sub Convert {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
Converts an image to qcow2 format. Image must not be in use.
END
    }
    my $path = $obj->{path};
    $uistatus = "converting";
    $uipath = $path;
    if ($obj->{status} ne "unused" && $obj->{status} ne "used" && $obj->{status} ne "paused") {
        $postreply .= "Status=ERROR Problem $uistatus $obj->{type} image: $obj->{name}\n";
    } elsif ($obj->{type} eq "img" || $obj->{type} eq "vmdk" || $obj->{type} eq "vhd") {
        my $oldpath = $path;
        my $newpath = "$path.qcow2";
        if ($obj->{mac} && $path =~ /\/mnt\/stabile\/node\//) {
            unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
            $macip = $nodereg{$obj->{mac}}->{'ip'};
            untie %nodereg;
            $oldpath = "$macip:$path";
        } else { # We are not on a node - check that image is not on a read-only filesystem
            my ($fname, $destfolder) = fileparse($path);
            my $ro = `touch "$destfolder/test.tmp" && { rm "$destfolder/test.tmp"; } || echo "read-only" 2>/dev/null`;
            if ($ro) { # Destinationfolder is not writable
                my $npath = "$spools[0]->{'path'}/$register{$path}->{'user'}/$fname.qcow2";
                $newpath = $npath;
            }
            if (-e $newpath) { # Don't overwrite existing file
                my $subpath = substr($newpath,0,-6);
                my $i = 1;
                if ($newpath =~ /(.+)\.(\d+)\.qcow2/) {
                    $i = $2;
                    $subpath = $1;
                }
                while (-e $newpath) {
                    $newpath = $subpath . ".$i.qcow2";
                    $i++;
                }
            }
        }
        eval {
            my $ug = new Data::UUID;
            my $newuuid = $ug->create_str();

            $register{$newpath} = {
                uuid=>$newuuid,
                name=>"$obj->{name} (converted)",
                notes=>$obj->{notes},
                image2=>$obj->{image2},
                managementlink=>$obj->{managementlink},
                upgradelink=>$obj->{managementlink},
                terminallink=>$obj->{terminallink},
                storagepool=>$obj->{regstoragepool},
                status=>$uistatus,
                mac=>($obj->{regstoragepool} == -1)?$obj->{mac}:"",
                size=>0,
                realsize=>0,
                virtualsize=>$obj->{virtualsize},
                type=>"qcow2",
                user=>$user
            };
            $register{$path}->{'status'} = $uistatus;

            my $daemon = Proc::Daemon->new(
                work_dir => '/usr/local/bin',
                exec_command => "perl -U steamExec $user $uistatus $obj->{status} \"$oldpath\" \"$newpath\""
            ) or do {$postreply .= "Status=ERROR $@\n";};
            my $pid = $daemon->Init() or do {$postreply .= "Status=ERROR $@\n";};
            $postreply .=  "Status=OK $uistatus $obj->{type} image: $obj->{name}\n";
            $main::syslogit->($user, "info", "$uistatus $obj->{type} image: $obj->{name}: $uuid");
            1;
        } or do {$postreply .= "Status=ERROR $@\n";};
        $main::updateUI->({tab=>"images", user=>$user, type=>"update"});
    } else {
        $postreply .= "Status=ERROR Only img and vmdk images can be converted\n";
    }
}

sub Snapshot {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
Adds a snapshot to a qcow2 image. Image can not be in use by a running server.
END
    }
    my $status = $obj->{status};
    my $path = $obj->{path};
    my $macip;
    $uistatus = "snapshotting";
    $uiuuid = $obj->{uuid};
    if ($status ne "unused" && $status ne "used") {
        $postreply .= "Status=ERROR Problem $uistatus $obj->{type} image: $obj->{name}\n";
    } elsif ($obj->{type} eq "qcow2") {
        my $newpath = $path;
        my $hassnap;
        my $snaptime = time;
        if ($obj->{mac} && $path =~ /\/mnt\/stabile\/node\//) {
            unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
            $macip = $nodereg{$obj->{mac}}->{'ip'};
            untie %nodereg;
            $newpath = "$macip:$path";
            my $esc_path = $path;
            $esc_path =~ s/([ ])/\\$1/g;
            my $qinfo = `$sshcmd $macip "sudo /usr/bin/qemu-img snapshot -l $esc_path"`;
            $hassnap = ($qinfo =~ /snap1/g);
            $postreply .= `$sshcmd $macip "sudo /usr/bin/qemu-img snapshot -d snap1 $esc_path"` if ($hassnap);
        } else {
            my $qinfo = `/usr/bin/qemu-img snapshot -l "$path"`;
            $hassnap = ($qinfo =~ /snap1/g);
            $postreply .= `/usr/bin/qemu-img snapshot -d snap1 "$path\n"` if ($hassnap);
        }
        eval {
            if ($hassnap) {
                $postreply .= "Status=Error Only one snapshot per image is supported for $obj->{type} image: $obj->{name} ";
            } else {
                $register{$path}->{'status'} = $uistatus;
                $register{$path}->{'snap1'} = $snaptime;

                if ($macip) {
                    my $esc_localpath = shell_esc_chars($path);
                    $res .= `$sshcmd $macip "sudo /usr/bin/qemu-img snapshot -c snap1 $esc_localpath"`;
                } else {
                    $res .= `/usr/bin/qemu-img snapshot -c snap1 "$path"`;
                }
                $register{$path}->{'status'} = $status;
                $postreply .=  "Status=$uistatus OK $uistatus $obj->{type} image: $obj->{name}\n";
                $main::syslogit->($user, "info", "$uistatus $obj->{type} image: $obj->{name}: $uuid");
            }
            1;
        } or do {$postreply .= "Status=ERROR $@\n";};
        $main::updateUI->({tab=>"images", user=>$user, type=>"update", uuid=>$obj->{'uuid'}, status=>$status, snap1=>$snaptime});
    } else {
        $postreply .= "Status=ERROR Only qcow2 images can be snapshotted\n";
    }
    return $postreply;
}

sub Unsnap {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
Removes a snapshot from a qcow2 image. Image can not be in use by a running server.
END
    }
    my $status = $obj->{status};
    my $path = $obj->{path};
    $uistatus = "unsnapping";
    $uiuuid = $obj->{uuid};
    my $macip;

    if ($status ne "unused" && $status ne "used") {
        $postreply .= "Status=ERROR Problem $uistatus $obj->{type} image: $obj->{name}\n";
    } elsif ($obj->{type} eq "qcow2") {
        my $newpath = $path;
        my $hassnap;
        my $qinfo;
        my $esc_path;
        if ($obj->{mac} && $path =~ /\/mnt\/stabile\/node\//) {
            unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
            $macip = $nodereg{$obj->{mac}}->{'ip'};
            untie %nodereg;
            $newpath = "$macip:$path";
            $esc_path = $path;
            $esc_path =~ s/([ ])/\\$1/g;
            $qinfo = `$sshcmd $macip "sudo /usr/bin/qemu-img snapshot -l $esc_path"`;
            $hassnap = ($qinfo =~ /snap1/g);
        } else {
            $qinfo = `/usr/bin/qemu-img snapshot -l "$path"`;
            $hassnap = ($qinfo =~ /snap1/g);
        }
        eval {
            my $snaptime = time;
            if ($hassnap) {
                delete $register{$path}->{'snap1'};
                $register{$path}->{'status'} = $uistatus;
                if ($macip) {
                    my $esc_localpath = shell_esc_chars($path);
                    $res .= `$sshcmd $macip "sudo /usr/bin/qemu-img snapshot -d snap1 $esc_localpath"`;
                } else {
                    $res .= `/usr/bin/qemu-img snapshot -d snap1 "$path"`;
                }
                $register{$path}->{'status'} = $status;
                $postreply .=  "Status=$uistatus OK $uistatus $obj->{type} image: $obj->{name}\n";
                $main::syslogit->($user, "info", "$uistatus $obj->{type} image: $obj->{name}: $uuid");
            } else {
                $postreply .= "Status=ERROR No snapshot found in $obj->{name}\n";
                delete $register{$path}->{'snap1'};
                $uistatus = $status;
            }
            1;
        } or do {$postreply .= "Status=ERROR $@\n";};
        $main::updateUI->({tab=>"images", user=>$user, type=>"update", uuid=>$obj->{'uuid'}, status=>$status, snap1=>'--'});
    } else {
        $postreply .= "Status=ERROR Only qcow2 images can be unsnapped\n";
    }
    return $postreply;
}

sub Revert {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
Applies a snapshot to a qcow2 image, i.e. the image is reverted to the state it was in when the snapshot was taken. Image can not be in use by a running server.
END
    }
    my $status = $obj->{status};
    my $path = $obj->{path};
    $uistatus = "reverting";
    $uipath = $path;
    my $macip;
    if ($status ne "used" && $status ne "unused") {
        $postreply .= "Status=ERROR Please shut down or pause your virtual machine before reverting\n";
    } elsif ($obj->{type} eq "qcow2") {
        my $newpath = $path;
        my $hassnap;
        if ($obj->{mac} && $path =~ /\/mnt\/stabile\/node\//) {
            unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
            $macip = $nodereg{$obj->{mac}}->{'ip'};
            untie %nodereg;
            $newpath = "$macip:$path";
            my $esc_path = $path;
            $esc_path =~ s/([ ])/\\$1/g;
            my $qinfo = `ssh -l irigo -i /var/www/.ssh/id_rsa_www -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no $macip "/usr/bin/qemu-img snapshot -l $esc_path"`;
            $hassnap = ($qinfo =~ /snap1/g);
        } else {
            my $qinfo = `/usr/bin/qemu-img snapshot -l "$path"`;
            $hassnap = ($qinfo =~ /snap1/g);
        }
        eval {
            if ($hassnap) {
                $register{$path}->{'status'} = $uistatus;
                if ($macip) {
                    my $esc_localpath = shell_esc_chars($path);
                    $res .= `$sshcmd $macip "sudo /usr/bin/qemu-img snapshot -a snap1 $esc_localpath"`;
                } else {
                    $res .= `/usr/bin/qemu-img snapshot -a snap1 "$path1"`;
                }
                $register{$path}->{'status'} = $status;
                $postreply .=  "Status=OK $uistatus $obj->{type} image: $obj->{name}\n";
                $main::syslogit->($user, "info", "$uistatus $obj->{type} image: $obj->{name}: $uuid");
            } else {
                $postreply .= "Status=ERROR no snapshot found\n";
                $uistatus = $status;
            }
            1;
        } or do {$postreply .= "Status=ERROR $@\n";};
        $main::updateUI->({tab=>"images", user=>$user, type=>"update", uuid=>$obj->{'uuid'}, status=>$status, snap1=>'--'});
    } else {
        $postreply .= "Status=ERROR Only qcow2 images can be reverted\n";
    }
    return;
}

sub Zbackup {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:mac,storagepool,synconly,snaponly,imageretention,backupretention:
Backs all images on ZFS storage up by taking a storage snapshot. By default all shared storagepools are backed up.
If storagepool -1 is specified, all ZFS node storages is backed up. If "mac" is specified, only specific node is backed up.
If "synconly" is set, no new snapshots are taken - only syncing of snapshots is performed.
If "snaponly" is set, only local active storage snapshot is taken - no sending to backup storage is done.
"xretention" can be either simply number of snapshots to keep, or max age of snapshot to keep in seconds [s], hours [h] or days [d],
e.g. "imageretention=10" will keep 10 image snapshots, "imageretention=600s" will purte image snapshots older than 600 seconds if possible, or "backretention=14d" will purge backup snapshots older than 14 days.
END
    }
    if ($isadmin) {
        my $synconly = $obj->{'synconly'};
        my $snaponly = $obj->{'snaponly'};
        my $mac = $obj->{'mac'};
        my $storagepool = $obj->{'storagepool'};
        $storagepool = -1 if ($mac);
        my $imageretention = $obj->{'imageretention'} || $imageretention;
        my $backupretention = $obj->{'backupretention'} || $backupretention;

        my $basepath = "stabile-backup";
        my $bpath = $basepath;
        my $mounts = `/bin/cat /proc/mounts`;
        my $zbackupavailable = (($mounts =~ /$bpath (\S+) zfs/)?$1:'');
        unless ($zbackupavailable) {$postreply .= "Status=OK ZFS backup not available, only doing local snapshots\n";}
        my $zfscmd = "zfs";
        my $macip;
        my $ipath = $spools[0]->{'zfs'} || 'stabile-images/images';
        my @nspools = @spools;
        if (!(defined $obj->{'storagepool'}) || $storagepool == -1) {
            @nspools = () if ($storagepool == -1); # Only do node backups
            unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
#            my $nipath = $ipath;
#            $nipath = "$1/node" if ($nipath =~ /(.+)\/(.+)/);
            my $nipath = 'stabile-node/node';
            foreach my $node (values %nodereg) {
                push @nspools, {
                    mac=>$node->{'mac'},
                    macip=>$node->{'ip'},
                    zfs=>$nipath,
                    id=>-1
                } if ($node->{'stor'} eq 'zfs' && (!$mac || $node->{'mac'} eq $mac))
            }
            untie %nodereg;
        }
        if (`pgrep zfs`) {
            $postreply .= "Status=ERROR Another ZFS backup is running. Please wait a minute...\n";
            $postmsg = "ERROR ERROR Another ZFS backup is running. Please wait a minute...";
            return $postreply;
        }
        $postreply .= "Status=OK Performing ZFS backup on " . (scalar @nspools) . " storage pools with image retention $imageretention, backup retention $backupretention\n";

        foreach my $spool (@nspools) {
            $ipath = $spool->{'zfs'};
            if ($spool->{'id'} == -1) { # We're doing a node backup
                $mac = $spool->{'mac'};
                $macip = $spool->{'macip'};
                $bpath = "$basepath/node-$mac";
            } else {
                next unless ($ipath);
                next if (($storagepool || $storagepool eq '0') && $storagepool ne $spool->{'id'});
                $bpath = "$basepath/$1" if ($ipath =~ /.+\/(.+)/);
                $mac = '';
                $macip = '';
            }
            if ($macip) {$zfscmd = "$sshcmd $macip sudo zfs";}
            else {$zfscmd = "zfs";}

            $postreply .= "Status=OK Commencing ZFS backup of $ipath $macip\n";
            my $res;
            my $cmd;
            my @imagesnaps;
            my @backupsnaps;

            # example: stabile-images/images@SNAPSHOT-20200524172901
            $cmd = qq/$zfscmd list -t snapshot | grep '$ipath'/;
            my $snaplist = `$cmd`;
            my @snaplines = split("\n", $snaplist);
            foreach my $snap (@snaplines) {
                push @imagesnaps, $2 if ($snap =~ /(.*)\@SNAPSHOT-(\d+)/);
            }
            if ($zbackupavailable) {
                $cmd = qq/zfs list -t snapshot | grep '$bpath'/;
                $snaplist = `$cmd`;
                @snaplines = split("\n", $snaplist);
                foreach my $snap (@snaplines) {
                    push @backupsnaps, $2 if ($snap =~ /(.*)\@SNAPSHOT-(\d+)/);
                }
            }
        # Find matching snapshots
            my $matches=0;
            my $matchbase = 0;
            foreach my $bsnap (@backupsnaps) {
                if ($bsnap eq $imagesnaps[$matchbase + $matches]) { # matching snapshot found
                    $matches++;
                } elsif ($matches) { # backup snapshots are ahead of image snapshots - correct manually, i.e. delete them.
                    $postreply .= "Status=ERROR Snapshots are out of sync.\n";
                    $postmsg = "ERROR Snapshots are out of sync";
                    $main::syslogit->($user, 'info', "ERROR snapshots of $ipath and $bpath are out of sync.");
                    return $postreply;
                } elsif (!$matchbase) { # Possibly there are image snapshots older than there are backup snapshots, find the match base i.e. first match in @imagesnaps
                    my $mb=0;
                    foreach my $isnap (@imagesnaps) {
                        if ($bsnap eq $isnap) { # matching snapshot found
                            $matchbase = $mb;
                            $matches++;
                            last;
                        }
                        $mb++;
                    }
                }
            }

            my $lastisnap = $imagesnaps[scalar @imagesnaps -1];
            my $lastisnaptime = timelocal($6,$5,$4,$3,$2-1,$1) if ($lastisnap =~ /(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)/);
            my $td = ($current_time - $lastisnaptime);
            if ($td<=5) {
                $postreply .= "Status=ERROR Last backup was taken $td seconds ago. Please wait a minute...\n";
                $postmsg = "ERROR ERROR Last backup was taken $td seconds ago. Please wait a minute...";
                return $postreply;
            }
            my $ni = scalar @imagesnaps;
            my $nb = scalar @backupsnaps;
        # If there are unsynced image snaps - sync them
            if ($zbackupavailable && !$snaponly) {
                if (scalar @imagesnaps > $matches+$matchbase) {
                    for (my $j=$matches+$matchbase; $j < scalar @imagesnaps; $j++) {
                        if ($macip) {
                            $cmd = qq[$zfscmd "send -i $ipath\@SNAPSHOT-$imagesnaps[$j-1] $ipath\@SNAPSHOT-$imagesnaps[$j] | ssh 10.0.0.1 sudo zfs receive $bpath"]; # -R
                        } else {
                            $cmd = qq[zfs send -i $ipath\@SNAPSHOT-$imagesnaps[$j-1] $ipath\@SNAPSHOT-$imagesnaps[$j] | zfs receive $bpath]; # -R
                        }
                        $res = `$cmd 2>&1`;
                        unless ($res && !$macip) { # ssh will warn about adding to list of known hosts
                            $matches++;
                            $nb++;
                        }
                        $postreply .= "Status=OK Sending ZFS snapshot $imagesnaps[$j-1]->$imagesnaps[$j] of $macip $ipath to $bpath $res\n";
                        $main::syslogit->($user, 'info', "OK Sending ZFS snapshot $imagesnaps[$j-1]->$imagesnaps[$j] of $macip $ipath to $bpath $res");
                    }
                }
            }
            $res = '';

            if ($matches && !$synconly) { # snapshots are in sync
        # Then perform the actual snapshot
                my $snap1 = sprintf "%4d%02d%02d%02d%02d%02d",$year,$mon+1,$mday,$hour,$min,$sec;
                my $oldsnap = $imagesnaps[$matches+$matchbase-1];
                $cmd = qq|$zfscmd snapshot -r $ipath\@SNAPSHOT-$snap1|;
                $postreply .= "Status=OK Performing ZFS snapshot with $matches matches and base $matchbase $res\n";
                $res = `$cmd 2>&1`;
                unless ($res && !$macip) {
                    $ni++;
                    push @imagesnaps, $snap1;
                }
        # Send it to backup if asked to
                unless ($snaponly || !$zbackupavailable) {
                    if ($macip) {
                        $cmd = qq[$zfscmd "send -i $ipath\@SNAPSHOT-$oldsnap $ipath\@SNAPSHOT-$snap1 | ssh 10.0.0.1 sudo zfs receive $bpath"];
                    } else {
                        $cmd = qq[zfs send -i $ipath\@SNAPSHOT-$oldsnap $ipath\@SNAPSHOT-$snap1 | zfs receive $bpath]; # -R
                    }
                    $res .= `$cmd 2>&1`;
                    unless ($res && !$macip) {
                        $matches++;
                        $nb++;
                        push @backupsnaps, $snap1;
                    }
                    $postreply .= "Status=OK Sending ZFS snapshot of $macip $ipath $oldsnap->$snap1 to $bpath $res\n";
                    $main::syslogit->($user, 'info', "OK Sending ZFS snapshot of $macip $ipath $oldsnap->$snap1 to $bpath $res");
                }
                $postreply .= "Status=OK Synced $matches ZFS snapshots. There are now $ni image snapshots, $nb backup snapshots.\n";
            } elsif ($matches) {
                $postreply .= "Status=OK Synced $matches ZFS snapshots. There are $ni image snapshots, $nb backup snapshots.\n";
#            } elsif ($ni==0 && $nb==0) { # We start from a blank slate
            } elsif ($nb==0) { # We start from a blank slate
                my $snap1 = sprintf "%4d%02d%02d%02d%02d%02d",$year,$mon+1,$mday,$hour,$min,$sec;
                $cmd = qq|$zfscmd snapshot -r $ipath\@SNAPSHOT-$snap1|;
                $res = `$cmd 2>&1`;
                $postreply .= "Status=OK Performing ZFS snapshot $res $macip\n";
        # Send it to backup by creating new filesystem
                unless ($snaponly || !$zbackupavailable) {
                    if ($macip) {
                        $cmd = qq[$zfscmd "send $ipath\@SNAPSHOT-$snap1 | ssh 10.0.0.1 sudo zfs receive $bpath"];
                        $res .= `$cmd 2>&1`;
                        $cmd = qq|zfs set readonly=on $bpath|;
                        $res .= `$cmd 2>&1`;
                        $cmd = qq|zfs mount $bpath|;
                        $res .= `$cmd 2>&1`;
                    } else {
                        $cmd = qq[zfs send -R $ipath\@SNAPSHOT-$snap1 | zfs receive $bpath];
                        $res .= `$cmd 2>&1`;
                    }
                    $postreply .= "Status=OK Sending complete ZFS snapshot of $macip:$ipath\@$snap1 to $bpath $res\n";
                    $main::syslogit->($user, 'info', "OK Sending complete ZFS snapshot of $macip:$ipath\@$snap1 to $bpath $res");
                    $matches++;
                    $nb++;
                }
                $ni++;
                $postreply .= "Status=OK Synced ZFS snapshots. There are $ni image snapshots, $nb backup snapshots.\n";
            } else {
                $postreply .= "Status=ERROR Unable to sync snapshots.\n";
                $postmsg = "ERROR Unable to sync snapshots";
            }
            my $i=0;
        # Purge image snapshots if asked to
            if ($imageretention && $matches>1) {
                my $rtime;
                if ($imageretention =~ /(\d+)(s|h|d)/) {
                    $rtime = $1;
                    $rtime = $1*60*60 if ($2 eq 'h');
                    $rtime = $1*60*60*24 if ($2 eq 'd');
                    $postreply .= "Status=OK Keeping image snapshots newer than $imageretention out of $ni.\n";
                } elsif ($imageretention =~ /(\d+)$/) {
                    $postreply .= "Status=OK Keeping " . (($imageretention>$ni)?$ni:$imageretention) . " image snapshots out of $ni.\n";
                } else {
                    $imageretention = 0;
                }
                if ($imageretention) {
                    foreach my $isnap (@imagesnaps) {
                        my $purge;
                        if ($rtime) {
                            my $snaptime = timelocal($6,$5,$4,$3,$2-1,$1) if ($isnap =~ /(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)/);
                            my $tdiff = ($current_time - $snaptime);
                            if ( $matches>1 && $tdiff>$rtime )
                                {$purge = 1;}
                            else
                                {last;}
                        } else { # a simple number was specified
#                            if ( $matches>1 && $matches+$matchbase>$imageretention )
                            if ( $matches>1 && $ni>$imageretention )
                                {$purge = 1;}
                            else
                                {last;}
                        }
                        if ($purge) {
                            $cmd = qq|$zfscmd destroy $ipath\@SNAPSHOT-$isnap|;
                            $res = `$cmd 2>&1`;
                            $postreply .= "Status=OK Purging image snapshot $isnap from $ipath.\n";
                            $main::syslogit->($user, 'info', "OK Purging image snapshot $isnap from $ipath");
                            $matches-- if ($i>=$matchbase);
                            $ni--;
                        }
                        $i++;
                    }
                }
            }
            # Purge backup snapshots if asked to
            if ($backupretention && $matches) {
                my $rtime;
                if ($backupretention =~ /(\d+)(s|h|d)/) {
                    $rtime = $1;
                    $rtime = $1*60*60 if ($2 eq 'h');
                    $rtime = $1*60*60*24 if ($2 eq 'd');
                    $postreply .= "Status=OK Keeping backup snapshots newer than $backupretention out of $nb.\n";
                } elsif ($backupretention =~ /(\d+)$/) {
                    $postreply .= "Status=OK Keeping " . (($backupretention>$nb)?$nb:$backupretention) . " backup snapshots out of $nb.\n";
                } else {
                    $backupretention = 0;
                }
                if ($backupretention && $zbackupavailable) {
                    foreach my $bsnap (@backupsnaps) {
                        my $purge;
                        if ($bsnap eq $imagesnaps[$matchbase+$matches-1]) { # We need to keep the last snapshot synced
                            $postreply .= "Status=OK Not purging backup snapshot $matchbase $bsnap.\n";
                            last;
                        } else {
                            if ($rtime) {
                                my $snaptime = timelocal($6,$5,$4,$3,$2-1,$1) if ($bsnap =~ /(\d\d\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)/);
                                my $tdiff = ($current_time - $snaptime);
                                if ( $matches>1 && $tdiff>$rtime )
                                    {$purge = 1;}
                            } else {
                                if ( $nb>$backupretention )
                                    {$purge = 1;}
                            }
                            if ($purge) {
                                $cmd = qq|zfs destroy $bpath\@SNAPSHOT-$bsnap|;
                                $res = `$cmd 2>&1`;
                                $postreply .= "Status=OK Purging backup snapshot $bsnap from $bpath.\n";
                                $main::syslogit->($user, 'info', "OK Purging backup snapshot $bsnap from $bpath");
                                $nb--;
                            } else {
                                last;
                            }
                        }
                    }
                }
            }
            $postmsg .= "OK Performing ZFS backup of $bpath. There are $ni image snapshots and $nb backup snapshots. ";
        }
        $postreply .= "Status=OK Updating all btimes\n";
        Updateallbtimes();
    } else {
        $postreply .= "Status=ERROR Not allowed\n";
        $postmsg = "ERROR Not allowed";
    }
    $main::updateUI->({tab=>"images", user=>$user, type=>"message", message=>$postmsg});
    return $postreply;
}

sub Backup {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
Backs an image up.
END
    }
    my $path = $obj->{path};
    my $status = $obj->{status};
    $uistatus = "backingup";
    $uipath = $path;
    my $remolder;
    $remolder = "14D" if ($obj->{bschedule} eq "daily14");;
    $remolder = "7D" if ($obj->{bschedule} eq "daily7");
    if ($status eq "snapshotting" || $status eq "unsnapping" || $status eq "reverting" || $status eq "cloning" ||
        $status eq "moving" || $status eq "converting") {
        $postreply .= "Status=ERROR Problem backing up $obj->{type} image: $obj->{name}\n";
    } elsif ($obj->{regstoragepool} == -1) {
        if (createNodeTask($obj->{mac}, "BACKUP $user $uistatus $status \"$path\" \"$backupdir\" $remolder")) {
            $postreply .= "OK not backingup image: $obj->{name} (on node, node probably asleep)\n";
        } else {
            $register{$path}->{'status'} = $uistatus;
            $uistatus = "lbackingup" if ($status eq "active"); # Do lvm snapshot before backing up
            $main::syslogit->($user, "info", "$uistatus $obj->{type} image: $obj->{name}: $uuid");
            $postreply .= "Status=backingup OK backingup image: $obj->{name} (on node)\n";
        }
    } elsif (!$spools[$obj->{regstoragepool}]->{'rdiffenabled'}) {
        $postreply .= "Status=ERROR Rdiff-backup has not been enabled for this storagepool ($spools[$obj->{regstoragepool}]->{'name'})\n";
    } else {
        if ($spools[$obj->{regstoragepool}]->{'hostpath'} eq "local" && $status eq "active") {
            my $poolpath = $spools[$obj->{regstoragepool}]->{'path'};
            # We only need to worry about taking an LVM snapshot if the image is in active use
            # We also check if the images is actually on an LVM partition
            my $qi = `/bin/cat /proc/mounts | grep "$poolpath"`; # Find the lvm volume mounted on /mnt/images
            ($qi =~ m/\/dev\/mapper\/(\S+)-(\S+) $pool.+/g)[-1]; # Select last match
            my $lvolgroup = $1;
            my $lvol = $2;
            if ($lvolgroup && $lvol) {
                $uistatus = "lbackingup";
            }
        }
        if ($uistatus ne "lbackingup" && $status eq "active") {
            $postreply .= "Status=ERROR Image is not on an LVM partition - suspend before backing up.\n";
            $main::updateUI->({tab=>"images", user=>$user, type=>"update", path=>$path, status=>$uistatus, message=>"Image is not on an LVM partition - suspend before backing up"});
        } else {
            my $buser;
            my $bname;
            if ($path =~ /.*\/(common|$user)\/(.+)/) {
                $buser = $1;
                $bname = $2;
            }
            if ($buser && $bname) {
                my $dirpath = $spools[$obj->{regstoragepool}]->{'path'};
                #chop $dirpath; # Remove last /
                eval {
                    $register{$path}->{'status'} = $uistatus;
                    my $daemon = Proc::Daemon->new(
                        work_dir => '/usr/local/bin',
                        exec_command => "perl -U steamExec $buser $uistatus $status \"$bname\" \"$dirpath\" \"$backupdir\" $remolder"
                    ) or do {$postreply .= "Status=ERROR $@\n";};
                    my $pid = $daemon->Init();
                    $postreply .=  "Status=backingup OK backingup image: $obj->{name}\n";
                    $main::syslogit->($user, "info", "$uistatus $obj->{type} image: $obj->{name}: $bname");
                    1;
                } or do {$postreply .= "Status=ERROR $@\n";}
            } else {
                $postreply .= "Status=ERROR Problem backing up $path\n";
            }
        }
    }
    return $postreply;
}

sub Restore {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
Backs an image up.
END
    }
    my $path = $obj->{path};
    my $status = $obj->{status};
    $uistatus = "restoring";
    my($bname, $dirpath, $suffix) = fileparse($path, (".vmdk", ".img", ".vhd", ".qcow", ".qcow2", ".vdi", ".iso"));
    my $backup = $params{"backup"} || $obj->{backup};
    my $pool = $register{$path}->{'storagepool'};
    $pool = "0" if ($pool == -1);
    my $poolpath = $spools[$pool]->{'path'};
    my $restorefromdir = $backupdir;
    my $inc = $backup;
    my $subdir; # 1 level of subdirs supported
    $subdir = $1 if ($dirpath =~ /.+\/$obj->{user}(\/.+)?\//);

    if ($backup =~ /^SNAPSHOT-(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/) { # We are dealing with a zfs restore
        $inc = "$1-$2-$3-$4-$5-$6";
        foreach my $spool (@spools) {
            my $ppath = $spool->{"path"};
            if (-e "$ppath/.zfs/snapshot/$backup/$obj->{user}$subdir/$bname$suffix") {
                $restorefromdir = "$ppath/.zfs/snapshot/$backup";
                last;
            }
        }
    } else {
        if ($backup eq "mirror") {
            my $mir = `/bin/ls "$backupdir/$obj->{user}/$bname$suffix/rdiff-backup-data" | grep current_mirror`;
            if ($mir =~ /current_mirror\.(\S+)\.data/) {
                $inc = $1;
            }
        }
        $inc =~ tr/:T/-/; # qemu-img does not like colons in file names - go figure...
        $inc = substr($inc,0,-6);
    }
    $uipath = "$poolpath/$obj->{user}$subdir/$bname.$inc$suffix";
    my $i;
    if (-e $uipath) {
        $i = 1;
        while (-e "$poolpath/$obj->{user}$subdir/$bname.$inc.$i$suffix") {$i++;}
        $uipath = "$poolpath/$obj->{user}$subdir/$bname.$inc.$i$suffix";
    }

    if (-e $uipath) {
        $postreply .= "Status=ERROR This image is already being restored\n";
    } elsif ($obj->{user} ne $user && !$isadmin) {
        $postreply .= "Status=ERROR No restore privs\n";
    } elsif (!$backup || $backup eq "--") {
        $postreply .= "Status=ERROR No backup selected\n";
    } elsif (overQuotas($obj->{virtualsize})) {
        $postreply .= "Status=ERROR Over quota (". overQuotas($obj->{virtualsize}) . ") restoring: $obj->{name}\n";
    } elsif (overStorage($obj->{ksize}*1024, $pool+0)) {
        $postreply .= "Status=ERROR Out of storage in destination pool restoring: $obj->{name}\n";
    } else {
        my $ug = new Data::UUID;
        my $newuuid = $ug->create_str();
        $register{$uipath} = {
            uuid=>$newuuid,
            status=>"restoring",
            name=>"$obj->{name} ($inc)" . (($i)?" $i":''),
            notes=>$obj->{notes},
            image2=>$obj->{image2},
            managementlink=>$obj->{managementlink},
            upgradelink=>$obj->{upgradelink},
            terminallink=>$obj->{terminallink},
            size=>0,
            realsize=>0,
            virtualsize=>$obj->{virtualsize},
            type=>$obj->{type},
            user=>$user
        };
        eval {
            $register{$path}->{'status'} = $uistatus;
            my $daemon = Proc::Daemon->new(
                work_dir => '/usr/local/bin',
                exec_command => "perl -U steamExec $obj->{user} $uistatus $status \"$path\" \"$restorefromdir\" \"$backup\" \"$uipath\""
            ) or do {$postreply .= "Status=ERROR $@\n";};
            my $pid = $daemon->Init();
            $postreply .=  "Status=$uistatus OK $uistatus $obj->{type} image: $obj->{name} ($inc)". ($console?", $newuuid\n":"\n");
            $main::syslogit->($user, "info", "$uistatus $obj->{type} image: $obj->{name} ($inc), $uipath, $newuuid: $uuid");
            1;
        } or do {$postreply .= "Status=ERROR $@\n";};
        $main::updateUI->({tab=>"images", user=>$user, type=>"update"});
    }
    return $postreply;
}

sub Master {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
Converts an image to a master image. Image must not be in use.
END
    }
    my $path = $obj->{path};
    my $status = $register{$path}->{status};
    $path =~ /(.+)\.$obj->{type}$/;
    my $namepath = $1;
    my $uiname;
    if (!$register{$path}) {
        $postreply .= "Status=ERROR Image $path not found\n";
    } elsif ($status ne "unused") {
        $postreply .= "Status=ERROR Only unused images may be mastered\n";
    } elsif ($namepath =~ /(.+)\.master/ || $register{$path}->{'master'}) {
        $postreply .= "Status=ERROR Only one level of mastering is supported\n";
    } elsif ($obj->{istoragepool} == -1 || $obj->{regstoragepool} == -1) {
        $postreply .= "Status=ERROR Unable to master $obj->{name} (master images are not supported on node storage)\n";
    } elsif ($obj->{type} eq "qcow2") {
        # Promoting a regular image to master
        # First find an unused path
        if (-e "$namepath.master.$obj->{type}") {
            my $i = 1;
            while ($register{"$namepath.$i.master.$obj->{type}"} || -e "$namepath.$i.master.$obj->{type}") {$i++;};
            $uinewpath = "$namepath.$i.master.$obj->{type}";
        } else {
            $uinewpath = "$namepath.master.$obj->{type}";
        }

        $uipath = $path;
#        $uiname = "$obj->{name} (master)";
        $uiname = "$obj->{name}";
        eval {
            my $qinfo = `/bin/mv -iv "$path" "$uinewpath"`;
            $register{$path}->{'name'} = $uiname;
            $register{$uinewpath} = $register{$path};
            delete $register{$path};
            $postreply .= "Status=$status Mastered $obj->{type} image: $obj->{name}\n";
            chop $qinfo;
            $main::syslogit->($user, "info", $qinfo);
            1;
        } or do {$postreply .= "Status=ERROR $@\n";};
        sleep 1;
        $main::updateUI->({tab=>"images", user=>$user, type=>"update", uuid=>$obj->{'uuid'}, newpath=>$uinewpath, status=>$status, name=>$uiname});
    } else {
        $postreply .= "Status=ERROR Only qcow2 images may be mastered\n";
    }
    return $postreply;
}

sub Unmaster {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:image:
Converts a master image to a regular image. Image must not be in use.
END
    }
    my $path = $obj->{path};
    my $status = $register{$path}->{status};
    $path =~ /(.+)\.$obj->{type}$/;
    my $namepath = $1;
    my $haschildren = 0;
    my $child;
    my $uinewpath;
    my $iname;
    my @regvalues = values %register;
    foreach my $val (@regvalues) {
        if ($val->{'master'} eq $path) {
            $haschildren = 1;
            $child = $val->{'name'};
            last;
        }
    }
    if (!$register{$path}) {
        $postreply .= "Status=ERROR Image $path not found\n";
    } elsif ($haschildren) {
        $postreply .= "Status=Error Cannot unmaster image. This image is used as master by: $child\n";
    } elsif ($status ne "unused" && $status ne "used") {
        $postreply .= "Status=ERROR Only used and unused images may be unmastered\n";
    } elsif (!( ($namepath =~ /(.+)\.master/) || ($obj->{master} && $obj->{master} ne "--")) ) {
        $postreply .= "Status=ERROR You can only unmaster master or child images\n";
    } elsif (($obj->{istoragepool} == -1 || $obj->{regstoragepool} == -1) && $namepath =~ /(.+)\.master/) {
        $postreply .= "Status=ERROR Unable to unmaster $obj->{name} (master images are not supported on node storage)\n";
    } elsif ($obj->{type} eq "qcow2") {
        # Demoting a master to regular image
        if ($namepath =~ /(.+)\.master$/) {
            $namepath = $1;
            $uipath = $path;
            # First find an unused path
            if (-e "$namepath.$obj->{type}") {
                my $i = 1;
                while ($register{"$namepath.$i.$obj->{type}"} || -e "$namepath.$i.$obj->{type}") {$i++;};
                $uinewpath = "$namepath.$i.$obj->{type}";
            } else {
                $uinewpath = "$namepath.$obj->{type}";
            }

            $iname = $obj->{name};
            $iname =~ /(.+)( \(master\))/;
            $iname = $1 if $2;
            eval {
                my $qinfo = `/bin/mv -iv "$path" "$uinewpath"`;
                $register{$path}->{'name'} = $iname;
                $register{$uinewpath} = $register{$path};
                delete $register{$path};
                $postreply .=  "Status=$status Unmastered $obj->{type} image: $obj->{name}\n";
                chomp $qinfo;
                $main::syslogit->($user, "info", $qinfo);
                1;
            } or do {$postreply .= "Status=ERROR $@\n";}
    # Rebasing a child image
        } elsif ($obj->{master} && $obj->{master} ne "--") {
            $uistatus = "rebasing";
            $uipath = $path;
            $iname = $obj->{name};
            $iname =~ /(.+)( \(child\d*\))/;
            $iname = $1 if $2;
            my $temppath = "$path.temp";
            $uipath = $path;
            $uimaster = "--";
            my $macip;

            if ($obj->{mac} && $path =~ /\/mnt\/stabile\/node\//) {
                unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
                $macip = $nodereg{$obj->{mac}}->{'ip'};
                untie %nodereg;
            }
            eval {
                my $master = $register{$path}->{'master'};
                my $usedmaster = '';
#                @regvalues = values %register;
                if ($master && $master ne '--') {
                    foreach my $valref (@regvalues) {
                        $usedmaster = 1 if ($valref->{'master'} eq $master && $valref->{'path'} ne $path); # Check if another image is also using this master
                    }
                }
                $main::updateUI->({tab=>"images", user=>$user, type=>"update", uuid=>$obj->{'uuid'}, status=>$uistatus});
                $register{$path} = {
                    master=>"",
                    name=>"$iname",
                    notes=>$obj->{notes},
                    status=>$uistatus,
                    snap1=>$obj->{snap1},
                    managementlink=>$obj->{managementlink},
                    upgradelink=>$obj->{upgradelink},
                    terminallink=>$obj->{terminallink},
                    image2=>$obj->{image2},
                    storagepool=>$obj->{istoragepool},
                    status=>$uistatus
                };

                if ($macip) {
                    my $esc_localpath = shell_esc_chars($path);
                    my $esc_localpath2 = shell_esc_chars($temppath);
                    $res .= `$sshcmd $macip "/usr/bin/qemu-img convert $esc_localpath -O qcow2 $esc_localpath2"`;
                    $res .= `$sshcmd $macip "if [ -f $esc_localpath2 ]; then /bin/mv -v $esc_localpath2 $esc_localpath; fi"`;
                } else {
                    $res .= `/usr/bin/qemu-img convert -O qcow2 "$path" "$temppath"`;
                    $res .= `if [ -f "$temppath" ]; then /bin/mv -v "$temppath" "$path"; fi`;
                }
                if ($master && !$usedmaster) {
                    $register{$master}->{'status'} = 'unused';
                    $main::syslogit->('info', "Freeing master $master");
                }
                $register{$path}->{'master'} = '';
                $register{$path}->{'status'} = $status;

                $postreply .= "Status=OK $uistatus $obj->{type} image: $obj->{name}\n";
                $main::updateUI->({tab=>"images", user=>$user, type=>"update", uuid=>$obj->{'uuid'}, status=>$status});
                $main::syslogit->($user, "info", "$uistatus $obj->{type} image: $obj->{name}: $uuid");
                1;
            } or do {$postreply .= "Status=ERROR $@\n";}
        } else {
            $postreply .= "Status=ERROR Not a master, not a child \"$obj->{name}\"\n";
        }
        sleep 1;
        $main::updateUI->({tab=>"images", user=>$user, type=>"update", uuid=>$obj->{'uuid'}, newpath=>$uinewpath, name=>$iname, status=>$status});
    } else {
        $postreply .= "Status=ERROR Only qcow2 images may be unmastered\n";
    }
    return $postreply;
}

# Save or create new image
sub Save {
    my ($img, $action, $obj) = @_;
    if ($help) {
        return <<END
POST:path, uuid, name, type, virtualsize, storagepool, user:
To save a collection of images you either PUT or POST a JSON array to the main endpoint with objects representing the images with the changes you want.
Depending on your privileges not all changes are permitted. If you save without specifying a uuid or path, a new image is created.
END
    }
    my $path = $obj->{path};
    my $uuid = $obj->{uuid};
    my $status = $obj->{status};
    if ($status eq "new") {
        # Create new image
        my $ug = new Data::UUID;
        if (!$uuid || $uuid eq '--') {
            $uuid = $ug->create_str();
        } else { # Validate
            my $valuuid  = $ug->from_string($uuid);
            if ($ug->to_string($valuuid) eq $uuid) {
                ;
            } else {
                $uuid = $ug->create_str();
            }
        }
        my $newuuid = $uuid;
        my $pooldir = $spools[$obj->{storagepool}]->{'path'};
        my $cmd;
        my $name = $obj->{name};
        $name =~ s/\./_/g; # Remove unwanted chars
        $name =~ s/\//_/g;
        eval {
            my $ipath = "$pooldir/$user/$name.$obj->{type}";
            $obj->{type} = "qcow2" unless ($obj->{type});
            # Find an unused path
            if ($register{$ipath} || -e "$ipath") {
                my $i = 1;
                while ($register{"$pooldir/$user/$name.$i.$obj->{type}"} || -e "$pooldir/$user/$name.$i.$obj->{type}") {$i++;};
                $ipath = "$pooldir/$user/$name.$i.$obj->{type}";
                $name = "$name.$i";
            }

            if ($obj->{type} eq 'qcow2' || $obj->{type} eq 'vmdk') {
                my $size = ($obj->{msize})."M";
                my $format = "qcow2";
                $format = "vmdk" if ($path1 =~ /\.vmdk$/);
                $cmd = qq|/usr/bin/qemu-img create -f $format "$ipath" "$size"|;
            } elsif ($obj->{type} eq 'img') {
                my $size = ($obj->{msize})."M";
                $cmd = qq|/usr/bin/qemu-img create -f raw "$ipath" "$size"|;
            } elsif ($obj->{type} eq 'vdi') {
                my $size = $obj->{msize};
                $cmd = qq|/usr/bin/VBoxManage createhd --filename "$ipath" --size "$size" --format VDI|;
            }

            $obj->{name} = 'New Image' if (!$obj->{name} || $obj->{name} eq '--' || $obj->{name} =~ /^\./ || $obj->{name} =~ /\//);
            if (-e $ipath) {
                $postreply .= "Status=ERROR Image already exists: \"$obj->{name}\" in \"$ipath\”\n";
            } elsif (overQuotas($obj->{ksize}*1024)) {
                $postreply .= "Status=ERROR Over quota (". overQuotas($obj->{ksize}*1024) . ") creating: $obj->{name}\n";
                $main::updateUI->({tab=>"images", user=>$user, type=>"message", message=>"Over quota in storage pool $obj->{storagepool}"});
                $main::syslogit->($user, "info", "Over quota in storage pool $obj->{storagepool}, not creating $obj->{type} image $obj->{name}");
            } elsif (overStorage($obj->{ksize}*1024, $obj->{storagepool}+0)) {
                $postreply .= "Status=ERROR Out of storage in destination pool creating: $obj->{name}\n";
                $main::updateUI->({tab=>"images", user=>$user, type=>"update", message=>"Out of storage in storage pool $obj->{storagepool}"});
                $main::syslogit->($user, "info", "Out of storage in storage pool $obj->{storagepool}, not creating $obj->{type} image $obj->{name}");
            } elsif ($obj->{virtualsize} > 10*1024*1024 && $obj->{name} && $obj->{name} ne '--') {
                $register{$ipath} = {
                    uuid=>$newuuid,
                    name=>$obj->{name},
                    user=>$user,
                    notes=>$obj->{notes},
                    type=>$obj->{type},
                    size=>0,
                    realsize=>0,
                    virtualsize=>$obj->{virtualsize},
                    storagepool=>$spools[0]->{'id'},
                    created=>$current_time,
                    managementlink=>$obj->{managementlink},
                    upgradelink=>$obj->{upgradelink},
                    terminallink=>$obj->{terminallink},
                    status=>"creating"
                };
                $uipath = $ipath;
                my $res = `$cmd`;
                $register{$ipath}->{'status'} = 'unused';

                $postreply .= "Status=OK Created $obj->{type} image: $obj->{name}\n";
                $postreply .= "Status=OK uuid: $newuuid\n"; # if ($console || $api);
                $postreply .= "Status=OK path: $ipath\n"; # if ($console || $api);
                sleep 1; # Needed to give updateUI a chance to reload
                $main::updateUI->({tab=>"images", uuid=>$newuuid, user=>$user, type=>"update", name=>$obj->{name}});
                $main::syslogit->($user, "info", "Created $obj->{type} image: $obj->{name}: $newuuid");
                updateBilling("New image");
            } else {
                $postreply .= "Status=ERROR Problem creating image: $obj->{name} of size $obj->{virtualsize}\n";
            }
            1;
        } or do {$postreply .= "Status=ERROR $@\n";}
    } else {
    # Moving images because of owner change or storagepool change
        if ($obj->{user} ne $obj->{reguser} || $obj->{storagepool} ne $obj->{regstoragepool}) {
            $uipath = Move($path, $obj->{user}, $obj->{storagepool}, $obj->{mac});
    # Resize a qcow2 image
        } elsif ($obj->{virtualsize} != $register{$path}->{'virtualsize'} &&
            ($obj->{user} eq $obj->{reguser} || index($privileges,"a")!=-1)) {
            if ($status eq "active" || $status eq "paused") {
                $postreply .= "Status=ERROR Cannot resize active images $path, $status.\n";
                $main::updateUI->({tab=>"images", user=>$user, type=>"update", status=>'ERROR', message=>"ERROR Cannot resize active images"});
            } elsif ($obj->{type} eq "qcow2" || $obj->{type} eq "img") {
                if ($obj->{virtualsize} < $register{$path}->{'virtualsize'}) {
                    $postreply .= "Status=ERROR Only growing of images supported.\n";
                } elsif (overQuotas($obj->{virtualsize}, ($register{$path}->{'storagepool'}==-1))) {
                    $postreply .= "Status=ERROR Over quota (". overQuotas($obj->{virtualsize}, ($register{$path}->{'storagepool'}==-1)) . ") resizing: $obj->{name}\n";
                } elsif (overStorage(
                    $obj->{virtualsize},
                    $register{$path}->{'storagepool'},
                    $register{$path}->{'mac'}
                )) {
                    $postreply .= "Status=ERROR Not enough storage ($obj->{virtualsize}) in destination pool $obj->{storagepool} resizing: $obj->{name}\n";
                } else {
                    $uistatus = "resizing";
                    $uipath = $path;
                    my $mpath = $path;
                    if ($obj->{mac} && $obj->{mac} ne '--') {
                        unless ( tie(%nodereg,'Tie::DBI', Hash::Merge::merge({table=>'nodes', key=>'mac', CLOBBER=>1}, $Stabile::dbopts)) ) {return 0};
                        $macip = $nodereg{$obj->{mac}}->{'ip'};
                        untie %nodereg;
                    }
                    $mpath = "$macip:$mpath" if ($macip && $macip ne '--');
                    $register{$path}->{'status'} = $uistatus;
                    $register{$path}->{'virtualsize'} = $obj->{virtualsize};
                    my $cmd = qq|steamExec $user $uistatus $status "$mpath" "$obj->{ksize}"|;
                    if ($action eq 'sync_save') { # We wait for result
                        my $res = `$cmd`;
                        $res =~ s/\n/ /g; $res = lc $res;
                        $postreply .= "Status=OK $res\n";
                    } else {
                        my $daemon = Proc::Daemon->new(
                            work_dir => '/usr/local/bin',
                            exec_command => $cmd,
#                            exec_command => "suidperl -U steamExec $user $uistatus $status \"$mpath\" \"$obj->{ksize}\""
                        ) or do {$postreply .= "Status=ERROR $@\n";};
                        my $pid = $daemon->Init();
                    }
                    $postreply .=  "Status=OK $uistatus $obj->{type} image: $obj->{name} ($obj->{ksize}k)\n";
                    $main::syslogit->($user, "info", "$uistatus $obj->{type} image $obj->{name} $uuid $mpath ($obj->{virtualsize})");
                }
            } else {
                $postreply .= "Status=ERROR Can only resize .qcow2 and .img images.\n";
            }
        } else {
            # Regular save
            if ($obj->{user} eq $obj->{reguser} || $isadmin) {
                my $qinfo;
                my $e;
                $obj->{bschedule} = "" if ($obj->{bschedule} eq "--");
                if ($obj->{bschedule}) {
                    # Remove backups
                    if ($obj->{bschedule} eq "none" && $spools[$obj->{regstoragepool}]->{'rdiffenabled'}) {
                        my($bname, $dirpath) = fileparse($path);
                        if ($path =~ /\/($user|common)\/(.+)/) {
                            my $buser = $1;
                            if (-d "$backupdir/$buser/$bname" && $backupdir && $bname && $buser) {
                                eval {
                                    $qinfo = `/bin/rm -rf "$backupdir/$buser/$bname"`;
                                    1;
                                } or do {$postreply .= "Status=ERROR $@\n"; $e=1;};
                                if (!$e) {
                                    $postreply .=  "Status=OK Removed all backups of $obj->{name}\n";
                                    chomp $qinfo;
                                    $register{$path} = {backupsize=>0};
                                    $main::syslogit->($user, "info", "Removed all backups of $obj->{name}: $path: $qinfo");
                                    $main::updateUI->({
                                        user=>$user,
                                        message=>"Removed all backups of $obj->{name}",
                                        backup=>$path
                                    });
                                    updateBilling("no backup $path");
                                    delete $register{$path}->{'btime'};
                                }
                            }
                        }
                        $obj->{bschedule} = "manually";
                        $register{$path}->{'bschedule'} = $obj->{bschedule};
                    }
                }

                $register{$path} = {
                    name=>$obj->{name},
                    user=>$obj->{user},
                    notes=>$obj->{notes},
                    bschedule=>$obj->{bschedule},
                    installable=>$obj->{installable},
                    managementlink=>$obj->{managementlink},
                    upgradelink=>$obj->{upgradelink},
                    terminallink=>$obj->{terminallink},
                    action=>""
                };
                my $domains = $register{$path}->{'domains'};
                if ($status eq 'downloading') {
                    unless (`pgrep $obj->{name}`) { # Check if image is in fact being downloaded
                        $status = 'unused';
                        $register{$path}->{'status'} = $status;
                        unlink ("$path.meta") if (-e "$path.meta");
                    }
                }
                elsif ($status ne 'unused') {
                    my $match;
                    if ($path =~ /\.master\.qcow2$/) {
                        my @regkeys = (tied %register)->select_where("master = '$path'");
                        $match = 2 if (@regkeys);
                    } else {
                        if (!$domreg{$domains}) { # Referenced domain no longer exists
                            ;
                        } else { # Verify if referenced domain still uses image
                            my @imgkeys = ('image', 'image2', 'image3', 'image4');
                            for (my $i=0; $i<4; $i++) {
                                $match = 1 if ($domreg{$domains}->{$imgkeys[$i]} eq $path);
                            }
                        }
                    }
                    unless ($match) {
                        $status = 'unused';
                        $register{$path}->{'status'} = $status;
                    }
                }
                if ($status eq 'unused') {
                    delete $register{$path}->{'domains'};
                    delete $register{$path}->{'domainnames'};
                }
                $uipath = $path;
                $postreply .= "Status=OK Saved $obj->{name} ($uuid)\n";
            } else {
                $postreply .= "Status=ERROR Unable to save $obj->{name}\n";
            }
        }
    }
    if ($postreply) {
        $postmsg = $postreply;
    } else {
        $postreply = to_json(\%{$register{$uipath}}, {pretty=>1}) if ($uipath);
        $postreply =~ s/""/"--"/g;
        $postreply =~ s/null/"--"/g;
        $postreply =~ s/"notes" {0,1}: {0,1}"--"/"notes":""/g;
        $postreply =~ s/"installable" {0,1}: {0,1}"(true|false)"/"installable":$1/g;
    }
    return $postreply;
}

sub Setstoragedevice {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:device,type:
Changes the device - disk or partition, used for images or backup storage.
[type] is either images or backup.
END
    }
    my $dev = $obj->{device};
    my $force = $obj->{force};
    my $type = 'backup';
    $type = 'images' if ($obj->{type} eq 'images');
    return "Status=Error Not allowed\n" unless ($isadmin);
    my $backupdevice = Getbackupdevice('', 'getbackupdevice');
    my $imagesdevice = Getimagesdevice('', 'getimagesdevice');
    my $devices_obj = from_json(Liststoragedevices('', 'liststoragedevices'));
    my %devices = %$devices_obj;
    my $backupdev = $devices{$backupdevice}->{dev};
    my $imagesdev = $devices{$imagesdevice}->{dev};
    if (!$devices{$dev}) {
        $postreply = "Status=Error You must specify a valid device ($dev)\n";
        return $postreply;
    }
    if (!$force && (($backupdev =~ /$dev/) || ($imagesdev =~ /$dev/))  && $dev !~ /vda/ && $dev !~ /sda/) { # make exception to allow returning to default setup
        $postreply = "Status=Error $dev is already in use as images or backup device\n";
        return $postreply;
    }
    my $stordir = $tenderpathslist[0];
    my $stordevice = $imagesdevice;
    if ($type eq 'backup') {
        $stordir = $backupdir;
        $stordevice = $backupdevice;
    }
    return "Status=Error Storage device not found\n" unless ($stordevice);
    my $mp = $devices{$dev}->{mounted};
    my $newstordir;
    # my $oldstordir;
    if ($devices{$dev}->{type} eq 'zfs') {
        my $cmd = qq|zfs list stabile-$type/$type -Ho mountpoint|;
        my $zmp = `$cmd`;
        chomp $zmp;
        if ($zmp =~ /^\//) {
            `zfs mount stabile-$type/$type`;
            $mp = $zmp;
            $newstordir = $mp;
        } else {
            `zfs create stabile-$type/$type`;
            $mp = "/stabile-$type/$type";
            $newstordir = $mp;
        }
    } else {
        $newstordir = (($type eq 'images')?"$mp/images":"$mp/backups");
        $newstordir = $1 if ($newstordir =~ /(.+\/images)\/images$/);
        $newstordir = $1 if ($newstordir =~ /(.+\/backups)\/backups$/);
    }
    if ($mp eq '/') {
        $newstordir = (($type eq 'images')?"/mnt/stabile/images":"/mnt/stabile/backups");
        `umount "$newstordir"`; # in case it's mounted
    }
    `mkdir "$newstordir"` unless (-e $newstordir);
    `chmod 777 "$newstordir"`;

    my $cfg = new Config::Simple("/etc/stabile/config.cfg");
    if ($type eq 'backup') {
        $cfg->param('STORAGE_BACKUPDIR', $newstordir);
        $cfg->save();
    } elsif ($type eq 'images') {

    # Handle shared storage config
    #    $oldstordir = $stordir;
        my $i = 0;
        for($i = 0; $i <= $#tenderpathslist; $i++) {
            my $dir = $tenderpathslist[$i];
            last if ($dir eq $newstordir);
        }
        # $tenderpathslist[0] = $newstordir;
        splice(@tenderpathslist, $i,1); # Remove existing entry
        unshift(@tenderpathslist, $newstordir); # Then add the new path
        $cfg->param('STORAGE_POOLS_LOCAL_PATHS', join(',', @tenderpathslist));

        # $tenderlist[0] = 'local';
        splice(@tenderlist, $i,1);
        unshift(@tenderlist, 'local');
        $cfg->param('STORAGE_POOLS_ADDRESS_PATHS', join(',', @tenderlist));

        # $tendernameslist[0] = 'Default';
        splice(@tendernameslist, $i,1);
        unshift(@tendernameslist, 'Default');

        if ($i) { # We've actually changed storage device
            my $oldstorname = $tenderpathslist[1];
            $oldstorname = $1 if ($oldstorname =~ /.*\/(.+)/);
            $tendernameslist[1] = "$oldstorname on $imagesdevice"; # Give the previous default pool a fitting name

            $storagepools = "$storagepools,$i" unless ($storagepools =~ /,\s*$i,?/ || $storagepools =~ /,\s*$i$/ || $storagepools =~ /^$i$/);
            $cfg->param('STORAGE_POOLS_DEFAULTS', $storagepools);
        }
        $cfg->param('STORAGE_POOLS_NAMES', join(',', @tendernameslist));

        $cfg->save();


    # Handle node storage configs
        unless ( tie(%idreg,'Tie::DBI', Hash::Merge::merge({table=>'nodeidentities',key=>'identity',CLOBBER=>3}, $Stabile::dbopts)) ) {return "Unable to access id register"};
        # Build hash of known node config files
        my @nodeconfigs;
        push @nodeconfigs, "/etc/stabile/nodeconfig.cfg";
        foreach my $valref (values %idreg) {
            my $nodeconfigfile = $valref->{'path'} . "/casper/filesystem.dir/etc/stabile/nodeconfig.cfg";
            next if ($nodeconfigs{$nodeconfigfile}); # Node identities may share basedir and node config file
            if (-e $nodeconfigfile) {
                push @nodeconfigs, $nodeconfigfile;
            }
        }
        untie %idreg;
        foreach my $nodeconfig (@nodeconfigs) {
            my $nodecfg = new Config::Simple($nodeconfig);
            my @ltenderlist = $nodecfg->param('STORAGE_SERVERS_ADDRESS_PATHS');
            my $ltenders = join(", ", @ltenderlist);
            next if ($ltenders =~ /10\.0\.0\.1:$newstordir$/ || $ltenders =~ /10\.0\.0\.1:$newstordir,/); # This entry already exists
            #my @ltenderlist = split(/,\s*/, $ltenders);
            #$ltenderlist[0] = "10.0.0.1:$newstordir";
            unshift(@ltenderlist, "10.0.0.1:$newstordir");
            $nodecfg->param('STORAGE_SERVERS_ADDRESS_PATHS', join(',', @ltenderlist));
            my @ltenderpathslist = $nodecfg->param('STORAGE_SERVERS_LOCAL_PATHS');
            my $ltenderpaths = join(", ", @ltenderpathslist);
            #my @ltenderpathslist = split(/,\s*/, $ltenderpaths);
            #$ltenderpathslist[0] = $newstordir;
            unshift(@ltenderpathslist, $newstordir);
            $nodecfg->param('STORAGE_SERVERS_LOCAL_PATHS', join(',', @ltenderpathslist));
            $nodecfg->save();
        }
        unless (`grep "$newstordir 10" /etc/exports`) {
            `echo "$newstordir 10.0.0.0/255.255.255.0(sync,no_subtree_check,no_root_squash,rw)" >> /etc/exports`;
            `/usr/sbin/exportfs -r`; #Reexport nfs shares
        }
# We no longer undefine storage pools - we add them
#        $oldstordir =~ s/\//\\\//g;
#        `perl -pi -e 's/$oldstordir 10.*\\\n//s;' /etc/exports` if ($oldstordir);

        `mkdir "$newstordir/common"` unless (-e "$newstordir/common");
        `cp "$stordir/ejectcdrom.xml" "$newstordir/ejectcdrom.xml"` unless (-e "$newstordir/ejectcdrom.xml");
        `cp "$stordir/mountvirtio.xml" "$newstordir/mountvirtio.xml"` unless (-e "$newstordir/mountvirtio.xml");
        `cp "$stordir/dummy.qcow2" "$newstordir/dummy.qcow2"` unless (-e "$newstordir/dummy.qcow2");
    }
    Updatedownloads();

    # Update /etc/stabile/cgconfig.conf
    my $devs = $devices{$dev}->{dev};
    my @pdevs = split(" ", $devs);
    my $majmins;
    foreach my $dev (@pdevs) {
        # It seems that cgroups cannot handle individual partitions for blkio
        my $physdev = $1 if ($dev =~ /(\w+)\d+/);
        if ($physdev && -d "/sys/fs/cgroup" ) {
            my $blkline = `lsblk -l /dev/$physdev`;
            my $majmin = '';
            $majmin = $1 if ($blkline =~ /$physdev +(\d+:\d+)/);
            $postreply .= "Status=OK Setting cgroups block device to $majmin\n";
            if ($majmin) {
                $majmins .= ($majmins)?" $majmin":$majmin;
            }
        }
    }
    setCgroupsBlkDevice($majmins) if ($majmins);

    $Stabile::Nodes::console = 1;
    require "$Stabile::basedir/cgi/nodes.cgi";
    $postreply .= Stabile::Nodes::do_reloadall('','reloadall');

    # Update config on stabile.io
    require "$Stabile::basedir/cgi/users.cgi";
    $Stabile::Users::console = 1;
    Stabile::Users::Updateengine('', 'updateengine');

    my $msg = "OK Now using $newstordir for $type on $obj->{device}";
    $main::updateUI->({tab=>'home', user=>$user, type=>'update', message=>$msg});
    $postreply .= "Status=OK Now using $newstordir for $type on $dev\n";
    return $postreply;
}

sub Initializestorage {
    my ($image, $action, $obj) = @_;
    if ($help) {
        return <<END
GET:device,type,fs,activate,force:
Initializes a local disk or partition, and optionally formats it with ZFS and creates a ZFS pool to use as image storage or backup storage.
[device] is a local disk device in /dev like e.g. 'sdd'. [type] may be either 'images' (default) or 'backup'. [fs] may be 'lvm' (default) or 'zfs'.
Set [activate] if you want to put the device into use immediately. Set [force] if you want to destroy existing ZFS pool and recreate (obviously use with care).
END
    }
    my $fs = $obj->{fs} || 'zfs';
    my $dev = $obj->{device};
    my $force = $obj->{force};
    my $activate = $obj->{activate};
    my $type = 'backup';
    $type = 'images' if ($obj->{type} eq 'images');
    return "Status=Error Not allowed\n" unless ($isadmin);
    my $backupdevice = Getbackupdevice('', 'getbackupdevice');
    my $imagesdevice = Getimagesdevice('', 'getimagesdevice');
    my $devices_obj = from_json(Liststoragedevices('', 'liststoragedevices'));
    my %devices = %$devices_obj;
    my $backupdev = $devices{$backupdevice}->{dev};
    my $imagesdev = $devices{$imagesdevice}->{dev};
    if (!$dev || !(-e "/dev/$dev")) {
        $postreply = "Status=Error You must specify a valid device\n";
        return $postreply;
    }
    if (($backupdev =~ /$dev/) || ($imagesdev =~ /$dev/)) {
        $postreply = "Status=Error $dev is already in use as images or backup device\n";
        return $postreply;
    }
    my $stordir = "/stabile-$type/$type";
    if ($fs eq 'lvm') {
        if ($type eq 'backup') {
            $stordir = "/mnt/stabile/backups";
        } else {
            $stordir = "/mnt/stabile/images";
        }
    }
    `chmod 666 /dev/zfs` if (-e '/dev/zfs'); # TODO: This should be removed once we upgrade to Bionic and zfs allow is supported

    my $vol = $type . "vol";
    my $mounts = `cat /proc/mounts`;
    my $zpools = `zpool list -v`;
    my $pvs = `pvdisplay -c`;
    my $z;
    $postreply = '';
    # Unconfigure existing zfs or lvm if $force and zfs/lvm configured or device is in use by either
    if ($zpools =~ /stabile-$type/ || $mounts =~ /dev\/mapper\/stabile$type/ || $zpools =~ /$dev/ || $pvs =~ /$dev/) {
        if ($fs eq 'zfs' || $zpools =~ /$dev/) {
            if ($force) { # ZFS needs to be unconfigured
                my $umount = `LANG=en_US.UTF-8 umount -v "/stabile-$type/$type" 2>&1`;
                unless ($umount =~ /(unmounted|not mounted|no mount point)/) {
                    $postreply .= "Status=Error Unable to unmount zfs $type storage on $dev - $umount\n";
                    return $postreply;
                }
                `umount "/stabile-$type"`;
                my $res = `zpool destroy "stabile-$type" 2>&1`;
                chomp $res;
                $postreply .= "Status=OK Unconfigured zfs - $res\n";
            } else {
                $postreply .= "Status=Error ZFS is already configured for $type\n";
                $z = 1;
            #    return $postreply;
            }
        }
        if ($fs eq 'lvm' || $pvs =~ /$dev/) {
            if ($force) {
                my $udir = (($type eq 'backup')?"/mnt/stabile/backups":"/mnt/stabile/images");
                my $umount = `umount -v "$udir" 2>&1`;
                unless ($umount =~ /unmounted|not mounted|no mount point/) {
                    $postreply .= "Status=Error Unable to unmount lvm $type storage - $umount\n";
                    return $postreply;
                }
                my $res = `lvremove --yes /dev/stabile$type/$vol  2>&1`;
                chomp $res;
                $res .= `vgremove -f stabile$type 2>&1`;
                chomp $res;
                my $pdev = "/dev/$dev";
                $pdev .= '1' unless ($pdev =~ /1$/);
                $res .= `pvremove $pdev 2>&1`;
                chomp $res;
                $postreply .= "Status=OK Unconfigured lvm - $res\n";
            } else {
                $postreply .= "Status=Error LVM is already configured for $type\n";
                return $postreply;
            }
        }
    }
    # Check if $dev is still in use
    $mounts = `cat /proc/mounts`;
    $zpools = `zpool list -v`;
    $pvs = `pvdisplay -c`;
    if ($mounts =~ /\/dev\/$dev/ || $pvs =~ /$dev/ || $zpools =~ /$dev/) {
        $postreply .= "Status=Error $dev is already in use - use force.\n";
        return $postreply;
    }
    # Now format
    my $ispart = 1 if ($dev =~ /[a-zA-Z]+\d+/);
    if ($fs eq 'zfs') { # ZFS was specified
        $postreply = "Status=OK Initializing $dev disk with ZFS for $type...\n";
        if (!$ispart) {
            my $fres = `parted -s /dev/$dev mklabel GPT 2>&1`;
            $postreply .= "Status=OK partitioned $dev: $fres\n";
        }
        if ($z) { # zpool already created
            `zpool add stabile-$type /dev/$dev`;
        } else {
            `zpool create stabile-$type /dev/$dev`;
            `zfs create stabile-$type/$type`;
            `zfs set atime=off stabile-$type/$type`;
        }
#        if ($force) {
#            $postreply .= "Status=OK Forcibly removing all files in $stordir to allow ZFS mount\n";
#            `rm -r $stordir/*`;
#        }
#        `zfs set mountpoint=$stordir stabile-$type/$type`;
        $stordir = "/stabile-$type/$type" if (`zfs mount stabile-$type/$type`);
        `/bin/chmod 777 $stordir`;
        $postreply .= "Status=OK Mounted stabile-$type/$type as $type storage on $stordir.\n";
        if ($activate) {
            $postreply .= "Status=OK Setting $type storage device to $dev.\n";
            Setstoragedevice('', 'setstoragedevice', {device=>"stabile-$type", type=>$type});
        }
    } else { # Assume LVM
        $postreply = "Status=OK Initializing $dev with LVM for $type...\n";
        my $part = $dev;
        if (!$ispart) {
            $part = $dev.'1';
            `/sbin/sfdisk -d /dev/$dev > /root/$dev-partition-sectors.save`;
            my $fres = `sfdisk /dev/$dev << EOF\n;\nEOF`;
            $postreply .= "Status=OK partitioned $dev: $fres\n";
        }
        `/sbin/vgcreate -f stabile$type /dev/$part`;
        `/sbin/vgchange -a y stabile$type`;
        my $totalpe =`/sbin/vgdisplay stabile$type | grep "Total PE"`;
        $totalpe =~ /Total PE\s+(\d+)/;
        my $size = $1 -2000;
#        my $size = "10000";
        if ($size <100) {
            $postreply .= "Status=Error Volume is too small to make sense...\n";
            return $postreply;
        }
        my $vol = $type . "vol";
        `/sbin/lvcreate --yes -l $size stabile$type -n $vol`;
#        `/sbin/mkfs.ext4 /dev/stabile$type/$vol`;
        `mkfs.btrfs /dev/stabile$type/$vol`;
        my $mounted = `mount -v /dev/stabile$type/$vol $stordir`;
        `chmod 777 $stordir`;
        if ($mounted) {
            $postreply .= "Status=OK Mounted /dev/stabile$type/$vol as $type storage on $stordir.\n";
        } else {
            $postreply .= "Status=Error Could not mount /dev/stabile$type/$vol as $type storage on $stordir.\n";
        }
        if ($activate){
            Setstoragedevice('', 'setstoragedevice', {device=>"stabile$type-$type".'vol', type=>$type});
        }
    }
    return $postreply;
}

sub setCgroupsBlkDevice {
    my @majmins = split(" ", shift);
    my $file = "/etc/stabile/cgconfig.conf";
    my %options = (
        blkio.throttle.read_bps_device => $valve_readlimit,
        blkio.throttle.write_bps_device => $valve_writelimit,
        blkio.throttle.read_iops_device => $valve_iopsreadlimit,
        blkio.throttle.write_iops_device => $valve_iopswritelimit
        );
    my @groups = ('stabile', 'stabilevm');
    my @newlines;
    foreach my $majmin (@majmins) {
        foreach my $group (@groups) {
            my $mline = qq|group $group {|; push @newlines, $mline;
            my $mline = qq|    blkio {|; push @newlines, $mline;
            foreach my $option (keys %options) {
                my $mline = qq|        $option = "$majmin $options{$option}";|;
                push @newlines, $mline;
            }
            my $mline = qq|    }|; push @newlines, $mline;
            my $mline = qq|}|; push @newlines, $mline;
        }
    }
    unless (open(FILE, "> $file")) {
        $postreply .= "Status=Error Problem opening $file\n";
        return $postreply;
    }
    print FILE join("\n", @newlines);
    close(FILE);
    return;
}
