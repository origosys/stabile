#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license

# Clear up tainted environment
$ENV{PATH} = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin';
delete @ENV{'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};

#use warnings FATAL => 'all';
use CGI::Carp qw(fatalsToBrowser);
use CGI qw(:standard);
use Getopt::Std;
use JSON;
use URI::Escape qw(uri_escape uri_unescape);
use Tie::DBI;
use Data::Dumper;
use Encode;
use Text::SimpleTable;
use ConfigReader::Simple;
use Sys::Syslog qw( :DEFAULT setlogsock);
use Digest::SHA qw(sha512_base64 sha512_hex);
use utf8;
use Hash::Merge qw( merge );
use Storable qw(freeze thaw);
use Gearman::Client;
use Proc::ProcessTable;
use HTTP::Async;
use HTTP::Request::Common;
use LWP::Simple qw(!head);
use Error::Simple;

our %options=();
# -a action -h help -f full list -p full update -u uuid -i image -m match pattern -k keywords -g args to gearman task
# -v verbose, include HTTP headers -s impersonate subaccount -t target [uuid or image] -c force console
Getopt::Std::getopts("a:hfpu:i:g:m:k:vs:t:c", \%options);

$Stabile::config = ConfigReader::Simple->new("/etc/stabile/config.cfg",
    [qw(
        AMT_PASSWD
        DBI_PASSWD
        DBI_USER
        DO_DNS
        DNS_DOMAIN
        DO_XMPP
        ENGINEID
        ENGINENAME
        ENGINE_DATA_NIC
        ENGINE_LINKED
        EXTERNAL_IP_RANGE_START
        EXTERNAL_IP_RANGE_END
        EXTERNAL_IP_QUOTA
        EXTERNAL_NIC
        EXTERNAL_SUBNET_SIZE
        MEMORY_QUOTA
        NODE_STORAGE_OVERCOMMISSION
        NODESTORAGE_QUOTA
        PROXY_GW
        PROXY_IP
        PROXY_IP_RANGE_END
        PROXY_IP_RANGE_START
        PROXY_SUBNET_SIZE
        RDIFF-BACKUP_ENABLED
        RDIFF-BACKUP_USERS
        RX_QUOTA
        SHOW_COST
        STORAGE_BACKUPDIR
        STORAGE_POOLS_ADDRESS_PATHS
        STORAGE_POOLS_DEFAULTS
        STORAGE_POOLS_LOCAL_PATHS
        STORAGE_POOLS_NAMES
        STORAGE_POOLS_RDIFF-BACKUP_ENABLED
        STORAGE_QUOTA
        Z_IMAGE_RETENTION
        Z_BACKUP_RETENTION
        TX_QUOTA
        VCPU_QUOTA
        VLAN_RANGE_START
        VLAN_RANGE_END
        VERSION
    )]);

$dbiuser =  $Stabile::config->get('DBI_USER') || "irigo";
$dbipasswd = $Stabile::config->get('DBI_PASSWD') || "";
$dnsdomain = $Stabile::config->get('DNS_DOMAIN') || "stabile.io";
$appstoreurl = $Stabile::config->get('APPSTORE_URL') || "https://www.origo.io/registry";
$appstores = $Stabile::config->get('APPSTORES') || "stabile.io"; # Used for publishing apps
$engineuser = $Stabile::config->get('ENGINEUSER') || "";
$imageretention = $Stabile::config->get('Z_IMAGE_RETENTION') || "";
$backupretention = $Stabile::config->get('Z_BACKUP_RETENTION') || "";
$enginelinked = $Stabile::config->get('ENGINE_LINKED') || "";
$downloadmasters = $Stabile::config->get('DOWNLOAD_MASTERS') || "";
$disablesnat = $Stabile::config->get('DISABLE_SNAT') || "";
our $engineid = $Stabile::config->get('ENGINEID') || "";

$Stabile::dbopts = {db=>'mysql:steamregister', key=>'uuid', autocommit=>0, CLOBBER=>2, user=>$dbiuser, password=>$dbipasswd};
$Stabile::auth_tkt_conf = "/etc/apache2/conf-available/auth_tkt_cgi.conf";

my $base = "/var/www/stabile";
$base = `cat /etc/stabile/basedir` if (-e "/etc/stabile/basedir");
chomp $base;
$base =~ /(.+)/; $base = $1; #untaint
$main::logfile = "/var/log/stabile/steam.log";

$current_time = time;
($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime($current_time);
$year += 1900;
$month = substr("0" . ($mon+1), -2);
$pretty_time = sprintf "%4d-%02d-%02d@%02d:%02d:%02d",$year,$mon+1,$mday,$hour,$min,$sec;

if ($ENV{'HTTP_HOST'} && !($ENV{'HTTP_HOST'} =~ /^10\./) && $ENV{'HTTP_HOST'} ne 'localhost' && !($ENV{'HTTP_HOST'} =~ /^127/)) {
    $baseurl = "https://$ENV{'HTTP_HOST'}/stabile";
    `echo "$baseurl" > /tmp/baseurl` if ((! -e "/tmp/baseurl") && $baseurl);
} else  {
    if (!$baseurl && (-e "/tmp/baseurl" || -e "/etc/stabile/baseurl")) {
        if (-e "/etc/stabile/baseurl") {
            $baseurl = `cat /etc/stabile/baseurl`;
        } else {
            $baseurl = `cat /tmp/baseurl`;
            chomp $baseurl;
            `echo "$baseurl" >/etc/stabile/baseurl` unless (-e "/etc/stabile/baseurl");
        }
    }
}
if (!$baseurl) {
    my $hostname = `hostname`; chomp $hostname;
    $baseurl = "https://$hostname/stabile";
}
$baseurl = $1 if ($baseurl =~ /(.+)/); #untaint

$Stabile::basedir = "/var/www/stabile";
$Stabile::basedir = `cat /etc/stabile/basedir` if -e "/etc/stabile/basedir";
chomp $Stabile::basedir;
$Stabile::basedir = $1 if ($Stabile::basedir =~ /(.+)/); #untaint

$package = substr(lc __PACKAGE__, length "Stabile::");
$programname = "Stabile";

$sshcmd = qq|ssh -l irigo -i /var/www/.ssh/id_rsa_www -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no|;

$ENV{'REQUEST_METHOD'} = $ENV{'REQUEST_METHOD'} || 'GET';

preInit();
1;

$main::syslogit = sub {
	my ($user, $p, $msg) = @_;
	my $priority = ($p eq 'syslog')?'info':$p;

    $current_time = time;
    ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime($current_time);
    $year += 1900;
    $month = substr("0" . ($mon+1), -2);
    my $pretty_time = sprintf "%4d-%02d-%02d@%02d:%02d:%02d",$year,$mon+1,$mday,$hour,$min,$sec;

    my $loguser = (!$tktuser || $tktuser eq $user)?"$user":"$user ($tktuser)";
	if ($msg && $msg ne '') {
	    utf8::decode($msg);
		unless (open(TEMP3, ">>$main::logfile")) {$posterror .= "Status=Error log file '$main::logfile' could not be written";}
        $msg =~ /(.+)/; $msg = $1; #untaint
		print TEMP3 $pretty_time, " : $loguser : $msg\n";
		close(TEMP3);
	}
	return 0 unless ($priority =~ /err|debug/);
	setlogsock('unix');
	# $programname is assumed to be a global.  Also log the PID
	# and to CONSole if there's a problem.  Use facility 'user'.
	openlog($programname, 'pid,cons', 'user');
	syslog($priority, "($loguser) $msg");
	closelog();
	return 1;
};


$main::postToOrigo = sub {
    my ($engineid, $postaction, $postcontent, $postkey, $callback) = @_;
    my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
    my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
    my $ret;

    if ($tktkey && $engineid) {
        my $browser = LWP::UserAgent->new;
        $browser->timeout(15);
        $browser->agent('pressurecontrol/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );

        my $postreq;
        $postreq->{'engineid'} = $engineid;
        $postreq->{'enginetkthash'} = sha512_hex($tktkey) if ($enginelinked);
        $postreq->{'appuser'} = $user;
        $postreq->{'callback'} .= $callback if ($callback);
        $postkey = 'POSTDATA' unless ($postkey);
        $postreq->{$postkey} = $postcontent;
        my $posturl = "https://www.origo.io/irigo/engine.cgi?action=$postaction";
        my $content = $browser->post($posturl, $postreq)->content();
        my $ok = ($content =~ /OK: (.*)/i);
        $ret .= $content;
    } else {
        $main::syslogit->('pressurecontrol', 'info', "Unable to get engine tktkey...");
        $ret .= "Unable to get engine tktkey...";
    }
    return $ret;
};

$main::uploadToOrigo = sub {
    my ($engineid, $filepath, $force) = @_;
    my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
    my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
    my $ret;

    if (!$filepath || !(-e $filepath)) {
        $ret = "Status=Error Invalid file path\n";
    } elsif ($tktkey && $engineid) {
        $HTTP::Request::Common::DYNAMIC_FILE_UPLOAD = 1;
        my $browser = LWP::UserAgent->new;
        $browser->timeout(15 * 60); # 15 min
        $browser->agent('pressurecontrol/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );
        my $fname = $1 if ($filepath =~ /.*\/(.+\.qcow2)$/);
        return "Status=Error Invalid file\n" unless ($fname);
        my $posturl = "https://www.origo.io/irigo/engine.cgi?action=uploadimage";

# -- using ->post
#         my $postreq = [
#             'file'          => [ $filepath ],
#             'filename'      => $fname,
#             'engineid'      => $engineid,
#             'enginetkthash' => sha512_hex($tktkey),
#             'appuser'       => $user,
#             'force'         => $force
#         ];
#         my $content = $browser->post($posturl, $postreq, 'Content_Type' => 'form-data')->content;
#         $ret .= $content;

# -- using ->request
        my $req = POST $posturl,
            Content_Type => 'form-data',
            Content => [
                'file'          => [ $filepath ],
                'filename'      => $fname,
                'engineid'      => $engineid,
                'enginetkthash' => sha512_hex($tktkey),
                'appuser'       => $user,
                'force'         => $force
            ];
        my $total;
        my $callback = $req->content;
        if (ref($callback) eq "CODE") {
            my $size = $req->header('content-length');
            my $counter = 0;
            my $progress = '';
            $req->content(
                sub {
                    my $chunk = $callback->();
                    if ($chunk) {
                        my $length = length $chunk;
                        $total += $length;
                        if ($total / $size * 100 > $counter) {
                            $counter = 1+ int $total / $size * 100;
                            $progress .= "#";
                            `echo "$progress$counter" >> /tmp/upload-$fname`;
                        }
#                        printf "%+5d = %5.1f%%\n", $length, $total / $size * 100;
#                        printf "%5.1f%%\n", $total / $size * 100;

                    } else {
#                        print "Done\n";
                    }
                    $chunk;
                }
            );
            my $resp = $browser->request($req)->content();
            $ret .= $resp;
            $ret .= "Status=OK $progress\n";
        } else {
            $ret .= "Status=Error Did not get a callback";
        }
    } else {
        $ret .= "Status=Error Unable to get engine tktkey...";
    }
    return $ret;
};

$main::postAsyncToOrigo = sub {
    my ($engineid, $postaction, $json_text) = @_;
    my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
    my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
    my $ret;

    if ($tktkey && $engineid) {
        my $browser = LWP::UserAgent->new;
        $browser->timeout(15);
        $browser->agent('pressurecontrol/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );

        $ret .= "Posting $postaction to origo.io\n";

        my $postreq;
        $postreq->{'engineid'} = $engineid;
        $postreq->{'enginetkthash'} = sha512_hex($tktkey);
        $postreq->{'POSTDATA'} = $json_text;
#        my $content = $browser->post("https://www.origo.io/irigo/engine.cgi?action=$postaction", $postreq)->content();
#        my $ok = ($content =~ /OK: (.*)/i);
#        $ret .= $content;

        my $async = HTTP::Async->new;
        my $post = POST "https://www.origo.io/irigo/engine.cgi?action=$postaction",
            [   engineid => $engineid,
                enginetkthash => sha512_hex($tktkey),
                POSTDATA => $json_text
            ];
        $async->add( $post );
#        while ( my $response = $async->wait_for_next_response ) {
#            $ret .= $response->decoded_content;
#        }
    } else {
        $main::syslogit->('pressurecontrol', 'info', "Unable to get engine tktkey...");
        $ret .= "Unable to get engine tktkey...";
    }
    return $ret;
};

$main::dnsCreate = sub {
    my ($engineid, $name, $value, $type, $username) = @_;
    my $res;
    my $dnssubdomain = substr($engineid, 0, 8);
    $type = uc $type;
    $type || 'CNAME';
    $name = $1 if ($name =~ /(.+)\.$dnsdomain/);
    # $name =$1 if ($name =~ /(.+)\.$dnssubdomain/);
    if ($type eq 'A') { # Look for initial registrations and format correctly
        if (!$name && $value) { # If no name provided assume we are creating initial A-record
            $name = $value;
        } elsif ($name =~ /^(\d+\.\d+\.\d+\.\d+)/) { # Looks like an IP address - must be same as value
            if ($1 eq $value) { # Keep some order in registrations
                $name = "$value.$dnssubdomain"; # The way we format initial registrations
            } else {
                $name = '';
            }
        }
    }
    # Only allow creation of records corresponding to user's own networks when username is supplied
    # When username is not supplied, we assume checking has been done
    if ($username) {
        my $checkval = $value;
        # Remove any trailing period
        $checkval = $1 if ($checkval =~ /(.+)\.$/);
        if ($type eq 'TXT') {
            $checkval = '';
        } elsif ($type eq 'A') {
            $checkval = $value;
        } else {
            $checkval = $1 if ($checkval =~ /(\d+\.\d+\.\d+\.\d+)\.$dnssubdomain\.$dnsdomain$/);
            $checkval = $1 if ($checkval =~ /(\d+\.\d+\.\d+\.\d+)\.$dnsdomain$/);
            $checkval = $1 if ($checkval =~ /(\d+\.\d+\.\d+\.\d+)$/);
        }
        if ($checkval) {
            unless (tie %networkreg,'Tie::DBI', {
                    db=>'mysql:steamregister',
                    table=>'networks',
                    key=>'uuid',
                    autocommit=>0,
                    CLOBBER=>0,
                    user=>$dbiuser,
                    password=>$dbipasswd}) {throw Error::Simple("Error Register could not be accessed")};
            my @regkeys = (tied %networkreg)->select_where("externalip = '$checkval'");
            if (scalar @regkeys == 1) {
                if ($register{$regkeys[0]}->{'user'} eq $username) {
                    ; # OK
                } else {
                    return qq|{"status": "Error", "message": "Invalid value $checkval, not allowed"}|;
                }
            } elsif (scalar @regkeys >1) {
                return qq|{"status": "Error", "message": "Invalid value $checkval"}|;
            }
            untie %networkreg;
            if ($type eq 'A') {
#                $name = "$checkval.$dnssubdomain"; # Only allow this type of A-records...?
            } else {
                $value = "$checkval.$dnssubdomain";
            }
        }
    }

    if ($type ne 'MX' && $type ne 'TXT' && `host $name.$dnsdomain authns1.cabocomm.dk` =~ /has address/) {
        return qq|{"status": "Error", "message": "$name is already registered"}|;
    };

    if ($enginelinked && $name && $value) {
        require LWP::Simple;
        my $browser = LWP::UserAgent->new;
        $browser->agent('Stabile/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );
        $browser->timeout(10);
        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
        my $tkthash = sha512_hex($tktkey);
        my $posturl = "https://www.origo.io/irigo/engine.cgi?action=dnscreate";

        my $async = HTTP::Async->new;
        my $post = POST $posturl,
            [ engineid        => $engineid,
                enginetkthash => $tkthash,
                name          => $name,
                domain        => $dnsdomain,
                value         => $value,
                type          => $type,
                username      => $username || $user
            ];
        # We fire this asynchronously and hope for the best. Waiting for an answer is just too erratic for now
        $async->add( $post );

        if ($username) {
            my $response;
            while ( $response = $async->wait_for_next_response ) {
                $ret .= $response->decoded_content;
            }
            foreach my $line (split /\n/, $ret) {
               $res .= $line unless ($line =~ /^\d/);
            }
        }
    #    $res =~ s/://g;
        return "$res\n";

    } else {
        return qq|{"status": "Error", "message": "Problem creating dns record with data $name, $value.| . ($enginelinked?"":" Engine is not linked!") . qq|"}|;
    }
};

$main::dnsDelete = sub {
    my ($engineid, $name, $value, $type, $username) = @_;
    my $dnssubdomain = substr($engineid, 0, 8);
    $name = $1 if ($name =~ /(.+)\.$dnsdomain$/);
#    $name =$1 if ($name =~ /(.+)\.$dnssubdomain/);
    if ($name =~ /^(\d+\.\d+\.\d+\.\d+)$/) {
        $name = "$1.$dnssubdomain";
        $type = $type || 'A';
    }

    $main::syslogit->($user, "info", "Deleting DNS entry $type $name $dnsdomain");
    if ($enginelinked && $name) {
        require LWP::Simple;
        my $browser = LWP::UserAgent->new;
        $browser->agent('Stabile/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );
        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
        my $tkthash = sha512_hex($tktkey);
        my $posturl = "https://www.origo.io/irigo/engine.cgi?action=dnsdelete";

        my $postreq = ();
        $postreq->{'engineid'} = $engineid;
        $postreq->{'enginetkthash'} = $tkthash;
        $postreq->{'name'} = $name;
        $postreq->{'value'} = $value;
        $postreq->{'type'} = $type;
        $postreq->{'username'} = $username || $user;
        $postreq->{'domain'} = "$dnsdomain";
        $content = $browser->post($posturl, $postreq)->content();
    #    $content =~ s/://g;
        return $content;
    } else {
        return "ERROR Invalid data $name." . ($enginelinked?"":" Engine is not linked!") . "\n";
    }
};

$main::dnsUpdate = sub {
    my ($engineid, $name, $value, $type, $oldname, $oldvalue, $username) = @_;
    $name = $1 if ($name =~ /(.+)\.$dnsdomain/);
    $type = uc $type;
    $type || 'CNAME';

    # Only allow deletion of records corresponding to user's own networks when username is supplied
    # When username is not supplied, we assume checking has been done
    # Obsolete
    # my $checkval;
    # if ($username) {
    #     if ($name =~ /\d+\.\d+\.\d+\.\d+/) {
    #         $checkval = $name;
    #     } else {
    #         my $checkname = $name;
    #         # Remove trailing period
    #         $checkname = $1 if ($checkname =~ /(.+)\.$/);
    #         $checkname = "$checkname.$dnsdomain" unless ($checkname =~ /(.+)\.$dnsdomain$/);
    #         $checkval = $1 if (`host $checkname authns1.cabocomm.dk` =~ /has address (\d+\.\d+\.\d+\.\d+)/);
    #         return "ERROR Invalid value $checkname\n" unless ($checkval);
    #     }
    #
    #     unless (tie %networkreg,'Tie::DBI', {
    #         db=>'mysql:steamregister',
    #         table=>'networks',
    #         key=>'uuid',
    #         autocommit=>0,
    #         CLOBBER=>0,
    #         user=>$dbiuser,
    #         password=>$dbipasswd}) {throw Error::Simple("Error Register could not be accessed")};
    #     my @regkeys = (tied %networkreg)->select_where("externalip = '$checkval' OR internalip = '$checkval'");
    #     if ($isadmin || (scalar @regkeys == 1 && $register{$regkeys[0]}->{'user'} eq $username)) {
    #         ; # OK
    #     } else {
    #         return "ERROR Invalid user for $checkval, not allowed\n";
    #     }
    #     untie %networkreg;
    # }

    $main::syslogit->($user, "info", "Updating DNS entries for $name $dnsdomain");
    if ($enginelinked && $name) {
        require LWP::Simple;
        my $browser = LWP::UserAgent->new;
        $browser->agent('Stabile/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );
        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
        my $tkthash = sha512_hex($tktkey);
        my $posturl = "https://www.origo.io/irigo/engine.cgi?action=dnsupdate";

        my $postreq = ();
        $postreq->{'engineid'} = $engineid;
        $postreq->{'enginetkthash'} = $tkthash;
        $postreq->{'name'} = $name;
        $postreq->{'value'} = $value;
        $postreq->{'type'} = $type;
        $postreq->{'oldname'} = $oldname if ($oldname);
        $postreq->{'oldvalue'} = $oldvalue if ($oldvalue);
        $postreq->{'username'} = $username || $user;
        $postreq->{'domain'} = $dnsdomain;
        $content = $browser->post($posturl, $postreq)->content();
        return $content;
    } else {
        return "ERROR Invalid data $name." . ($enginelinked?"":" Engine is not linked!") . "\n";
    }
};

$main::dnsList = sub {
    my ($engineid, $username, $domain) = @_;
    if ($enginelinked) {
        require LWP::Simple;
        my $browser = LWP::UserAgent->new;
        $browser->agent('Stabile/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );
        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
        my $tkthash = sha512_hex($tktkey);
        my $posturl = "https://www.origo.io/irigo/engine.cgi?action=dnslist";
        $domain = $domain || $dnsdomain;

        my $postreq = ();
        $postreq->{'engineid'} = $engineid;
        $postreq->{'enginetkthash'} = $tkthash;
        $postreq->{'domain'} = $domain;
        $postreq->{'username'} = $username || $user;
        $content = $browser->post($posturl, $postreq)->content();
    #    $content =~ s/://g;
        return $content;
    } else {
        return "ERROR Engine is not linked!\n";
    }
};

$main::dnsClean = sub {
    my ($engineid, $username) = @_;
    if ($enginelinked) {
        require LWP::Simple;
        my $browser = LWP::UserAgent->new;
        $browser->agent('Stabile/1.0b');
        $browser->protocols_allowed( [ 'http','https'] );
        my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
        my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
        my $tkthash = sha512_hex($tktkey);
        my $posturl = "https://www.origo.io/irigo/engine.cgi?action=dnsclean";
        my $postreq = ();
        $postreq->{'engineid'} = $engineid;
        $postreq->{'enginetkthash'} = $tkthash;
        $postreq->{'domain'} = $dnsdomain;
        $content = $browser->post($posturl, $postreq)->content();
        $content =~ s/://g;
        return $content;
    } else {
        return "ERROR Engine is not linked!\n";
    }
};

$main::xmppSend = sub {
    my ($to, $msg, $engineid, $sysuuid) = @_;
    $engineid = `cat /etc/stabile/config.cfg | sed -n -e 's/^ENGINEID=//p'` unless ($engineid);
    my $doxmpp = `cat /etc/stabile/config.cfg | sed -n -e 's/^DO_XMPP=//p'`;
    if (!$doxmpp) {
        return "INFO: DO_XMPP not enabled in config\n";

    } elsif ($to && $msg) {
        my $xdom;
        $xdom = $1 if ($to =~ /\@(.+)$/);
        if ($xdom && `host -t SRV _xmpp-server._tcp.$xdom` !~ /NXDOMAIN/) {
            require LWP::Simple;
            my $browser = LWP::UserAgent->new;
            $browser->agent('Stabile/1.0b');
            $browser->protocols_allowed( [ 'http','https'] );
            $browser->timeout(10);
            my $tktcfg = ConfigReader::Simple->new($Stabile::auth_tkt_conf, [qw(TKTAuthSecret)]);
            my $tktkey = $tktcfg->get('TKTAuthSecret') || '';
            my $tkthash = sha512_hex($tktkey);
            my $posturl = "https://www.origo.io/irigo/engine.cgi?action=xmppsend";

            my $async = HTTP::Async->new;
            my $post = POST $posturl,
                [   engineid => $engineid,
                    enginetkthash => $tkthash,
                    sysuuid => $sysuuid,
                    to => $to,
                    msg => $msg
                ];
            $async->add( $post );

            #my $postreq = ();
            #$postreq->{'engineid'} = $engineid;
            #$postreq->{'enginetkthash'} = $tkthash;
            #$postreq->{'to'} = $to;
            #$postreq->{'msg'} = $msg;
            #$content = $browser->post($posturl, $postreq)->content();

            return "Status=OK Sent xmpp message to $to\n";
        } else {
            return "Status=ERROR XMPP srv records not found for domain \"$xdom\"\n";
        }

    } else {
        return "Status=ERROR Invalid xmpp data $to, $msg\n";
    }
};

# Enumerate and return network interfaces
$main::getNics = sub {
    my $internalnic = $Stabile::config->get('ENGINE_DATA_NIC');
    my $externalnic = $Stabile::config->get('EXTERNAL_NIC');
    if (!$externalnic) {
        my $droute = `ip route show default`;
        $externalnic = $1 if ($droute =~ /default via .+ dev (.+) proto/);
    }
    my @nics = ();
    if (!$externalnic || !$internalnic) {
        my $niclist = `ifconfig | grep flags= | sed -n -e 's/: .*//p'`;
        if (-e "/mnt/stabile/tftp/bionic") { # If a piston root exists, assume we will be providing boot services over secondary NIC even if it has no link
            $niclist = `ifconfig -a | grep flags= | sed -n -e 's/: .*//p'`;
        }
        # my $niclist = `netstat -in`;
        push @nics, $externalnic if ($externalnic);
        foreach my $line (split("\n", $niclist)) {
            if ($line =~ /^(\w+)$/) {
                my $nic = $1;
                push(@nics, $nic) if ($nic ne 'lo' && $nic ne $externalnic && !($nic=~/^virbr/) && !($nic=~/^docker/) && !($nic=~/^br/) && !($nic=~/^vnet/) && !($nic=~/^Name/) && !($nic=~/^Kernel/) && !($nic=~/^Iface/) && !($nic=~/(\.|\:)/));
            }
        }
    }
    $externalnic = $externalnic || $nics[0];
    $internalnic = $internalnic || $nics[1] || $externalnic;
    return ($internalnic, $externalnic);
};

$main::updateUI = sub {
    my @parslist = @_;
    my $newtasks;
    my $tab;
    my $duser;
    foreach my $pars (@parslist) {
        my $type = $pars->{type};
        my $duuid = $pars->{uuid};
        my $domuuid = $pars->{domuuid};
        my $dstatus = $pars->{status};
        my $message = $pars->{message};
        $message =~ s/"/\\"/g;
        $message =~ s/'/\\'/g;
        my $newpath = $pars->{newpath};
        my $displayip = $pars->{displayip};
        my $displayport = $pars->{displayport};
        my $name = $pars->{name};
        my $master = $pars->{master};
        my $mac = $pars->{mac};
        my $macname = $pars->{macname};
        my $progress = $pars->{progress};
        my $title = $pars->{title};
        my $managementlink = $pars->{managementlink};
        my $backup = $pars->{backup};
        my $download = $pars->{download};
        my $size = $pars->{size};
        my $sender = $pars->{sender};
        my $path = $pars->{path};
        my $snap1 = $pars->{snap1};
        my $username = $pars->{username};

        $tab = $pars->{tab};
        $duser = $pars->{user};
        $duser = "irigo" if ($duser eq "--");
        $tab = $tab || substr(lc __PACKAGE__, 9);
        $type = $type || ($message?'message':'update');
        $sender = $sender || "stabile:$package";

        if ($package eq 'users' && $pars->{'uuid'}) {
            my %u = %{$register{$pars->{'uuid'}}};
            delete $u{'password'};
            $u{'user'} = $duser;
            $u{'type'} = 'update';
            $u{'status'} = ($u{'privileges'} =~ /d/)?'disabled':'enabled';
            $u{'tab'} = $package;
            $u{'timestamp'} = $current_time;
            $newtasks .= to_json(\%u) . ", ";
        } else {
            $newtasks .= "{\"type\":\"$type\",\"tab\":\"$tab\",\"timestamp\":$current_time" .
                ($duuid?",\"uuid\":\"$duuid\"":"") .
                ($domuuid?",\"domuuid\":\"$domuuid\"":"") .
                ($duser?",\"user\":\"$duser\"":"") .
                ($dstatus?",\"status\":\"$dstatus\"":"") .
                ($message?",\"message\":\"$message\"":"") .
                ($newpath?",\"path\":\"$newpath\"":"") .
                ($displayip?",\"displayip\":\"$displayip\"":"") .
                ($displayport?",\"displayport\":\"$displayport\"":"") .
                ($name?",\"name\":\"$name\"":"") .
                ($backup?",\"backup\":\"$backup\"":"") .
                ($download?",\"download\":\"$download\"":"") .
                ($size?",\"size\":\"$size\"":"") .
                ($mac?",\"mac\":\"$mac\"":"") .
                ($macname?",\"macname\":\"$macname\"":"") .
                ($progress?",\"progress\":$progress":"") . # This must be a number between 0 and 100
                ($title?",\"title\":\"$title\"":"") .
                ($managementlink?",\"managementlink\":\"$managementlink\"":"") .
                ($master?",\"master\":\"$master\"":"") .
                ($snap1?",\"snap1\":\"$snap1\"":"") .
                ($username?",\"username\":\"$username\"":"") .
                ($path?",\"path\":\"$path\"":"") .
                ",\"sender\":\"$sender\"}, ";
        }
    }
    $newtasks = $1 if ($newtasks =~ /(.+)/); #untaint
    my $res;
    eval {
        opendir my($dh), '/tmp' or die "Couldn't open '/tmp': $!";
        my @files;
        if ($tab eq 'nodes' || $duser eq 'irigo') {
            # write tasks to all admin user's session task pipes
            @files = grep { /.*~A-.*\.tasks$/ } readdir $dh;
        } else {
            # write tasks to all the user's session task pipes
            @files = grep { /^$duser~.*\.tasks$/ } readdir $dh;
        }
        closedir $dh;
        my $t = new Proc::ProcessTable;
        my @ptable = @{$t->table};
        my @pfiles;
        my $cmnds;
        foreach my $f (@files) {
#            my $n = `pgrep -fc "$f"`;
#            chomp $n;
            foreach my $p ( @ptable ){
                my $pcmd = $p->cmndline;
                $cmnds .= $pcmd . "\n" if ($pcmd =~ /tmp/);
                if ($pcmd =~ /\/tmp\/$f/) { # Only include pipes with active listeners
                    push @pfiles, "/tmp/$f";
                    last;
                }
            }
        };
        my $tasksfiles = join(' ', @pfiles);
        $tasksfiles = $1 if ($tasksfiles =~ /(.+)/); #untaint
        # Write to users named pipes if user is logged in and session file found
        if ($tasksfiles) {
            $res = `/bin/echo \'$newtasks\' | /usr/bin/tee  $tasksfiles \&`;
        } else {
        # If session file not found, append to orphan tasks file wait a sec and reload
            $res = `/bin/echo \'$newtasks\' >> /tmp/$duser.tasks`;
            $res .= `chown www-data:www-data /tmp/$duser.tasks`;
#            sleep 1;
            eval {`/usr/bin/pkill -HUP -f ui_update`; 1;} or do {;};
#            `echo "duh: $duser" >> /tmp/duh`;
        }
#        eval {`/usr/bin/pkill -HUP -f $duser~ui_update`; 1;} or do {;};
    } or do {$e=1; $res .= "ERROR Problem writing to tasks pipe $@\n";};
    return 1;
};

sub action {
    my ($target, $action, $obj) = @_;
    my $res;
    my $func = ucfirst $action;
    # If a function named $action (with first letter uppercased) exists, call it and return the result
    if (defined &{$func}) {
        $res .= &{$func}($target, $action, $obj);
    }
    return $res;
}

sub privileged_action {
    my ($target, $action, $obj) = @_;
    return "Status=ERROR Your account does not have the necessary privileges\n" if ($isreadonly);
    return action($target, $action) if ($help);
    my $res;
    $obj = {} unless ($obj);
    $obj->{'console'} = 1 if ($console || $options{c});
    $obj->{'baseurl'} =  $baseurl if ($baseurl);
    my $client = Gearman::Client->new;
    $client->job_servers('127.0.0.1:4730');
    # Gearman server will try to call a method named "do_gear_$action"
    $res = $client->do_task(steamexec => freeze({package=>$package, tktuser=>$tktuser, user=>$user, target=>$target, action=>$action, args=>$obj}));
    $res = ${ $res };
    return $res;
}

sub privileged_action_async {
    my ($target, $action, $obj) = @_;
    return "Status=ERROR Your account does not have the necessary privileges\n" if ($isreadonly);
    return action($target, $action) if ($help);
    my $client = Gearman::Client->new;
    $client->job_servers('127.0.0.1:4730');
    my $tasks = $client->new_task_set;
    $obj = {} unless ($obj);
    $obj->{'console'} = 1 if ($console || $options{c});
    # Gearman server will try to call a method named "do_gear_$action"
    if (scalar(keys %{$obj}) > 2 ) {
        my $handle = $tasks->add_task(steamexec => freeze({package=>$package, tktuser=>$tktuser, user=>$user, target=>$target, action=>$action, args=>$obj}));
    } else {
        my $handle = $tasks->add_task(steamexec => freeze({package=>$package, tktuser=>$tktuser, user=>$user, target=>$target, action=>$action}));
    }
    my $regtarget = $register{$target};
    my $imgregtarget = $imagereg{$target};
    $uistatus = $regtarget->{status} || "$action".'ing';
    $uistatus = 'cloning' if ($action eq 'clone');
    $uistatus = 'snapshotting' if ($action eq 'snapshot');
    $uistatus = 'unsnapping' if ($action eq 'unsnap');
    $uistatus = 'mastering' if ($action eq 'master');
    $uistatus = 'unmastering' if ($action eq 'unmaster');
    $uistatus = 'backingup' if ($action eq 'backup');
    $uistatus = 'restoring' if ($action eq 'restore');
    $uistatus = 'saving' if ($action eq 'save');
    $uistatus = 'venting' if ($action eq 'releasepressure');
    my $name = $regtarget->{name} || $imgregtarget->{name};
    if ($action eq 'save') {
        if ($package eq 'images') {
            if ($obj->{status} eq 'new') {
                $obj->{status} = 'unused';
            }
            elsif ($obj->{regstoragepool} ne $obj->{storagepool}) {
                $obj->{'status'} = $uistatus = 'moving';
            }
        }
        $postreply = to_json($obj, {pretty=>1});
        $postreply = encode('utf8', $postreply);
        $postreply =~ s/""/"--"/g;
        $postreply =~ s/null/"--"/g;
        $postreply =~ s/"notes" {0,1}: {0,1}"--"/"notes":""/g;
        $postreply =~ s/"installable" {0,1}: {0,1}"(true|false)"/"installable":$1/g;
        return $postreply;
    } else {
        return "Status=$uistatus OK $action $name (deferred)\n";
    }
}

sub do_gear_action {
    my ($target, $action ,$obj) = @_;
    $target = encode("iso-8859-1", $target); # MySQL uses Latin1 as default charset
    $action = $1 if ($action =~ /gear_(.+)/);
    my $res;
    return "This only works with elevated privileges\n" if ($>);
    if ($register{$target}
        || $action =~ /all$|save|^monitors|^packages|^changemonitoremail|^buildsystem|^removesystem|^updateaccountinfo|^updateengineinfo|^removeusersystems|^removeuserimages/
        || $action =~ /^updateamtinfo|^updatedownloads|^releasepressure|linkmaster$|activate$|engine$|^syncusers|^deletesystem|^getserverbackups|^listserverbackups|^fullstats/
        || $action =~ /^zbackup|^updateallbtimes|^initializestorage|^liststoragedevices|^getbackupdevice|^getimagesdevice|^listbackupdevices|^listimagesdevices/
        || $action =~ /^setstoragedevice|^updateui|configurecgroups|backup|sync_backup/
        || ($action eq 'remove' && $package eq 'images' && $target =~ /\.master\.qcow2$/) # We allow removing master images by name only
    ) {
        my $func = ucfirst $action;
        # If a function named $action (with first letter uppercased) exists, call it and return the result
        if (defined &{$func}) {
            if ($obj) {
                $console = $obj->{'console'} if ($obj->{'console'});
                $target = $obj->{uuid} if (!$target && $obj->{uuid}); # backwards compat with apps calling removesystem
                $res .= &{$func}($target, $action, $obj);
            } else {
                $res .= &{$func}($target, $action);
            }
        } else {
            $res .= "Status=ERROR Unable to $action $target - function not found in $package\n";
        }
    } else {
        $res .= "Status=ERROR Unable to $action $target - target not found in $package\n";
    }
    return $res;
}

sub preInit {
# Set global vars: $user, $tktuser, $curuuid and if applicable: $curdomuuid, $cursysuuid, $curimg
# Identify and validate user, read user prefs from DB
    unless ( tie(%userreg,'Tie::DBI', Hash::Merge::merge({table=>'users', key=>'username'}, $Stabile::dbopts)) ) {throw Error::Simple("Status=Error User register could not be  accessed")};

    $user = $user || $Stabile::user || $ENV{'REMOTE_USER'};
    $user = 'irigo' if ($package eq 'steamexec');
    $remoteip = $ENV{'REMOTE_ADDR'};
    # If request is coming from a running server from an internal ip, identify user requesting access
    if (!$user && $remoteip && $remoteip =~ /^10\.\d+\.\d+\.\d+/) {
        unless ( tie(%networkreg,'Tie::DBI', Hash::Merge::merge({table=>'networks', CLOBBER=>3}, $Stabile::dbopts)) ) {throw Error::Simple("Status=Error Network register could not be accessed")};
        unless ( tie(%domreg,'Tie::DBI', Hash::Merge::merge({table=>'domains', CLOBBER=>3}, $Stabile::dbopts)) ) {throw Error::Simple("Status=Error Domain register could not be accessed")};
        my @regkeys = (tied %networkreg)->select_where("internalip = '$remoteip'");
        foreach my $k (@regkeys) {
            my $network = $networkreg{$k};
            my @domregkeys = (tied %domreg)->select_where("networkuuid1 = '$network->{uuid}'");
            my $dom = $domreg{$network->{'domains'}} || $domreg{$domregkeys[0]}; # Sometimes domains is lost in network - compensate
            # Request is coming from a running server from an internal ip - accept
            if ($network->{'internalip'} eq $remoteip) {
                $user = $network->{'user'};
                # my $dom = $domreg{$network->{'domains'}};
                if ($package eq 'networks') {
                    $curuuid = $network->{'uuid'};
                    $curdomuuid = $network->{'domains'};
                    $cursysuuid = $dom->{'system'};
                } elsif ($package eq 'images') {
                    $curimg = $dom->{'image'} unless ($curimg);
                } elsif ($package eq 'systems') {
                    $curuuid = $dom->{'system'} || $dom->{'uuid'} unless ($curuuid);
                    $cursysuuid = $dom->{'system'};
                    $curdomuuid = $dom->{'uuid'};
                } elsif ($package eq 'servers') {
                    $curuuid = $dom->{'uuid'} unless ($curuuid);
                    $cursysuuid = $dom->{'system'};
                }
                if (!$userreg{$user}->{'allowinternalapi'}) {
                    $user = ''; # Internal API access is not enabled, disallow access
                }
                last;
            }
        }
        untie %networkreg;
        untie %domreg;
    }
    $user = $1 if $user =~ /(.+)/; #untaint
    $tktuser = $user;
    $Stabile::tktuser = $tktuser;

    # Initalize CGI
    $Stabile::q = new CGI;

    # Load params
    %params = $Stabile::q->Vars;
    $uripath = URI::Escape::uri_unescape($ENV{'REQUEST_URI'});
    if ($options{s}) {
        $account = $options{s};
    } else {
        $account = $Stabile::q->cookie('steamaccount');
    }
    $user = 'guest' if (!$user && $params{'action'} eq 'help');
    die "No active user. Please authenticate or provide user through REMOTE_USER environment variable." unless ($user);

    my $u = $userreg{$user};
    my @accounts = split(/,\s*/, $u->{'accounts'}) if ($u->{'accounts'});
    my @accountsprivs = split(/,\s*/, $u->{'accountsprivileges'}) if ($u->{'accountsprivileges'});
    for my $i (0 .. $#accounts)
        { $ahash{$accounts[$i]} = $accountsprivs[$i] || 'r'; }

	$privileges = '';
    # User is requesting access to another account - check privs
    if ($account && $account ne $user) {
        if ($ahash{$account}) {
            $user = $account;
            $main::account = $account;
            # Only allow users whose base account is admin to get admin privs
            $ahash{$account} =~ s/a// unless ($userreg{$tktuser}->{'privileges'} =~ /a/);
            $privileges = $ahash{$account};
            $u = $userreg{$account};
        }
    }

    $Stabile::user = $user;

    $defaultmemoryquota = $Stabile::config->get('MEMORY_QUOTA') + 0;
    $defaultstoragequota = $Stabile::config->get('STORAGE_QUOTA') + 0;
    $defaultnodestoragequota = $Stabile::config->get('NODESTORAGE_QUOTA') + 0;
    $defaultvcpuquota = $Stabile::config->get('VCPU_QUOTA') + 0;
    $defaultexternalipquota = $Stabile::config->get('EXTERNAL_IP_QUOTA') + 0;
    $defaultrxquota = $Stabile::config->get('RX_QUOTA') + 0;
    $defaulttxquota = $Stabile::config->get('TX_QUOTA') + 0;

    # Read quotas and privileges from db
    $Stabile::userstoragequota = 0+ $u->{'storagequota'} if ($u->{'storagequota'});
    $Stabile::usernodestoragequota = 0+ $u->{'nodestoragequota'} if ($u->{'storagequota'});
    $usermemoryquota = 0+ $u->{'memoryquota'} if ($u->{'memoryquota'});
    $uservcpuquota = 0+ $u->{'vcpuquota'} if ($u->{'vcpuquota'});
    $Stabile::userexternalipquota = 0+ $u->{'externalipquota'} if ($u->{'externalipquota'});
    $Stabile::userrxquota = 0+ $u->{'rxquota'} if ( $u->{'rxquota'});
    $Stabile::usertxquota = 0+ $u->{'txquota'} if ($u->{'txquota'});

    $billto = $u->{'billto'};
    $Stabile::userprivileges = $u->{'privileges'};
    $privileges = $Stabile::userprivileges if (!$privileges && $Stabile::userprivileges);
    $isadmin = index($privileges,"a")!=-1;
    $ismanager = index($privileges,"m")!=-1;
    $isreadonly = index($privileges,"r")!=-1;
    $preserveimagesonremove = index($privileges,"p")!=-1;
    $fulllist = $options{f} && $isadmin;
    $fullupdate = $options{p} && $isadmin;

    my $bto = $userreg{$billto};
    my @bdnsdomains = split(/, ?/, $bto->{'dnsdomains'});
    my @udnsdomains = split(/, ?/, $u->{'dnsdomains'});
    $dnsdomain = '' if ($dnsdomain eq '--'); # TODO - ugly
    $udnsdomains[0] = '' if ($udnsdomains[0] eq '--');
    $bdnsdomains[0] = '' if ($bdnsdomains[0] eq '--');
    $dnsdomain = $udnsdomains[0] || $bdnsdomains[0] || $dnsdomain; # override config value

    my $bstoreurl = $bto->{'appstoreurl'};
    $bstoreurl = '' if ($bstoreurl eq '--');
    my $ustoreurl = $u->{'appstoreurl'};
    $ustoreurl = '' if ($ustoreurl eq '--');
    $appstoreurl = $bstoreurl || $ustoreurl || $appstoreurl; # override config value

    $Stabile::sshcmd = $sshcmd;
    $Stabile::disablesnat = $disablesnat;
    $Stabile::privileges = $privileges;
    $Stabile::isadmin = $isadmin;

    $storagepools = $u->{'storagepools'}; # Prioritized list of users storage pools as numbers, e.g. "0,2,1"
    my $dbuser = $u->{'username'};
    untie %userreg;

    # If params are passed in URI for a POST og PUT request, we try to parse them out
     if (($ENV{'REQUEST_METHOD'} ne 'GET')  && !$isreadonly) {
         $action = $1 if (!$action && $uripath =~ /action=(\w+)/);
         if ($uripath =~ /$package(\.cgi)?\/(.+)$/ && !$isreadonly) {
             my $uuid = $2;
             if (!(%params) && !$curuuid && $uuid =~ /^\?/) {
                 %params = split /[=&]/, substr($uuid,1);
                 $curuuid = $params{uuid};
             } else {
                 $curuuid = $uuid;
             }
             $curuuid = $1 if ($curuuid =~ /\/(.+)/);
         }
     }

    # Parse out params from g option if called from cmdline
    my $args = $options{g};
    if ($args && !%params) {
        my $obj = from_json( uri_unescape ($args));
        if (ref($obj) eq 'HASH') {
            %params = %{$obj};
        } else {
            %params = {};
            $params{'POSTDATA'} = $args;
        }
        $console = $obj->{'console'} if ($obj->{'console'});
        $curuuid = $obj->{uuid} if (!$curuuid && $obj->{uuid}); # backwards compat with apps calling removesystem
    }

    # Action may be via on command line switch -a
    if (!$action) {
        $action = $options{a};
        if ($action) { # Set a few options if we are called from command line
            $console = 1 unless ($options{v} && !$options{c});
            $Data::Dumper::Varname = $package;
            $Data::Dumper::Pair = ' : ';
            $Data::Dumper::Terse = 1;
            $Data::Dumper::Useqq = 1;
        }
    }
    # Parse out $action - i.e. find out what action is requested
    $action = $action || $params{'action'}; # $action may have been set above to 'remove' by DELETE request

    # Handling of action given as part of addressable API
    # Special cases for systems, monitors, etc.
    if (!$action && $uripath =~ /$package\/(.+)(\/|\?)/ && !$params{'path'}) {
        $action = $1;
        $action = $1 if ($action =~ /([^\/]+)\/(.*)/);
    }
    $curuuid = $curuuid || $params{'uuid'} || $params{'id'} || $params{'system'} || $params{'serveruuid'};
    # Handling of target given as part of addressable API
    #    if ($uripath =~ /$package(\.cgi)?\/($action\/)?(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})(:\w+)?/) {
    if ($uripath =~ /$package\/(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})(:\w+)?/) {
        $curuuid = "$1$2";
    } elsif ($package eq 'nodes' && $uripath =~ /$package\/(\w{12})(:\w+)?/) {
        $curuuid = "$1$2";
    }

    $action = lc $action;
    if (!$params && $options{k}) {
        $params{'keywords'} = URI::Escape::uri_unescape($options{k});
        $console = 1 unless ($options{v} && !$options{c});
    }
    $action = (($action)?$action.'_':'') . 'remove' if ($ENV{'REQUEST_METHOD'} eq 'DELETE' && $action ne 'remove');
    # -f should only set $fulllisting and not trigger any keyword actions
    delete $params{'keywords'} if ($params{'keywords'} eq '-f');

    # Regular read - we send out JSON version of directory list
    if (!$action && (!$ENV{'REQUEST_METHOD'} || $ENV{'REQUEST_METHOD'} eq 'GET')) {
        if (!($package)) {
            ; # If we get called as a library this is were we end - do nothing...
        } elsif ($params{'keywords'}) {
            ; # If param keywords is provided treat as a post
        } else {
            $action = 'list';
        }
    }

    ### Main security check
    unless ($package eq 'pressurecontrol' || $dbuser || ($user eq 'common' && $action =~ /^updatebtime|^list/)) {throw Error::Simple("Status=Error $action: Unknown user $user [$remoteip]")};
    if (index($privileges,"d")!=-1 && $action ne 'help') {throw Error::Simple("Status=Error Disabled user")};

    $curuuid = $curuuid || URI::Escape::uri_unescape($params{'uuid'}); # $curuuid may have been set above for DELETE requests
    $curuuid = "" if ($curuuid eq "--");
    $curuuid = $options{u} unless $curuuid;
    if ($package eq 'images') {
        $curimg = URI::Escape::uri_unescape($params{'image'} || $params{'path'}) unless ($action eq 'listfiles');
        $curimg = "" if ($curimg eq "--");
        $curimg = $1 if ($curimg =~ /(.*)\*$/); # Handle Dojo peculiarity
        $curimg = URI::Escape::uri_unescape($options{i}) unless $curimg;
        unless (tie(%imagereg,'Tie::DBI', Hash::Merge::merge({table=>'images', CLOBBER=>1}, $Stabile::dbopts)) ) {throw Error::Simple("Stroke=Error Image UUID register could not be accessed")};
        if ($curimg && !$curuuid && $curimg =~ /(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})/) {
            $curuuid = $curimg;
            $curimg = $imagereg{$curuuid}->{'path'} if ($imagereg{$curuuid});
#        } elsif ($target && !$curimg && !$curuuid) {
#            if ($target =~ /(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})/) {
#                $curuuid = $1;
#                $curimg = $imagereg{$curuuid}->{'path'};
#            } else {
#                $curimg = $target;
#            }
        } elsif (!$curimg && $curuuid) {
            $curimg = $imagereg{$curuuid}->{'path'} if ($imagereg{$curuuid});
        }
        untie %imagereg;
    }
}

sub process {
    my $target = $params{'target'} || $options{t} ||  $curuuid;
    # We may receive utf8 strings either from browser or command line - convert them to native Perl to avoid double encodings
    utf8::decode($target) if ( $target =~ /[^\x00-\x7f]/ );# true if string contains any non-ascii character
    my $uipath;
#    my $uistatus;
# Special handling
    if ($package eq 'images') {
        $target = $curimg || $params{'path'} || $params{'image'} || $target unless ($target =~ /^\/.+/);
        $params{'restorepath'} = $params{'path'} if ($action eq 'listfiles');
        $params{'baseurl'} = "https://$ENV{'HTTP_HOST'}/stabile" if ($action eq 'download' && $ENV{'HTTP_HOST'} && !($baseurl =~ /\./)); # send baseurl if configured value not valid
    } elsif ($package eq 'systems') {
        $target = $params{'id'} || $target if ($action =~ /^monitors_/);
    } elsif ($package eq 'nodes') {
        $target = $target || $params{'mac'};
    } elsif ($package eq 'users') {
        $target = $target || $params{'username'};
    }
    # Named action - we got a request for an action
    my $obj;
    if ($action && (defined &{"do_$action"}) && ($ENV{'REQUEST_METHOD'} ne 'POST' || $action eq 'upload' || $action eq 'restorefiles')) {
        # If a function named do_$action (only lowercase allowed) exists, call it and print the result
        if ($action =~ /^monitors/) {
            if ($params{'PUTDATA'}) {
                $obj = $params{'PUTDATA'};
                $action = 'monitors_save' unless ($action =~ /monitors_.+/);
            } else {
                $obj = { action => $action, id => $target };
            }
        } else {
            unless (%params) {
                if ($package eq 'images' && $target =~ /^\//) {
                    %params = ("path", $target);
                    delete $params{"uuid"};
                } else{
                    %params = ("uuid", $target);
                }
            }
            if ($curuuid || $target) {
                $params{uuid} = $curuuid || $target unless ($params{uuid} || $params{path} || ($params{image} && $package eq 'images'));
            }
            $obj = getObj(\%params);
        }
        $obj->{'console'} = $console if ($console);
        $obj->{'baseurl'} = $params{baseurl} if ($params{baseurl});
    # Perform the action
        $postreply = &{"do_$action"}($target, $action, $obj);
        if (!$postreply) { # We expect some kind of reply
            $postreply .= header('text/plain', '500 Internal Server Error because no reply') unless ($console);
            $main::syslogit->($user, 'info', "Could not $action $target ($package)") unless ($action eq 'uuidlookup');
        } elsif (! ($postreply =~ /^(Content-type|Status|Location):/i) ) {
            if ($postreply =~ /Content-type:/) {
                ;
            } elsif (!$postreply || $postreply =~ /Status=/ || $postreply =~ /^</ || $postreply =~ /^\w/) {
                $postreply = header('text/plain; charset=UTF8') . $postreply unless ($console);
            } else {
                $postreply = header('application/json; charset=UTF8') . $postreply unless ($console);
            }
        }
        print "$postreply";

    } elsif (($params{'PUTDATA'} || $params{"keywords"} || $params{"POSTDATA"})  && !$isreadonly) {
        # We got a save post with JSON. Look for interesting stuff and perform action or save
        my @json_array;
		if ($params{'PUTDATA'}) {
		    my $json_text = $params{'PUTDATA'};
            utf8::decode($json_text);
            $json_text =~ s/\x/ /g;
    		$json_text =~ s/\[\]/\"\"/g;
		    @json_array = from_json($json_text);
		} elsif ($params{"keywords"} || $params{"POSTDATA"}) {
            my $json_text = $params{"keywords"} || $params{'POSTDATA'};
            $json_text = uri_unescape($json_text);
            utf8::decode($json_text);
            $json_text =~ s/\x/ /g;
            $json_text =~ s/\[\]/\"\"/g;
            my $json_obj = from_json($json_text);
            if (ref $json_obj eq 'ARRAY') {
                @json_array = @$json_obj;
            } elsif (ref $json_obj eq 'HASH') {
                my %json_hash = %$json_obj;
                my $json_array_ref = [\%json_hash];
                if ($json_hash{"items"}) {
                    $json_array_ref = $json_hash{"items"};
                }
                @json_array = @$json_array_ref;
            }
		}

        foreach (@json_array) {
			my %h = %$_;
			$console = 1 if $h{"console"};
            my $objaction = $h{'action'} || $action;
            $objaction = 'save' if (!$objaction || $objaction eq "--");
            $h{'action'} = $objaction = $action.'_'.$objaction if ($action eq "monitors" || $action eq "packages"); # Allow sending e.g. disable action to monitors by calling monitors_disable
            $h{'action'} = $objaction if ($objaction && !$h{'action'});
            my $obj = getObj(\%h);
            next unless $obj;
            $obj->{'console'} = $console if ($console);
        # Now build the requested action
            my $objfunc = "do_$objaction";
        # If a function named objfunc exists, call it
            if (defined &$objfunc) {
                $target = $h{'uuid'} || $h{'id'};
                $uiuuid = $target;
                my $targetimg = $imagereg{$target};
        # Special handling
                if ($package eq 'images') {
                    $target = $targetimg->{'path'} || $h{'image'} || $h{'path'} || $target;
                }
        # Perform the action
                $postreply = &{$objfunc}($target, $objaction, $obj);
        #        $uistatus = $1 if ($postreply =~ /\w+=(.\w+) /);
        # Special handling
                if ($package eq 'images') {
                    if ($h{'status'} eq 'new') {
#                        $uistatus = 'new';
#                        $uiuuid = ''; # Refresh entire view
                    }
                }
                my $node = $nodereg{$mac};
                my $updateEntry = {
                    tab=>$tab,
                    user=>$user,
                    uuid=>$uiuuid,
                    status=>$uistatus,
                    mac=>$mac,
                    macname=>$node->{'name'},
                    displayip=>$uidisplayip,
                    displayport=>$uidisplayport,
                    type=>$uiupdatetype,
                    message=>$postmsg
                };
                # Special handling
                if ($package eq 'images') {
                    $obj->{'uuid'} = '' if ($uistatus eq 'new');
                    $uipath = $obj->{'path'};
                    $updateEntry->{'path'} = $uipath;
                    $uiname = $obj->{'name'};
                }
                if ($uiname) {
                    $updateEntry->{'name'} = $uiname;
                }
                if ($uiuuid || $postmsg || $uistatus) {
                    push (@updateList, $updateEntry);
                }
            } else {
                $postreply .= "Status=ERROR Unknown $package action: $objaction\n";
            }
		}

        if (! ($postreply =~ /^(Content-type|Status|Location):/i) ) {
            if (!$postreply || $postreply =~ /Status=/) {
                $postreply = header('text/plain; charset=UTF8') . $postreply unless ($console);
            } else {
                $postreply = header('application/json; charset=UTF8') . $postreply unless ($console);
            }
        }
        print $postreply;
    } else {
        $postreply .= "Status=Error Unknown $ENV{'REQUEST_METHOD'} $package action: $action\n";
        print header('text/html', '500 Internal Server Error') unless ($console);
        print $postreply;
	}
    # Functions called via aliases to privileged_action or privileged_action_async cannot update $postmsg or $uistatus
    # so updateUI must be called internally in these functions.
    if (@updateList) {
        $main::updateUI->(@updateList);
    }
}


# Print list of available actions
sub Help {
    $help = 1;
    no strict 'refs';
    my %fdescriptions;
    my %fmethods;
    my %fparams;
    my @fnames;

    my $res = header() unless ($console);
    #    my $tempuuid = "484d7852-90d2-43f1-8bd6-e29e234848b0";
    my $tempuuid = "";
    unless ($console) {
        $res .= <<END
    <!DOCTYPE html>
    <html>
        <head>
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.0/jquery.min.js"></script>
            <!-- script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script -->
            <!-- script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js" integrity="sha384-ZMP7rVo3mIykV+2+9J3UJ46jBk0WLaUAdn689aCwoqbBJiSnjAK/l8WvCWPIPm49" crossorigin="anonymous"></script -->
            <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js" integrity="sha384-ChfqqxuZUCnJSK3+MXmPNIyE6ZbWh2IMqE241rYiqJxyMiZ6OW/JmZQ5stwEULTy" crossorigin="anonymous"></script>
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css" integrity="sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO" crossorigin="anonymous">
            <style>
                .form-control {display: inline-block; width: auto; margin: 2px; }
                input.form-control {width: 180px;}
				pre {
					overflow-x: auto;
					white-space: pre-wrap;
					white-space: -moz-pre-wrap;
					white-space: -pre-wrap;
					white-space: -o-pre-wrap;
					word-wrap: break-word;
				}
            </style>
        </head>
        <body style="margin:1.25rem;">
        <div>
            <table style="width:100%;"><tr><td>
            <select class="form-control" id="scopeaction" name="scopeaction" placeholder="action" onchange="data.scopeaction=this.value; dofields();" autocomplete="off"></select>
            <span id="scopeinputs">
            <input class="form-control" id="scopeuuid" name="scopeuuid" placeholder="uuid" onchange="data.scopedata.uuid=this.value; update();" value="$tempuuid" autocomplete="off" size="34">
            </span>
            <button class="btn btn-primary" href="#" onclick="doit();">Try it</button>
            <pre>
    \$.ajax({
        url: "<span class='scopeurl'>/stabile/$package?uuid=$tempuuid&action=activate</span>",
        type: "<span class='scopemethod'>GET</span>", <span id="dataspan" style="display:none;"><br />        data: "<span class="scopedata"></span>",</span>
        success: function(result) {\$("#scoperesult").text(result);}
    });
            </pre>
            </td><td width="50%"><textarea id="scoperesult" style="width:100%; height: 200px;"></textarea></td>
            </tr>
            </table>
        </div>
            <script>
                data = {"scopemethod": "GET", "scopeaction": "activate", "scopeuuid": "$tempuuid", "scopeurl": "/stabile/$package?uuid=$tempuuid&action=activate"};
                function doit() {
                    var obj = {
                        url: data.scopeurl,
                        type: data.scopemethod,
                        success: handleResult,
                        error: handleResult
                    }
                    if (data.scopemethod != 'GET') obj.data = JSON.stringify(data.scopedata);
                    \$.ajax(obj);
                    \$("#scoperesult").text("");
                    return true;
                    function handleResult(data, textStatus, jqXHR) {
                        if (jqXHR == 'Unauthorized') {
                            \$("#scoperesult").text(jqXHR + ": You must log in before you can call API methods.");
                        } else if (jqXHR.responseText) {
                            \$("#scoperesult").text(jqXHR.responseText);
                        } else {
                            \$("#scoperesult").text("No result received");
                        }
                    }
                }
                function dofields() {
                    if (scopeparams[data.scopeaction].length==0) {
                        \$("#scopeinputs").hide();
                    } else {
                        var fields = "";
                        \$.each(scopeparams[data.scopeaction], function (i, item) {
                            var itemname = "scope" + item;
                            if (\$("#"+itemname).val()) data[itemname] = \$("#"+itemname).val();
                            fields += '<input class="form-control" id="' + itemname + '" placeholder="' + item + '" value="' + ((data[itemname])?data[itemname]:'') + '" size="34" onchange="update();"> ';
                        });
                        \$("#scopeinputs").empty();
                        \$("#scopeinputs").append(fields);
                        \$("#scopeinputs").show();
                    }
                    update();
                }
                function update() {
                    data.scopemethod = scopemethods[data.scopeaction];
                    if (data.scopemethod == "POST") {
                        \$("#dataspan").show();
                        data.scopeurl = "/stabile/$package";
                        data.scopedata = {"items": [{"action":data.scopeaction}]};
                        \$.each(scopeparams[data.scopeaction], function (i, item) {
                            var val = \$("#scope"+item).val();
                            if (val) data.scopedata.items[0][item] = val;
                         });
                    } else if (data.scopemethod == "PUT") {
                        \$("#dataspan").show();
                        data.scopeurl = "/stabile/$package";
                        data.scopedata = [{"action":data.scopeaction}];
                        \$.each(scopeparams[data.scopeaction], function (i, item) {
                            var val = \$("#scope"+item).val();
                            if (val) data.scopedata[0][item] = val;
                         });
                    } else {
                        \$("#dataspan").hide();
                        data.scopeurl = "/stabile/$package?action="+data.scopeaction;
                        \$.each(scopeparams[data.scopeaction], function (i, item) {
                            var val = \$("#scope"+item).val();
                            if (val) data.scopeurl += "&" + item + "=" + val;
                        });
                        data.scopedata = '';
                    }
                    \$(".scopemethod").text(data.scopemethod);
                    \$(".scopeurl").text(data.scopeurl);
                    \$(".scopedata").text(JSON.stringify(data.scopedata, null, ' ').replace(/\\n/g,'').replace(/  /g,''));
                }
                \$( document ).ready(function() {
                    data.scopeaction=\$("#scopeaction").val(); dofields()
                });
END
        ;
        $res .= qq|var scopeparams = {};\n|;
        $res .= qq|var scopemethods = {};\n|;
        $res .= qq|var package="$package"\n|;
    }
    my @entries;
    if ($package eq 'networks') {
        @entries = sort keys %Stabile::Networks::;
    } elsif ($package eq 'images') {
        @entries = sort keys %Stabile::Images::;
    } elsif ($package eq 'servers') {
        @entries = sort keys %Stabile::Servers::;
    } elsif ($package eq 'nodes') {
        @entries = sort keys %Stabile::Nodes::;
    } elsif ($package eq 'users') {
        @entries = sort keys %Stabile::Users::;
    } elsif ($package eq 'systems') {
        @entries = sort keys %Stabile::Systems::;
    }

    foreach my $entry (@entries) {
        if (defined &{"$entry"} && $entry !~ /help/i && $entry =~ /^do_(.+)/) {
            my $fname = $1;
            # Ask function for help - $help is on
            my $helptext = &{"$entry"}(0, $fname);
            my @helplist = split(":", $helptext, 3);
            chomp $helptext;
            unless ($fname =~ /^gear_/) {
                $fmethods{$fname} = $helplist[0];
                $fparams{$fname} = $helplist[1];
                $fdescriptions{$fname} = $helplist[2];
                $fdescriptions{$fname} =~ s/\n// unless ($console);
                $fdescriptions{$fname} =~ s/\n/\n<br>/g unless ($console);
                my @plist = split(/, ?/, $fparams{$fname});
                unless ($console) {
                    $res .= qq|scopeparams["$fname"] = |.to_json(\@plist).";\n";
                    $res .= qq|\$("#scopeaction").append(new Option("$fname", "$fname"));\n|;
                    $res .= qq|scopemethods["$fname"] = "$helplist[0]";\n|;
                }
            }
        }
    }
    @fnames = sort (keys %fdescriptions);

    unless ($console) {
        $res .= "\n</script>\n";
        $res .= <<END
        <div class="table-responsive" style="margin-top:1.5rem; noheight: 65vh; overflow-y: scroll;">
            <table class="table table-striped table-sm">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Method</th>
                  <th>Parameters</th>
                  <th style="width:60%;">Description</th>
                </tr>
              </thead>
              <tbody>
END
        ;
        foreach my $fname (@fnames) {
            my $fp = ($fparams{$fname}) ? "$fparams{$fname}" : '';
            $res .= <<END
                    <tr>
                      <td><a href="#" onclick="data.scopeaction=this.text; \$('#scopeaction option[value=$fname]').prop('selected', true); dofields();">$fname</a></td>
                      <td>$fmethods{$fname}</td>
                      <td>$fp</td>
                      <td>$fdescriptions{$fname}</td>
                    </tr>
END
            ;
        }
        $res .= <<END
                </tbody>
            </table>
        </div>
END
        ;
        $res .= qq|</body>\n</html>|;
    } else {
        foreach my $fname (@fnames) {
            my $fp = ($fparams{$fname}) ? "[$fparams{$fname}]" : '';
            $res .= <<END
* $fname ($fmethods{$fname}) $fp $fdescriptions{$fname}
END
            ;
        }
    }

    return $res;
}

sub getBackupSize {
    my ($subdir, $img, $imguser) = @_; # $subdir, if specified, includes leading slash
    $imguser = $imguser || $user;
    my $backupsize = 0;
    my @bdirs = ("$backupdir/$imguser$subdir/$img");
    if ($backupdir =~ /^\/stabile-backup\//) { # ZFS backup is enabled - we need to scan more dirs
        @bdirs = (
            "/stabile-backup/*/$imguser$subdir/" . shell_esc_chars($img),
            "/stabile-backup/*/.zfs/snapshot/*/$imguser$subdir/". shell_esc_chars($img)
        );
    }
    foreach my $bdir (@bdirs) {
        my $bdu = `/usr/bin/du -bs $bdir 2>/dev/null`;
        my @blines = split("\n", $bdu);
        # only count size from last snapshot
        my $bline = pop @blines;
#        foreach my $bline (@blines) {
            $bline =~ /(\d+)\s+/;
            $backupsize += $1;
#        }
    }
    return $backupsize;
}

sub shell_esc_chars {
    my $str = shift;
    $str =~ s/([;<>\*\|`&\$!#\(\)\[\]\{\}:'" ])/\\$1/g;
    return $str;
}
