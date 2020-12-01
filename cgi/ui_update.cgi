#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license

use CGI ':standard';
use JSON;
use URI::Escape;
use Tie::DBI;
use Error qw(:try);
use Sys::Syslog qw( :DEFAULT setlogsock);
use ConfigReader::Simple;
use Data::Dumper;
use Time::HiRes qw(usleep);

$ENV{PATH} = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin';
delete @ENV{'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};

$SIG{'INT'} = sub { handle_signal('INT'); };
$SIG{'PIPE'} = sub { handle_signal('PIPE'); };
$SIG{'HUP'} = sub { handle_signal('HUP'); };
$SIG{'TERM'} = sub { handle_signal('TERM'); };

$q = new CGI;
%params = $q->Vars;

$user = $ENV{'REMOTE_USER'};
$user = $1 if ($user =~ /(.+)/); #untaint
$account = $q->cookie('steamaccount'); # User is using another account
$account = $user unless ($account);
$account = $1 if ($account =~ /(.+)/); #untaint


$naptime = 2;
$tied;
$session;
$i = 0;

my $config = ConfigReader::Simple->new("/etc/stabile/config.cfg",
    [qw(STORAGE_BACKUPDIR
    DBI_USER DBI_PASSWD ENGINEID
    )]);
my $dbiuser =  $config->get('DBI_USER') || "irigo";
my $dbipasswd = $config->get('DBI_PASSWD') || "";
my $tktname = 'auth_tkt';
$tktname = ('auth_' . substr($config->get('ENGINEID'), 0, 8) ) if ($config->get('ENGINEID'));

if (!is_user()) { # User not authenticated
    print header('text/html', '401 Unauthorized');
    print "User: $0 : $user not allowed\n";

} elsif (!$params{'s'}) { # Set up a new session

    $privileges = getPrivileges($user);

    if ($account ne $user) { # Check privileges
        $account = checkAccount($user, $account); # this also sets global $privileges
    }
    my $isadmin = index($privileges,"a")!=-1;

    if (!$account || index($privileges,"d")!=-1) {
        print header('text/html', '401 Unauthorized');
        exit 0;
    }

    my $tkt = $q->cookie($tktname);
    $session = substr($tkt, 0, 6);
    $session = "A-" . $session if ($isadmin);
    $session =~ /(.+)/; $session = $1; #untaint
    my $i = 1;
    while (-e "/tmp/$account~$session.$i.tasks") {$i++;};
    $session = "$session.$i";

    $account = $1 if ($account =~ /(.+)/);

    print header('application/json; charset=UTF8');

    # system(qq[/usr/bin/pkill -f "$account~ui_update" &]); # Remove lingering ui_update.cgi's if reloading or changing account
    `pkill -f "$account~ui_update.cgi"`; # Remove lingering ui_update.cgi's if reloading or changing account

    if ($session ) {
    #    `/usr/bin/mkfifo -m666 /tmp/$account~$session.tasks` unless (-e "/tmp/$account~$session.tasks");
        my $tasks = qq|{"type": "session", "session": "$session", "url": "/stabile/ui_update/$account~ui_update?s=$session"}|;
        print "[$tasks]\n";
    } else {
        sleep $naptime;
    }
} else { # Wait and read input from operations
    print header('application/json; charset=UTF8');

    $session = $params{'s'};
    $session =~ /(.+)/; $session = $1; #untaint
#    if (-e "/tmp/$account~$session.tasks") {
    my $r = substr rand(),2,4;
    my $update = qq|{"type": "serial", "serial": "$r"}|;
    my $tasks;
    if (-e "/tmp/$account.tasks") {
        $update = qq|{"type": "serial", "serial": "$r", "orphan": true}|;
        # Orphaned tasks found - read them
        $tasks = `/bin/cat < /tmp/$account.tasks`; # Read session tasks from pipe
        # unlink ("/tmp/$account.tasks");
        `rm "/tmp/$account.tasks"`;
    } else {
        $update = qq|{"type": "serial", "serial": "$r"}|;
        # This is where we block and wait for news...
        `/usr/bin/mkfifo -m666 /tmp/$account~$session.tasks` unless (-e "/tmp/$account~$session.tasks");
        $tasks = `/bin/cat < /tmp/$account~$session.tasks`; # Read session tasks from pipe
    }
    chomp $tasks;
    $tasks = substr($tasks, 0, -2) if ($tasks =~ /(, )$/); # Remove last comma and space
    if ($tasks && $tasks ne "--") {
        $update .= qq|, $tasks|;
    }
    print "[$update]\n";
    unlink "/tmp/$account~$session.tasks";
#    } else {
#        my $tasks = qq|{"type":"logout", "message":"Logged out"}| ;
#        print "[$tasks]\n";
#    }
}

sub handle_signal {
    my $sig = shift;
    return 0 if ($sig eq 'PIPE');
#    unlink "/tmp/$account~$session.tasks"; # unless ($hupped);
#    `/bin/rm /tmp/$account~$session.tasks`; # unless ($hupped);
#    `/usr/bin/touch /tmp/$account~$session.tasks` if (-e "/tmp/$account~$session.tasks");
    # Remove old session files
#    `/usr/bin/find /tmp/* -maxdepth 0 -name "*.tasks" ! -name "$account~$session.tasks" -mmin +1 -exec rm '{}' \\;`;
#    print header('application/json; charset=UTF8');
    print qq|{"signal":"$sig"}\n|;
    my $t = time;
    unlink "/tmp/$account~$session.tasks";
    `pkill -f "/bin/cat < /tmp/$account~$session.tasks"`;
    exit 0;
#    die;
}

sub is_user {
    # $0 contains the name of the script e.g. jakob@cabo.dk~ui_update.cgi
    $0 =~ /.+\/(.+)~+.+/;
    if ($1 eq $user || $1 eq $account) {return 1;}
    else {return 0;}
}

sub getPrivileges {
    my $u = shift;
    unless (tie %userreg,'Tie::DBI', {
        db=>'mysql:steamregister',
        table=>'users',
        key=>'username',
        autocommit=>0,
        CLOBBER=>1,
        user=>$dbiuser,
        password=>$dbipasswd}) {return ""};
    my $privs = $userreg{$u}->{'privileges'};
    untie %userreg;
    return $privs;
}

sub checkAccount {
    my ($user, $account) = @_;
    unless (tie %userreg,'Tie::DBI', {
        db=>'mysql:steamregister',
        table=>'users',
        key=>'username',
        autocommit=>0,
        CLOBBER=>1,
        user=>$dbiuser,
        password=>$dbipasswd}) {return 0};

    my %ahash;
    my @accounts = split(',', $userreg{$user}->{'accounts'});
    my @accountsprivs = split(',', $userreg{$user}->{'accountsprivileges'});
    for my $i (0 .. $#accounts)
        { $ahash{$accounts[$i]} = $accountsprivs[$i] || 'r'; }

    if ($ahash{$account}) {
        $user = $account;
        $privileges = $ahash{$account};
        unless ($userreg{$user}->{'username'}) {
            return 0;
        };
        if (index($privileges,"d")!=-1) {
            return 0;
        };
    }
    untie %userreg;
    return $user;
}