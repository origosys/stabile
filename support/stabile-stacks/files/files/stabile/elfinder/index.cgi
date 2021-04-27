#!/usr/bin/perl

use JSON;
use URI::Encode qw(uri_encode uri_decode);
use Data::Dumper;
use utf8;
use Text::ParseWords;
use WebminCore;
init_config();

# Ask Webmin to parse input
ReadParse();

my $action = $in{action};

my $cookie = $ENV{HTTP_COOKIE};
my $tkt;
$tkt = $1 if ($cookie =~ /auth_tkt=(\w+)/);
#$tkt = $1 if ($cookie =~ /auth_tkt=(\S+)\%/);
my $tktuser = `/usr/local/bin/ticketmaster.pl $tkt`;
chomp $tktuser;

if ($action eq 'smbmount') {
    my $hostname = $in{hostname};
    my $path = $in{path};
    $path = $2 if ($path =~ /(groups\/)(.+)/);

    $path =~ s/(\.+\/)//g;
    $path = "home/$1" if ($path =~ /^users\/.+\/(.*)/);
    $path = $1 if ($path =~ /(.+)\/$/);
    my $res = <<END
Content-type: text/html; charset=utf-8

smb://$tktuser\@$hostname/$path
END
;
    print $res;

} elsif ($action eq 'getpublink' || $action eq 'setpubread') {
    my $dir = $in{dir};
    $dir = $1 if ($dir =~ /(.+)\/$/);
    my $checked = $in{checked};
    my $dirOK = dirOK($dir);
    my $r;
    if ($dirOK) {
        my $tkt = `/usr/local/bin/ticketmaster.pl g -- "$dir"`;
        chomp $tkt;
        my $externalip = `cat /tmp/externalip`;
        chomp $externalip;
        my $pubreadpath;
        my $readpath;
        my $pubreadmatch = "false";
        my $prpaths = `cat /etc/apache2/sites-available/default | sed -rn 's/.*"\\/mnt\\/data\\/(.+)\\/"/\\1/p'`;
        my @pubreadpaths = split("\n", $prpaths);
        foreach my $prpath (@pubreadpaths) {
            if ($dir =~ /^$prpath/) {
                $pubreadmatch = "true" if ($dir eq $prpath);
                $pubreadpath = $dir;
                $pubreadpath = "/public/$2/"  if ($pubreadpath =~ /^(groups|users|shared)\/(.+)/);
                last;
            } elsif ($prpath =~ /^$dir/) {
                $pubreadpath = '--';
            }
        }
        if ($dirOK > 0) { # Write access required to share publicly
            my $escdir = $dir;
            $escdir = "$escdir/" unless ($escdir =~ /.*\/$/);
            $escdir =~ s/\//\\\//g;
            if ($pubreadpath && $pubreadmatch eq 'true' && $checked eq 'false') {
        # Remove share
                my $cmd = qq|perl -ni -e 'print unless (/\\/mnt\\/data\\/$escdir/)' /etc/apache2/sites-available/default|;
                `$cmd`;
                $readpath = "/$dir";
                $pubreadpath = '';
                `/etc/init.d/apache2 reload`;
            } elsif (!$pubreadpath && $checked eq 'true') {
        # Add share
                $pubreadpath = $dir;
                $pubreadpath = "/public/$2/"  if ($pubreadpath =~ /^(groups|users|shared)\/(.+)/);
                $escpubreadpath = $pubreadpath;
                $escpubreadpath =~ s/\//\\\//g;
                my $cmd = qq|perl -pi -e 's/<\\/VirtualHost>/Alias "$escpubreadpath\\/" "\\/mnt\\/data\\/$escdir"\\n<\\/VirtualHost>/;' /etc/apache2/sites-available/default|;
                `$cmd`;
                `/etc/init.d/apache2 reload`;
            }
        }

        my $res = <<END
Content-type: application/json; charset=utf-8

{"link": "https://$externalip/origo/elfinder/index.cgi?auth_tkt=$tkt", "path": "/origo/elfinder/index.cgi?auth_tkt=$tkt", "pubreadpath": "$pubreadpath", "pubreadmatch": $pubreadmatch, "readpath": "$readpath"}
END
;
        print "$res\n$r" if ($tktuser && $tktuser ne 'g');
    }

} elsif ($action eq 'btsync') {
    my $syncaction = $in{syncaction};
    my $dir = $in{dir};
    $dir = $1 if ($dir =~ /(.+)\/$/);
    my $dirOK;
    my $res = <<END
Content-type: application/json; charset=utf-8

END
;
    $dir = "/mnt/data/$dir" if ($dir =~ /^(users\/|groups\/|shared)/);
    # Security check
    my $pdir = "$dir/";

    if ($pdir =~ /^\/mnt\/data\/users\/$tktuser\//) {
        $dirOK = 1;
    } elsif ($pdir =~ /^\/mnt\/data\/groups\/(.+)\//) {
        my $groupdir = $1;
        $groupdir = $1 if ($groupdir =~ /(.+)\/[^\/]+/);
    # Get the users groups
        my %usergroups;
        my $intip = `cat /tmp/internalip`;
        $intip = `cat /etc/origo/internalip` if (-e '/etc/origo/internalip');
        my $dominfo = `samba-tool domain info $intip`;
        my $sambadomain;
        $sambadomain = $1 if ($dominfo =~ /Domain\s+: (\S+)/);
        if ($sambadomain) {
            my @domparts = split(/\./, $sambadomain);
            my $userbase = "CN=users,DC=" . join(",DC=", @domparts);
            my $cmd = "/usr/bin/ldbsearch -H /opt/samba4/private/sam.ldb -b \"CN=$tktuser,$userbase\" objectClass=user memberof";
            my $cmdres = `$cmd`;
            my @lines = split("\n", $cmdres);
            foreach my $line (@lines) {
                if ($line =~ /^memberOf: CN=(.+),CN=Users/) {
                    $group = $1;
                    $usergroups{$group} = $group;
                }
            };
        }
        if ($usergroups{$groupdir}) {
            $dirOK = -1;
            $dirOK = 1 if (isWriter($tktuser, $groupdir));
        }
    } elsif ($pdir =~ /^\/mnt\/data\/shared\//) {
        $dirOK = -1;
        $dirOK = 1 if (isWriter($tktuser, ''));
    }

    if ($tktuser) {
        if ($syncaction eq 'get_folders' && $dirOK>0) {
            my $btjson = `curl --silent "http://localhost:8888/api?method=get_folders"`;
            my $bthashref = from_json($btjson);
            my @folders = @{ $bthashref };
            my @newfolders = ();
            foreach my $folder (@folders) {
                push(@newfolders, $folder) if (
                        $folder->{dir} =~ /^\/mnt\/data\/users\/$tktuser\//
                        || $folder->{dir} =~ /^\/mnt\/data\/groups\//)
            }
            my $newjson = to_json(\@folders, {pretty=>1});
            $res .= $newjson;
        } elsif ($syncaction eq 'add_folder' && -e $dir && $dirOK>0) {
            my $btjson = `curl --silent "http://localhost:8888/api?method=get_folders"`;
            my $bthashref = from_json($btjson);
            my @folders = @{ $bthashref };
            my %dirs = map { $_->{dir} => $_->{secret} } @folders;
            if (!$dirs{$dir}) { # Only allow syncing folder once
                my $udir = $dir;
                utf8::decode($udir);
                $udir = uri_encode($udir);
                my $cmd = qq|curl --silent "http://localhost:8888/api?method=add_folder\&dir=$udir\&force=1"|;
                my $r = `$cmd`;
                $res .= getFolderInfo($dir, $in{secret}, $tktuser, $r, $dirOK);
            }
        } elsif ($syncaction eq 'remove_folder' && $dirOK>0) {
            my $secret = $in{secret};
            unless ($secret) {
                my $btjson = `curl --silent "http://localhost:8888/api?method=get_folders"`;
                my $bthashref = from_json($btjson);
                my @folders = @{ $bthashref };
                my %dirs = map { $_->{dir} => $_->{secret} } @folders;
                $secret = $dirs{$dir};
            }
            if ($secret) {
                my $r = `curl --silent "http://localhost:8888/api?method=remove_folder\&secret=$secret\&force=1"`;
                $r = uri_encode($r);
            }
            $res .= getFolderInfo($dir, $in{secret}, $tktuser, $r, $dirOK);
        } elsif ($syncaction eq 'get_folder_info' && $dirOK) {
            $res .= getFolderInfo($dir, $in{secret}, $tktuser, '', $dirOK);
        }
    }
    print $res;

} elsif ($in{auth_tkt}) {
    print "Location: index.cgi\n\n";

} else {
    my $commands;
    my $url = qq|url : 'php/connector.cgi',|;
    if ($tktuser eq 'g') {
        $commands = qq|commands: ['info', 'download', 'logout']|;
        $url = qq|url : 'php/connector.cgi?auth_tkt=$tkt',|;
    }


    my $elfinder = <<END
Content-type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
	<head>
		<meta charset="utf-8">
        <meta http-equiv="Cache-Control" content="no-store" />
        <title>Browse files</title>
        <script>
            IRIGO = {};
            IRIGO.tktuser = "$tktuser";
        </script>
		<!-- jQuery and jQuery UI (REQUIRED) -->
		<link rel="stylesheet" type="text/css" href="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.23/themes/smoothness/jquery-ui.css">
		<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.8.0/jquery.min.js"></script>
		<script src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.23/jquery-ui.min.js"></script>

		<!-- elFinder CSS (REQUIRED) -->
		<link rel="stylesheet" type="text/css" href="css/elfinder.full.css">
		<link rel="stylesheet" type="text/css" href="css/theme.css">

        <!-- elFinder JS (REQUIRED) -->
		<script src="js/elfinder.full.js"></script>

		<!-- elFinder initialization (REQUIRED) -->
		<script type="text/javascript" charset="utf-8">
			// Documentation for client options:
			// https://github.com/Studio-42/elFinder/wiki/Client-configuration-options
			\$(document).ready(function() {
				\$('#elfinder').elfinder({
					$url
                    $commands
				});
			});
		</script>
	</head>
	<body>

    <!-- Element where elFinder will be created (REQUIRED) -->
    <div id="elfinder"></div>
	</body>
</html>
END
;
    print $elfinder;
}

sub getFolderInfo {
    my $dir = shift;
    my $secret = shift;
    my $tktuser = shift;
    my $r = shift;
    my $dirOK = shift;
    $r = qq|"$r"| unless ($r =~ /^(\{|\[)/);
    my $btjson;
    my @jsons;
    my $ret = '';
    unless ($secret) {
        my $btjson = `curl --silent "http://localhost:8888/api?method=get_folders"`;
        my $bthashref = from_json($btjson);
        my @folders = @{ $bthashref };
        my %dirs = map { $_->{dir} => $_->{secret} } @folders;
        $secret = $dirs{$dir};
    }
    if ($secret) {
        my $secrets_json = `curl --silent "http://localhost:8888/api?method=get_secrets\&secret=$secret"`;
        my $privileges_json = '"privileges": "read_write"';
        if ($dir =~ /^\/mnt\/data\/groups/ || $dir =~ /^\/mnt\/data\/shared/) {
            unless ($dirOK>0) { # Only writers can see the read_write secret
                $secrets_json = '{"read_only": "' . from_json($secrets_json)->{read_only} . '"}';
                $privileges_json = '"privileges": "read_only"';
            }
        }
        push @jsons, $privileges_json if ($privileges_json);
        push @jsons, qq|"secrets": $secrets_json| if ($secrets_json);
        my $hosts_json = `curl --silent "http://localhost:8888/api?method=get_folder_hosts\&secret=$secret"`;
        $hosts_json = $1 if ($hosts_json =~ /^\{(.+)\}$/);
        push @jsons, $hosts_json if ($hosts_json);
        my $speed_json = `curl --silent "http://localhost:8888/api?method=get_speed\&secret=$secret"`;
        push @jsons, qq|"speed": $speed_json| if ($speed_json);
        my $peers_json = `curl --silent "http://localhost:8888/api?method=get_folder_peers\&secret=$secret"`;
        push @jsons, qq|"peers": $peers_json| if ($peers_json);
        push @jsons, qq|"result": $r| if ($r);
        my $json = '{' . join(', ', @jsons) . '}';
        $json = to_json(from_json($json), {pretty=>1});
        $ret .= $json;
    } else {
        my $btjson = `curl --silent "http://localhost:8888/api?method=get_folders"`;
        my $bthashref = from_json($btjson);
        my @folders = @{ $bthashref };
        my @subfolders = ();
        my @parfolders = ();
        foreach my $folder (@folders) {
            my $mdir = $folder->{dir};
            if ($mdir =~ /^$dir/) {
                $folder->{dir} =~ s/\/mnt\/data\/users\/$tktuser\//Home\//;
                push(@subfolders, $folder);
            }
            if ($dir =~ /^$mdir/) {
                $folder->{dir} =~ s/\/mnt\/data\/users\/$tktuser\//Home\//;
                push(@parfolders, $folder);
            }
        }
        my $privileges_json = '"privileges": "read_write"';
        if ($dir =~ /^\/mnt\/data\/groups/ || $dir =~ /^\/mnt\/data\/shared/) {
            if ($dirOK<0) {
                $privileges_json = '"privileges": "read_only"';
            }
        }
        my $newjson = qq|{"dir": "$dir"\n, "dirs": | . to_json(\@subfolders, {pretty=>1}) .
                      qq|, "parents": | . to_json(\@parfolders, {pretty=>1}) . ", " .
                      $privileges_json;
        $newjson .=   qq|,\n "result": $r| if ($r);
        $newjson .=   qq|}|;
        $ret = $newjson;
    }
    return $ret;
}

sub isWriter {
    ($tktuser, $group) = @_;
    my $conf = "/etc/samba/smb.conf";
    $conf = "/etc/samba/smb.conf.group.$group" if ($group);
    if (-e $conf) {
        my $wlist = `cat "$conf" | grep "write list"`;
        chomp $wlist;
        if ($wlist =~ /write list =(.+)/) {
            $wlist = $1;
            my @writers = quotewords('\s+', 1, $wlist);
            foreach my $writer (@writers) {
                if ($writer =~ /(\+)?"(.+)\\(.+)"/) {
                    if ($1) {
                        return 2 if (isGroupMember($tktuser, $3));
                    } else {
                        $writer = $3;
                        return 1 if (lc $writer eq lc $tktuser);
                    }
                }
            }
        } else {
            return 1; # No write list
        }
    }
}

sub isGroupMember {
    ($tktuser, $group) = @_;
    my $glist = `samba-tool group listmembers "$group"`;
    my @groups = split(/\n/, $glist);
    foreach my $g (@groups) {
        return 1 if (lc $g eq lc $tktuser);
    }
}

sub dirOK {
    my $dir = shift;
    $dir = "/mnt/data/$dir" if ($dir =~ /^(users\/|groups\/|shared)/);
    # Security check
    my $pdir = "$dir/";

    if ($pdir =~ /^\/mnt\/data\/users\/$tktuser\//) {
        $dirOK = 1;
    } elsif ($pdir =~ /^\/mnt\/data\/groups\/(.+)\//) {
        my $groupdir = $1;
        $groupdir = $1 if ($groupdir =~ /(.+)\/[^\/]+/);
    # Get the users groups
        my %usergroups;
        my $intip = `cat /tmp/internalip`;
        $intip = `cat /etc/origo/internalip` if (-e '/etc/origo/internalip');
        my $dominfo = `samba-tool domain info $intip`;
        my $sambadomain;
        $sambadomain = $1 if ($dominfo =~ /Domain\s+: (\S+)/);
        if ($sambadomain) {
            my @domparts = split(/\./, $sambadomain);
            my $userbase = "CN=users,DC=" . join(",DC=", @domparts);
            my $cmd = "/usr/bin/ldbsearch -H /opt/samba4/private/sam.ldb -b \"CN=$tktuser,$userbase\" objectClass=user memberof";
            my $cmdres = `$cmd`;
            my @lines = split("\n", $cmdres);
            foreach my $line (@lines) {
                if ($line =~ /^memberOf: CN=(.+),CN=Users/) {
                    $group = $1;
                    $usergroups{$group} = $group;
                }
            };
        }
        if ($usergroups{$groupdir}) {
            $dirOK = -1;
            $dirOK = 1 if (isWriter($tktuser, $groupdir));
        }
    } elsif ($pdir =~ /^\/mnt\/data\/shared\//) {
        $dirOK = -1;
        $dirOK = 1 if (isWriter($tktuser, ''));
    }
    # 1 = rw, -1 = r, 0 = no access
    return $dirOK;
}