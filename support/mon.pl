#!/usr/bin/perl
#
# mon - schedules service tests and triggers alerts upon failures
#
# Jim Trocki, trockij@arctic.org
#
# $Id: mon.pl,v 1.1 2012-10-23 19:57:32 cabo Exp $
#
# Copyright (C) 1998 Jim Trocki
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
use strict;

my $RCSID='$Id: mon.pl,v 1.1 2012-10-23 19:57:32 cabo Exp $';
my $AUTHOR='trockij@arctic.org';
my $RELEASE='$Name:  $';

#
# NetBSD rc.d script compatibility
#
$0= "mon" . " " . join(" ", @ARGV) if $^O eq "netbsd";

#
# modules in the perl distribution
#
use Getopt::Long qw(:config no_ignore_case);
use Text::ParseWords;
use POSIX;
use Fcntl;
use Socket;
use Sys::Hostname;
use Sys::Syslog qw(:DEFAULT);
use FileHandle;

use Data::Dumper;

#
# CPAN modules
#
use Time::HiRes qw(gettimeofday tv_interval usleep);
use Time::Period;

sub auth;
sub call_alert;
sub check_auth;
sub clear_timers;
sub client_accept;
sub client_close;
sub client_command;
sub client_dopending;
sub client_write_opstatus;
sub collect_output;
sub daemon;
sub debug;
sub debug_dir;
sub dep_ok;
sub dep_summary;
sub depend;
sub dhmstos;
sub die_die;
sub disen_host;
sub disen_service;
sub disen_watch;
sub do_alert;
sub do_startup_alerts;
sub err_startup;
sub esc_str;
sub gen_scriptdir_hash;
sub handle_io;
sub handle_trap;
sub handle_trap_timeout;
sub host_exists;
sub host_singleton_group;
sub inRange;
sub init_cf_globals;
sub init_globals;
sub load_auth;
sub load_state;
sub normalize_paths;
sub mysystem;
sub init_dtlog;
sub pam_conv_func;
sub proc_cleanup;
sub process_event;
sub randomize_startdelay;
sub read_cf;
sub readhistoricfile;
sub reload;
sub remove_proc;
sub reset_server;
sub run_monitor;
sub save_state;
sub set_last_test;
sub set_op_status;
sub reset_timer;
sub setup_server;
sub sock_write;
sub syslog_die;
sub un_esc_str;
sub usage;
sub write_dtlog;

#
# globals
#
my %opt;		# cmdline arguments
my %CF;			# configuration directives
my $PWD;		# current working directory
my $HOSTNAME;		# system hostname
my $STOPPED;		# 1 = scheduler stopped, 0 = not stopped
my $STOPPED_TIME;	# time(2) scheduler was stopped, if stopped
my $SLEEPINT;		# don't touch
my %watch_disabled;	# watches disabled, indexed by watch
my %watch;		# main configuration file data structure
my %alias;		# aliases
my %groups;		# hostgroups, indexed by group
my %views;		# view lists, indexed by name
my %view_users;         # view preferences, per user

#
# I/O routine globals
#
my %clients;		# fds of connected clients
my $numclients;		# count of connected clients
my %running;		# procs which are forked and running,
			# indexed by group/service
my $iovec;		# used for select loop
my %runningpid;		# procs which are forked and running,
			# indexed by PID
my $procs;		# number of outstanding procs
my %fhandles;		# input file handles of children
my %ibufs;		# buffer structure to hold data from children
my ($fdset_rbits, $fdset_ebits);

#
# history globals
#
my @last_alerts;	# alert history, in memory
my @last_failures;	# failure history, in memory

#
# misc. globals
#
my $i;			# loop iteration counter, used for debugging only
my $lasttm;		# the last time(2) the mon loop started
my $pid_file_owner;	# set when creating pid file
my $tm;			# used in main loop

#
# authentication structure globals
#
my %AUTHCMDS;
my %NOAUTHCMDS;
my %AUTHTRAPS;

#
# PAM authentication globals (must not be lexically scoped)
#
use vars qw ( $PAM_username $PAM_password ) ;


#
# opstatus globals
#
my (%OPSTAT, %FAILURE, %SUCCESS, %WARNING);	# operational statuses
my ($TRAP_COLDSTART, $TRAP_WARMSTART,		# trap types
	$TRAP_LINKDOWN, $TRAP_LINKUP,
	$TRAP_AUTHFAIL, $TRAP_EGPNEIGHBORLOSS,
	$TRAP_ENTERPRISE, $TRAP_HEARTBEAT);

my ($STAT_FAIL, $STAT_OK, $STAT_COLDSTART,	# _op_status values
	$STAT_WARMSTART, $STAT_LINKDOWN,
	$STAT_UNKNOWN, $STAT_TIMEOUT,
	$STAT_UNTESTED, $STAT_DEPEND, $STAT_WARN);

my ($FL_MONITOR, $FL_UPALERT,			# alert type flags
	$FL_TRAP, $FL_TRAPTIMEOUT,
	$FL_STARTUPALERT, $FL_TEST, $FL_REDISTRIBUTE,
        $FL_ACKALERT, $FL_DISABLEALERT);

my $TRAP_PDU;
my (%ALERTHASH, %MONITORHASH);			# hash of pathnames for
						# alerts/monitors
my $PROT_VERSION;
my $START_TIME;					# time(2) server started
my $TRAP_PRO_VERSION;				# trap protocol version
my $DEP_EVAL_SANDBOX;				# perl environment for
						# dep evals

#
# argument parsing
#
my $getopt_result = GetOptions(\%opt,
			       qw/
				  A|authfile=s
				  B|cfbasedir=s
				  D|statedir=s
				  L|logdir=s
				  M|m4:s
				  O|syslogfacility=s
				  P|pidfile=s
				  S|stopped
				  a|alertdir=s
				  b|basedir=s
				  c|configfile=s
				  d|debug+
				  f|fork
				  h|help
				  i|sleep=i
				  k|maxkeep=i
				  l|loadstate:s
				  m|maxprocs=i
				  p|port=i
				  r|randstart=s
				  s|scriptdir=s
				  t|trapport=i
				  v|version
				  /);

if (!$getopt_result) {
  usage();
  exit;
}

#
# these two things can be taken care of without
# initializing things further
#
if ($opt{"v"}) {
    print "$RCSID\n$RELEASE\n";
    exit;
}

if ($opt{"h"}) {
    usage();
    exit;
}

if ($opt{"d"})
{
    eval 'require Data::Dumper;';

    if ($@ ne "")
    {
    	die "error: $@\n";
    }
}

if ($^O eq "linux" || $^O =~ /^(open|free|net)bsd$/ || $^O eq "aix")
{
    Sys::Syslog::setlogsock ('unix');
}

elsif ($^O eq "solaris")
{
    Sys::Syslog::setlogsock ('stream');
}

openlog ("mon", "cons,pid", $CF{"SYSLOG_FACILITY"});

#
# definitions
#
die "basedir $opt{b} does not exist\n" if ($opt{"b"} && ! -d $opt{"b"});

init_globals();
init_cf_globals();

syslog_die ("config file $CF{CF} does not exist") if (! -f $CF{"CF"});

#
# read config file
#
if ((my $err = read_cf ($CF{"CF"}, 1)) ne "") {
    syslog_die ("$err");
}

closelog;

openlog ("mon", "cons,pid", $CF{"SYSLOG_FACILITY"});

#
# cmdline args override config file
#
$CF{"ALERTDIR"}  = $opt{"a"} if ($opt{"a"});
$CF{"BASEDIR"}   = $opt{"b"} if ($opt{"b"});
$CF{"AUTHFILE"}  = $opt{"A"} if ($opt{"A"});
$CF{"LOGDIR"}    = $opt{"L"} if ($opt{"L"});
$CF{"STATEDIR"}  = $opt{"D"} if ($opt{"D"});
$CF{"SCRIPTDIR"} = $opt{"s"} if ($opt{"s"});

$CF{"PIDFILE"}   = $opt{"P"} if defined($opt{"P"});	# allow empty pidfile
$CF{"MAX_KEEP"}  = $opt{"k"} if ($opt{"k"});
$CF{"MAXPROCS"}  = $opt{"m"} if ($opt{"m"});
$CF{"SERVPORT"}  = $opt{"p"} if ($opt{"p"});
$CF{"TRAPPORT"}  = $opt{"t"} if ($opt{"t"});

$SLEEPINT  = $opt{"i"} if ($opt{"i"});

if ($opt{"r"}) {
    syslog_die ("bad randstart value") if (!defined (dhmstos ($opt{"r"})));
    $CF{"RANDSTART"} = dhmstos($opt{"r"});
}

if ($opt{"S"}) {
    $STOPPED = 1;
    $STOPPED_TIME = time;
}


#
# do some path cleanups and
# build lookup tables for alerts and monitors
#
normalize_paths();
gen_scriptdir_hash();

if ($opt{"d"}) {
    debug_dir();
}

#
# load the auth control, bind, and listen
#
load_auth (1);
load_view_users(1);

#
# init client interface
#   %clients is an I/O structure, indexed by the fd of the client
#   $numclients is the number of clients currently connected
#   $iovec is fd_set for clients and traps
#
%clients = ();
$numclients = 0;
$iovec = '';
setup_server();

#
# fork and become a daemon
#
init_dtlog() if ($CF{"DTLOGGING"});
daemon() if ($opt{"f"});
if ($CF{"PIDFILE"} ne '' && open PID, ">$CF{PIDFILE}") {
    $pid_file_owner = $$;
    print PID "$pid_file_owner\n";
    close PID;
}
set_last_test ();

#
# randomize startup checks if asked to
#
randomize_startdelay() if ($CF{"RANDSTART"});

@last_alerts = ();
@last_failures = ();
readhistoricfile ();

$procs = 0;
$i=0;
$lasttm=time;
$fdset_rbits = $fdset_ebits = '';
%watch_disabled = ();

$SIG{HUP} = \&reset_server;
$SIG{INT} = \&handle_sigterm;		# for interactive debugging
$SIG{TERM} = \&handle_sigterm;
$SIG{PIPE} = 'IGNORE';

#
# load previously saved state
#
if (exists $opt{"l"}) {
    if ($opt{"l"}) {
	# If -l was given an argument (all, disabled, opstatus, etc...)
	# pass that to load_state
	load_state($opt{"l"});
    }else{
	# Otherwise default to old behavior of just loading disabled hosts/services/groups
	load_state("disabled");
    }
}



syslog ('info', "mon server started");

#
# startup alerts
#
do_startup_alerts();

#
# main monitoring loop
#
for (;;) {
debug (1, "$i" . ($STOPPED ? " (stopped)" : "") . "\n");
    $i++;
    $tm = time;

    #
    # step through the watch groups, decrementing and
    # handing expired timers
    #
    if (!$STOPPED) {
	if (defined $CF{"EXCLUDE_PERIOD"}
	    && $CF{"EXCLUDE_PERIOD"} ne "" &&
	    inPeriod (time, $CF{"EXCLUDE_PERIOD"})) {
	    debug (1, "not running monitors because of global exclude_period\n");
	} else {
	    foreach my $group (keys %watch) {
		foreach my $service (keys %{$watch{$group}}) {

		    my $sref = \%{$watch{$group}->{$service}};

		    my $t = $tm - $lasttm;
		    $t = 1 if ($t <= 0);

		    #
		    # trap timer
		    #
		    if ($sref->{"traptimeout"}) {
			$sref->{"_trap_timer"} -= $t;
			
			if ($sref->{"_trap_timer"} <= 0 && 
			    $tm - $sref->{"_last_trap"} > $sref->{"traptimeout"}) 
			  {
			      $sref->{"_trap_timer"} = $sref->{"traptimeout"};
			      handle_trap_timeout ($group, $service);
			  }
		    }

		    #
		    # trap duration timer
		    #
		    if (defined ($sref->{"_trap_duration_timer"})) {
			$sref->{"_trap_duration_timer"} -= $t;
			
			if ($sref->{"_trap_duration_timer"} <= 0) {
			    set_op_status ($group, $service, $STAT_OK);
			    undef $sref->{"_trap_duration_timer"};
			}
		    }

		    #
		    # polling monitor timer
		    #
		    if ($sref->{"interval"} && $sref->{"_timer"} <= 0 &&
			!$running{"$group/$service"})
		      {
			  if (!$CF{"MAXPROCS"} || $procs < $CF{"MAXPROCS"})
			    {
				if (defined $sref->{"exclude_period"} 
				    && $sref->{"exclude_period"} ne "" &&
				    inPeriod (time, $sref->{"exclude_period"}))
				  {
				      debug (1, "not running $group,$service because of exclude_period\n");
				  }

				elsif (($sref->{"dep_behavior"} eq "m" &&
					defined $sref->{"depend"} && $sref->{"depend"} ne "")
				       || (defined $sref->{"monitordepend"} && $sref->{"monitordepend"} ne "")) 
				  {
				      if (dep_ok ($sref, 'm'))
					{
					    run_monitor ($group, $service);
					}

				      else
					{
					    debug (1, "not running $group,$service because of depend\n");
					}
				  }

				else
				  {
				      run_monitor ($group, $service);
				  }
			    }

			  else
			    {
				syslog ('info', "throttled at $procs processes");
			    }
		      }

		    else
		      {
			  $sref->{"_timer"} -= $t;
			  if ($sref->{"_timer"} < 0)
			    {
				$sref->{"_timer"} = 0;
			    }
		      }
		}
	    }
	}
    }

    $lasttm = time;

    #
    # collect any output from subprocs
    #
    collect_output;

    #
    # clean up after exited processes, and trigger alerts
    #
    proc_cleanup;

    #
    # handle client, server, and trap I/O
    # this routine sleeps for $SLEEPINT if no I/O is ready
    #
    handle_io;
}

die "not reached";

END {
    unlink $CF{"PIDFILE"} if $$ == $pid_file_owner && $CF{"PIDFILE"} ne '';
}


##############################################################################

#
# startup alerts
#
sub do_startup_alerts {
    foreach my $group (keys %watch) {
    	foreach my $service (keys %{$watch{$group}}) {
	    do_alert ($group, $service, "", 0, $FL_STARTUPALERT);
	}
    }
}


#
# handle alert event, throttling the alert call if necessary
#
sub do_alert {
    my ($group, $service, $output, $retval, $flags) = @_;
    my (@groupargs, $last_alert, $alert);
    my ($sref, $range, @alerts);

debug (1, "do_alert flags=$flags\n");

    $sref = \%{$watch{$group}->{$service}};

    my $tmnow = time;

    if ($STOPPED) {
      syslog ("notice", "ignoring alert for $group,$service because the mon scheduler is stopped");
      return;
    }

    #
    # if redistribute it set, call it now
    #
    if ($sref->{"redistribute"} ne '') 
    {
        my ($fac, $args);
        ($fac, $args) = split (/\s+/, $sref->{"redistribute"}, 2);
        call_alert (
                    group       => $group,
                    service     => $service,
                    output      => $output,
                    retval      => $retval,
                    flags       => $flags | $FL_REDISTRIBUTE,

                    alert       => $fac,
                    args        => $args,
                   )
    }

    #
    # if the alarm is disabled, ignore it
    #
    if ((exists $watch_disabled{$group} && $watch_disabled{$group} == 1) 
	|| (defined $sref->{"disable"} && $sref->{"disable"} == 1))
    {
	syslog ("notice", "ignoring alert for $group,$service");
	return;
    }

    #
    # dependency check
    #
    if (!($flags & $FL_STARTUPALERT) &&
	!($flags & $FL_UPALERT) &&
	((defined $sref->{"depend"} && $sref->{"dep_behavior"} eq "a")
	 || (defined $sref->{"alertdepend"})))
    {
	if (!$sref->{"_depend_status"})
	{
	    debug (1, "alert for $group,$service supressed because of dep fail\n");
	    return;
	}
    }

    my ($summary) = split("\n", $output);
    $summary = "(NO SUMMARY)" if (!defined $summary || $summary =~ /^\s*$/m);
    my ($prevsumm) = split("\n", $sref->{"_failure_output"}) if (defined $sref->{"_failure_output"});
    $prevsumm = "(NO SUMMARY)" if (!defined $prevsumm || $prevsumm =~ /^\s*$/m);
    

    my $strippedsummary = $summary;
    $strippedsummary =~ s/\s//mg;
    my $strippedprevious = $prevsumm;
    $strippedprevious =~ s/\s//mg;
    # If the summary changed, un-acknowledge the service if 'unack_summary' is set
    if ($sref->{'_ack'} != 0 
	&& $sref->{'unack_summary'} == 1 
	&& $strippedsummary ne $strippedprevious
	&& !($flags & ($FL_UPALERT|$FL_ACKALERT|$FL_DISABLEALERT))) {
	print STDERR "Unacking $group/$service:\nSummary: X".$strippedsummary."X\nPrevious: X".$strippedprevious."X\n";
	$sref->{"_ack"} = 0;
	$sref->{"_ack_comment"} = "";
        $sref->{"_consec_failures"}=1;
        foreach my $period (keys %{$sref->{"periods"}})
          {
            $sref->{"periods"}->{$period}->{"_last_alert"} = 0;
#            $sref->{"periods"}->{$period}->{"_alert_sent"} = 0;
            $sref->{"periods"}->{$period}->{"_1stfailtime"} = 0;
            $sref->{"periods"}->{$period}->{"_failcount"} = 0;
          }
    }

    #
    # no alerts for ack'd failures, except for upalerts or summary changes
    # when observe_summary is set
    #
    if ($sref->{"_ack"} != 0 && !($flags & ($FL_UPALERT|$FL_ACKALERT|$FL_DISABLEALERT)))
    {
	syslog ("debug", "no alert for $group.$service" .
		" because of ack'd failure");
	return;
    }

    #
    # check each time period for pending alerts
    #
    foreach my $periodlabel (keys %{$sref->{"periods"}})
    {
	#
	# only send alerts that are in the proper period
	#
    	next if (!inPeriod ($tmnow, $sref->{"periods"}->{$periodlabel}->{"period"}));

    	my $pref = \%{$sref->{"periods"}->{$periodlabel}};

	#
	# skip upalerts/ackalerts not paired with down alerts
	# disable by setting "no_comp_alerts" in period section
	#
	if (!$pref->{"no_comp_alerts"} && ($flags & ($FL_UPALERT | $FL_ACKALERT)) && !$pref->{"_alert_sent"})
	{
	    syslog ('debug', "$group/$service/$periodlabel: Suppressing upalert since no down alert was sent.") if ($flags & $FL_UPALERT);
	    syslog ('debug', "$group/$service/$periodlabel: Suppressing ackalert since no down alert was sent.") if ($flags & $FL_ACKALERT);
	    next;
	}

        #
        # skip looping upalerts when "no_comp-alerts" set.
        #
        if ($pref->{"no_comp_alerts"} && ($flags & $FL_UPALERT) && ($pref->{"_no_comp_alerts_upalert_sent"}>0))
        {   
            next;
        }

	#
	# do this if we're not handling an upalert, startupalert, ackalert, or disablealert
	#
	if (!($flags & $FL_UPALERT) && !($flags & $FL_STARTUPALERT)  && !($flags & $FL_DISABLEALERT) && !($flags & $FL_ACKALERT))
	{
  	    #
	    # alert only when exit code matches
	    #

	    if (exists $pref->{"alertexitrange"}) {
		next if (!inRange($retval, $pref->{"alertexitrange"}));
	    }

	    #
	    # alert only numalerts
	    #
	    if ($pref->{"numalerts"} &&
	    	     $pref->{"_alert_sent"} >= $pref->{"numalerts"})
	    {
                syslog ('debug', "$group/$service/$periodlabel: Suppressing alert since numalerts is met.");
	    	next;
	    }

	    #
	    # only alert once every "alertevery" seconds, unless
	    # output from monitor is different or if strict alertevery
	    #
	    # strict and _ignore_summary are basically the same though
	    # strict short-circuits and overrides other settings and exists
	    # for compatibility with pre-1.1 configs
	    #
	    if	($pref->{"alertevery"} != 0 &&                                                                 # if alertevery is set and
		 ($tmnow - $pref->{"_last_alert"} < $pref->{"alertevery"}) &&                                  # we're within the time period and one of these:
		 (($pref->{"_alertevery_strict"}) ||                                                           # [ strict is set or
		  ($pref->{"_observe_detail"} && $sref->{"_failure_output"} eq $output) ||                     # observing detail and output hasn't changed or
		  (!$pref->{"_observe_detail"} && (!$pref->{"_ignore_summary"}) && ($prevsumm eq $summary)) || # not observing detail
		    											       # and not ignoring summary and summ hasn't changed or
		  ($pref->{"_ignore_summary"})))	                                                       # we're ignoring summary changes ]
	    {
                syslog ('debug', "$group/$service/$periodlabel: Suppressing alert for now due to alertevery.");
		next;
	    }

	    #
	    # alertafter NUM
	    #
	    if (defined $pref->{"alertafter_consec"} && ($sref->{"_consec_failures"} < $pref->{"alertafter_consec"}))
	    {
                syslog ('debug', "$group/$service/$periodlabel: Suppressing alert for now due to alertafter consecutive failures.");
	    	next;
	    }

	    #
	    # alertafter timeval
	    #
	    elsif ( (!defined ($pref->{"alertafter"})) && (defined ($pref->{"alertafterival"})) )
	    {
	    	$pref->{'_1stfailtime'} = $tmnow if $pref->{'_1stfailtime'} == 0;
		if ($tmnow - $pref->{'_1stfailtime'} <= $pref->{'alertafterival'})
		{
                    syslog ('debug', "$group/$service/$periodlabel: Suppressing alert for now due to alertafter numval.");
		    next;
		}
	    }

	    #
	    # alertafter NUM timeval
	    #
	    elsif (defined ($pref->{"alertafter"}))
	    {
		$pref->{"_failcount"}++;

		if ($tmnow - $pref->{'_1stfailtime'} <= $pref->{'alertafterival'} &&
		    $pref->{"_failcount"} < $pref->{"alertafter"})
		{
                    syslog ('debug', "$group/$service/$periodlabel: Suppressing alert for now due to alertafter num timeval.");
		    next;
		}

		#
		# start a new time interval
		#
		if ($tmnow - $pref->{'_1stfailtime'} > $pref->{'alertafterival'})
		{
		    $pref->{"_failcount"} = 1;
		}

		if ($pref->{"_failcount"} == 1)
		{
		    $pref->{"_1stfailtime"} = $tmnow;
		}

		if ($pref->{"_failcount"} < $pref->{"alertafter"})
		{
                    syslog ('debug', "$group/$service/$periodlabel: Suppressing alert for now due to alertafter num timeval.");
		    next;
		}
	    }
	}

	#
	# at this point, no alerts are blocked,
	# so send the alerts
	#

	#
	# trigger multiple alerts in this period
	#
	if ($flags & $FL_UPALERT)
	{
	    @alerts = @{$pref->{"upalerts"}};
	}
	elsif ($flags & $FL_STARTUPALERT)
	{
	    @alerts = @{$pref->{"startupalerts"}};
	}
	elsif ($flags & $FL_DISABLEALERT)
	{
	    @alerts = @{$pref->{"disablealerts"}};
	}
	elsif ($flags & $FL_ACKALERT)
	{
	    @alerts = @{$pref->{"ackalerts"}};
	}
	else
	{
	    @alerts = @{$pref->{"alerts"}};
	}

	my $called = 0;

	for (my $i=0;$i<@alerts;$i++)
	{
	    my ($range, $fac, $args);

	    if ($alerts[$i] =~ /^exit\s*=\s*((\d+|\d+-\d+))\s/i)
	    {
		$range=$1;
		next if (!inRange($retval, $range));
		($fac, $args) = (split (/\s+/, $alerts[$i], 3))[1,2];
	    }
	    else
	    {
		($fac, $args) = split (/\s+/, $alerts[$i], 2);
	    }

	    $called++ if (call_alert (
		    group	=> $group,
		    service	=> $service,
		    output	=> $output,
		    retval	=> $retval,
		    flags	=> $flags,

		    pref	=> $pref,
		    alert	=> $fac,
		    args	=> $args,
		)
	    );
	}

	#
	# reset _alert_sent if up alert was sent from a trap
	#
        if ($called)
        {
            if( (($FL_TRAP | $flags) && ($FL_UPALERT & $flags)) ) {
	        $pref->{"_alert_sent"} = 0;
                $pref->{"_last_alert"} = 0;
            }
            else {
                $pref->{"_alert_sent"}++;

                #
                # reset _no_comp_alerts_upalert_sent counter - when service will be
                # back up, upalert will be sent.
                #
                if ($pref->{"no_comp_alerts"}) {
                    $pref->{"_no_comp_alerts_upalert_sent"} = 0;
                }
            }

	    if ($pref->{"no_comp_alerts"} && ($flags & $FL_UPALERT)) {
		$pref->{"_no_comp_alerts_upalert_sent"}++;
	    }
        }
    }
}



#
# walk through the watch list and reset the time
# the service was last called
#
sub set_last_test {
    my ($i, $k, $t);
    $t = time;
    foreach $k (keys %watch)
    {
    	foreach my $service (keys %{$watch{$k}})
	{
	    $watch{$k}->{$service}->{"_timer"} = $watch{$k}->{$service}->{"interval"};
	}
    }

}


#
# parse configuration file
#
# build the following data structures:
#
# %group
#       each element of %group is an array of hostnames
#       group records are terminated by a blank line in the
#       configuration file
# %watch{"group"}->{"service"}->{"variable"} = value
# %alias
#
sub read_cf {
    my ($CF, $commit) = @_;
    my ($var, $watchgroup, $ingroup, $curgroup, $inwatch,
	$args, $hosts, %disabled, $h, $i,
	$inalias, $curalias, $inview, $curview);
    my ($sref, $pref);
    my ($service, $period);
    my ($authtype, @authtypes);
    my $line_num = 0;

    #
    # parse configuration file
    #
    if (exists($opt{"M"}) || $CF =~ /\.m4$/)
    {
        my $m4 = "m4";
	$m4 = $opt{"M"} if (defined($opt{"M"}));
	return "could not open m4 pipe of cf file: $CF: $!"
	    if (!open (CFG, "$m4 $CF |"));
    }

    else
    {
	return "could not open cf file: $CF: $!"
	    if (!open (CFG, $CF));
    }

    #
    # buffers to hold the new un-committed config
    #
    my %new_alias = ();
    my %new_views = ();
    my %new_CF = %CF;
    my %new_groups;
    my %new_watch;

    my %is_watch;

    my $servnum = 0;

    my $DEP_BEHAVIOR = "a";
    my $DEP_MEMORY = 0;
    my $UNACK_SUMMARY = 0;

    my $incomplete_line = 0;
    my $linepart = "";
    my $l = "";
    my $acc_line = "";

    for (;;)
    {
	#
	# read in a logical "line", which may span actual lines
	#
	do
	{
	    $line_num++;
	    last if (!defined ($linepart = <CFG>));
	    next if $linepart =~ /^\s*#/;

	    #
	    # accumulate multi-line lines (ones which are \-escaped)
	    #
	    if ($incomplete_line) { $linepart =~ s/^\s*//; }

	    if ($linepart =~ /^(.*)\\\s*$/)
	    {
		$incomplete_line = 1;
		$acc_line .= $1;
		chomp $acc_line;
		next;
	    }

	    else
	    {
		$acc_line .= $linepart;
	    }

	    $l = $acc_line;
	    $acc_line = "";

	    chomp $l;
	    $l =~ s/^\s*//;
	    $l =~ s/\s*$//;

	    $incomplete_line = 0;
	    $linepart = "";
	};

	#
	# global variables which can be overriden by the command line
	#
	if (!$inwatch && $l =~ /^(\w+) \s* = \s* (.*) \s*$/ix)
	{
	    if ($1 eq "alertdir") {
		$new_CF{"ALERTDIR"} = $2;

	    } elsif ($1 eq "basedir") {
		$new_CF{"BASEDIR"} = $2;
		$new_CF{"BASEDIR"} = "$PWD/$new_CF{BASEDIR}" if ($new_CF{"BASEDIR"} !~ m{^/});
		$new_CF{"BASEDIR"} =~ s{/$}{};

	    } elsif ($1 eq "cfbasedir") {
		$new_CF{"CFBASEDIR"} = $2;
		$new_CF{"CFBASEDIR"} = "$PWD/$new_CF{CFBASEDIR}" if ($new_CF{"CFBASEDIR"} !~ m{^/});
		$new_CF{"CFBASEDIR"} =~ s{/$}{};

	    } elsif ($1 eq "mondir") {
		$new_CF{"SCRIPTDIR"} = $2;

	    } elsif ($1 eq "logdir") {
		$new_CF{"LOGDIR"} = $2;

	    } elsif ($1 eq "histlength") {
		$new_CF{"MAX_KEEP"} = $2;

	    } elsif ($1 eq "serverport") {
		$new_CF{"SERVPORT"} = $2;

	    } elsif ($1 eq "trapport") {
		$new_CF{"TRAPPORT"} = $2;

	    } elsif ($1 eq "serverbind") {
	    	$new_CF{"SERVERBIND"} = $2;

	    } elsif ($1 eq "clientallow") {
		$new_CF{"CLIENTALLOW"}= $2;

	    } elsif ($1 eq "trapbind") {
	    	$new_CF{"TRAPBIND"} = $2;

	    } elsif ($1 eq "pidfile") {
		$new_CF{"PIDFILE"} = $2;

	    } elsif ($1 eq "randstart") {
		$new_CF{"RANDSTART"} = dhmstos($2);
		if (!defined ($new_CF{"RANDSTART"})) {
		    close (CFG);
		    return "cf error: bad value '$2' for randstart option (syntax: randstart = timeval), line $line_num";
		}

	    } elsif ($1 eq "maxprocs") {
		$new_CF{"MAXPROCS"} = $2;

	    } elsif ($1 eq "statedir") {
		$new_CF{"STATEDIR"} = $2;

	    } elsif ($1 eq "authfile") {
		$new_CF{"AUTHFILE"} = $2;
                if (! -r $new_CF{"AUTHFILE"}) {
                    close (CFG);
                    return "cf error: authfile '$2' does not exist or is not readable, line $line_num";
                }

	    } elsif ($1 eq "authtype") {
		$new_CF{"AUTHTYPE"} = $2;
		@authtypes = split(' ' , $new_CF{"AUTHTYPE"}) ;
		foreach $authtype (@authtypes) {
		    if ($authtype eq "pam") {
			eval 'use Authen::PAM qw(:constants);' ;
			if ($@ ne "") {
			    close (CFG);
			    return "cf error: could not use PAM authentication: $@";
			}
		    }
		}

	    } elsif ($1 eq "pamservice") {
		$new_CF{"PAMSERVICE"} = $2;

	    } elsif ($1 eq "userfile") {
		$new_CF{"USERFILE"} = $2;
                if (! -r $new_CF{"USERFILE"}) {
                    close (CFG);
                    return "cf error: userfile '$2' does not exist or is not readable, line $line_num";
                }

	    } elsif ($1 eq "historicfile") {
	    	$new_CF{"HISTORICFILE"} = $2;

	    } elsif ($1 eq "historictime") {
	    	$new_CF{"HISTORICTIME"} = dhmstos($2);
		if (!defined $new_CF{"HISTORICTIME"}) {
		    close (CFG);
		    return "cf error: bad value '$2' for historictime command (syntax: historictime = timeval), line $line_num";
		}

	    } elsif ($1 eq "cltimeout") {
		$new_CF{"CLIENT_TIMEOUT"} = dhmstos($2);
		if (!defined ($new_CF{"CLIENT_TIMEOUT"})) {
		    close (CFG);
		    return "cf error: bad value '$2' for cltimeout command (syntax: cltimeout = secs), line $line_num";
		}

	    } elsif ($1 eq "monerrfile") {
	    	$new_CF{"MONERRFILE"} = $2;

	    } elsif ($1 eq "dtlogfile") {
		$new_CF{"DTLOGFILE"} = $2;

	    } elsif ($1 eq "dtlogging") {
		$new_CF{"DTLOGGING"} = 0;
		if ($2 == 1 || $2 eq "yes" || $2 eq "true") {
		    $new_CF{"DTLOGGING"} = 1;
		}

	    } elsif ($1 eq "dep_recur_limit") {
	    	$new_CF{"DEP_RECUR_LIMIT"} = $2;

	    } elsif ($1 eq "dep_behavior") {
		if ($2 ne "m" && $2 ne "a" && $2 ne "hm") {
		    close (CFG);
		    return "cf error: unknown dependency behavior '$2', line $line_num";
		}
		$DEP_BEHAVIOR = $2;

	    } elsif ($1 eq "dep_memory") {
		my $memory = dhmstos($2);
		if (!defined $memory) {
		    close (CFG);
		    return "cf error: bad value '$2' for dep_memory option (syntax: dep_memory = timeval), line $line_num";
		}
		$DEP_MEMORY = $memory;

	    } elsif ($1 eq "unack_summary") {
		if (defined $2) {
		    if ($2 =~ /y(es)?/i) {
			$UNACK_SUMMARY = 1;
		    } elsif ($2 =~ /n(o)?/i) {
			$UNACK_SUMMARY = 0;
		    } elsif ($2 eq "0" || $2 eq "1") {
			$UNACK_SUMMARY = $2;
		    } else {
			return "cf error: invalid unack_summary value '$2' (syntax: unack_summary [0|1|y|yes|n|no])";
		    }
		} else {
		    $UNACK_SUMMARY = 1;
		}

	    } elsif ($1 eq "syslog_facility") {
	    	$new_CF{"SYSLOG_FACILITY"} = $2;

	    } elsif ($1 eq "startupalerts_on_reset") {
		if ($2 =~ /^1|yes|true|on$/i) {
		    $new_CF{"STARTUPALERTS_ON_RESET"} = 1;
		} else {
		    $new_CF{"STARTUPALERTS_ON_RESET"} = 0;
		}

	    } elsif ($1 eq "monremote") {
		$new_CF{"MONREMOTE"} = $2;
		
	    } elsif ($1 eq "exclude_period") {
		if (inPeriod (time, $2) == -1)
		  {
		      close (CFG);
		      return "cf error: malformed exclude_period '$2' (the specified time period is not valid as per Time::Period::inPeriod), line $line_num";
		  }
		$new_CF{"EXCLUDE_PERIOD"} = $2;
	    } else {
		close (CFG);
		return "cf error: unknown variable '$1', line $line_num";
	    }

	    next;
	}

	#
	# end of record
	#
	if ($l eq "")
	{
	    $ingroup    = 0;
	    $inalias	= 0;
	    $inwatch    = 0;
	    $period	= 0;
	    $inview     = 0;

	    $curgroup   = "";
	    $curalias	= "";
	    $watchgroup = "";

	    $servnum	= 0;
	    next;
	}

	#
	# hostgroup record
	#
	if ($l =~ /^hostgroup\s+([a-zA-Z0-9_.-]+)\s*(.*)/)
	{
	    $curgroup = $1;

	    $ingroup = 1;
	    $inview = 0;
	    $inalias = 0;
	    $inwatch = 0;
	    $period  = 0;


	    $hosts = $2;
	    %disabled = ();

	    foreach $h (grep (/^\*/, @{$groups{$curgroup}}))
	    {
		# We have to make $i = $h because $h is actually
		# a pointer to %groups and will modify it.
		$i = $h;
		$i =~ s/^\*//;
		$disabled{$i} = 1;
	    }

	    @{$new_groups{$curgroup}} = split(/\s+/, $hosts);

	    #
	    # keep hosts which were previously disabled
	    #
	    for ($i=0;$i<@{$new_groups{$curgroup}};$i++)
	    {
		$new_groups{$curgroup}[$i] = "*$new_groups{$curgroup}[$i]"
		    if ($disabled{$new_groups{$curgroup}[$i]});
	    }

	    next;
	}

	if ($ingroup)
	{
	    push (@{$new_groups{$curgroup}}, split(/\s+/, $l));

	    for ($i=0;$i<@{$new_groups{$curgroup}};$i++)
	    {
		$new_groups{$curgroup}[$i] = "*$new_groups{$curgroup}[$i]"
		    if ($disabled{$new_groups{$curgroup}[$i]});
	    }

	    next;
	}

	#
	# alias record
	#
	if ($l =~ /^alias\s+([a-zA-Z0-9_.-]+)\s*$/)
	{
	    $inalias = 1;
	    $inview = 0;
	    $ingroup = 0;
	    $inwatch = 0;
	    $period  = 0;

	    $curalias = $1;
	    next;
	}

	if ($inalias)
	{
	    if ($l =~ /\A(.*)\Z/)
	    {
		push (@{$new_alias{$curalias}}, $1);
		next;
	    }
	}

	#
	# view record
	#
	if ($l =~ /^view\s+([a-zA-Z0-9_.-]+)\s+(.*)$/)
	{
	    $inview = 1;
	    $inalias = 0;
	    $ingroup = 0;
	    $inwatch = 0;
	    $period  = 0;

	    $curview = $1;
            $new_views{$curview}={};

	    foreach (split(/\s+/, $2)) {
		$new_views{$curview}->{$_} = 1;
	    };
	    next;
	}
	
	if ($inview)
	{
	    foreach (split(/\s+/, $l)) {
		$new_views{$curview}->{$_} = 1;
	    };
	    next;
	}

	#
	# watch record
	#
	if ($l =~ /^watch\s+([a-zA-Z0-9_.-]+)\s*/)
	{
	    $watchgroup = $1;
	    $inwatch = 1;
	    $inview = 0;
	    $inalias = 0;
	    $ingroup = 0;
	    $period  = 0;

	    if (!defined ($new_groups{$watchgroup}))
	    {
		#
		# This hostgroup doesn't exist yet, we'll create it and warn
		#
	    	@{$new_groups{$watchgroup}} = ($watchgroup);
		print STDERR "Warning: watch group $watchgroup defined with no corresponding hostgroup.\n";
	    }
	    if ($new_watch{$watchgroup})
	    {
		close (CFG);
		return "cf error: watch '$watchgroup' already defined, line $line_num";
	    }

	    $curgroup   = "";
	    $service = "";

	    next;
	}

	if ($inwatch)
	{
	    #
	    # env variables
	    #
	    if ($l =~ /^([A-Z_][A-Z0-9_]*)=(.*)/)
	    {
		if ($service eq "") {
		    close (CFG);
		    return "cf error: environment variable defined without a service, line $line_num";
		}
		$new_watch{$watchgroup}->{$service}->{"ENV"}->{$1} = $2;

		next;
	    }

	    #
	    # non-env variables
	    #
	    else
	    {
		$l =~ /^(\w+)\s*(.*)$/;
		$var = $1;
		$args = $2;
	    }

	    #
	    # service entry
	    #
	    if ($var eq "service")
	    {
		$service = $args;

		if ($service !~ /^[a-zA-Z0-9_.-]+$/) {
		    close (CFG);
		    return "cf error: invalid service tag '$args', line $line_num";
		}

		elsif (exists $new_watch{$watchgroup}->{$service})
		{
		    close (CFG);
		    return "cf error: service $service already defined for watch group $watchgroup, line $line_num";
		}

		$period = 0;
		$sref = \%{$new_watch{$watchgroup}->{$service}};
		$sref->{"service"} = $args;
		$sref->{"interval"} = undef;
		$sref->{"randskew"} = 0;
                $sref->{"redistribute"} = "";
		$sref->{"dep_behavior"} = $DEP_BEHAVIOR;
		$sref->{"dep_memory"} = $DEP_MEMORY;
		$sref->{"exclude_period"} = "";
		$sref->{"exclude_hosts"} = {};
		$sref->{"_op_status"} = $STAT_UNTESTED;
		$sref->{"_last_op_status"} = $STAT_UNTESTED;
		$sref->{"_ack"} = 0;
		$sref->{"_ack_comment"} = '';
		$sref->{"unack_summary"} = $UNACK_SUMMARY;
		$sref->{"_consec_failures"} = 0;
		$sref->{"_failure_count"} = 0 if (!defined($sref->{"_failure_count"}));
		$sref->{"_start_of_monitor"} = time if (!defined($sref->{"_start_of_monitor"}));
		$sref->{"_alert_count"} = 0 if (!defined($sref->{"_alert_count"}));
		$sref->{"_last_failure"} = 0 if (!defined($sref->{"_last_failure"}));
		$sref->{"_last_success"} = 0 if (!defined($sref->{"_last_success"}));
		$sref->{"_last_trap"} = 0 if (!defined($sref->{"_last_trap"}));
		$sref->{"_last_traphost"} = '' if (!defined($sref->{"_last_traphost"}));
		$sref->{"_exitval"} = "undef" if (!defined($sref->{"_exitval"}));
		$sref->{"_last_check"} = undef;
		#
		# -1 for _monitor_duration means no monitor has been run yet
		# so there is no duration data available
		#
		$sref->{"_monitor_duration"} = -1;
		$sref->{"_monitor_running"} = 0;
		$sref->{"_depend_status"} = undef;
		$sref->{"failure_interval"} = undef;
		$sref->{"_old_interval"} = undef;
		next;
	    }

	    if ($service eq "")
	    {
		close (CFG);
		return "cf error: need to specify service in watch record, line $line_num";
	    }


	    #
	    # period definition
	    #
	    # for each service there can be one or more alert periods
	    # this is stored as an array of hashes named
	    #     %{$watch{$watchgroup}->{$service}->{"periods"}}
	    # each index for this hash is a unique tag for the period as
	    # defined by the user or named after the period (such as
	    # "wd {Mon-Fri} hr {7am-11pm}")
	    #
	    # the value of the hash is an array containing the list of alert commands
	    # and arguments, so
	    #
	    # @alerts = @{$watch{$watchgroup}->{$service}->{"periods"}->{"TAG"}}
	    #
	    if ($var eq "period")
	    {
		$period = 1;

		my $periodstr;

		if ($args =~ /^([a-z_]\w*) \s* : \s* (.*)$/ix)
		{
		    $periodstr = $1;
		    $args = $2;
		}

		else
		{
		    $periodstr = $args;
		}

		if (exists $sref->{"periods"}->{$periodstr})
		{
		    close (CFG);
		    return "cf error: period '$periodstr' already defined for watch group $watchgroup service $service, line $line_num";
		}

		$pref = \%{$sref->{"periods"}->{$periodstr}};

		if (inPeriod (time, $args) == -1)
		{
		    close (CFG);
		    return "cf error: malformed period '$args' (the specified time period is not valid as per Time::Period::inPeriod), line $line_num";
		}

		$pref->{"period"} = $args;
		$pref->{"alertevery"} = 0;
		$pref->{"numalerts"} = 0;
		$pref->{"_alert_sent"} = 0;
		$pref->{"no_comp_alerts"} = 0;
		$pref->{"_no_comp_alerts_upalert_sent"} = 0;
		@{$pref->{"alerts"}} = ();
		@{$pref->{"upalerts"}} = ();
		@{$pref->{"ackalerts"}} = ();
		@{$pref->{"disablealerts"}} = ();
		@{$pref->{"startupalerts"}} = ();
		next;
	    }

	    #
	    # period variables
	    #
	    if ($period)
	    {
		if ($var eq "alert")
		{
		    push @{$pref->{"alerts"}}, $args;
		}
		
		elsif ($var eq "ackalert")
		{
		    push @{$pref->{"ackalerts"}}, $args;
		}
		
		elsif ($var eq "disablealert")
		{
		    push @{$pref->{"disablealerts"}}, $args;
		}
		
		elsif ($var eq "upalert")
		{
		    $sref->{"_upalert"} = 1;
		    push @{$pref->{"upalerts"}}, $args;
		}

		elsif ($var eq "startupalert")
		{
		    push @{$pref->{"startupalerts"}}, $args;
		}

		elsif ($var eq "alertevery")
		{
		    $pref->{"_observe_detail"} = 0;
		    $pref->{"_alertevery_strict"} = 0;
		    $pref->{"_ignore_summary"} = 0;

		    if ($args =~ /(\S+) \s+ observe_detail \s*$/ix)
		    {
			$pref->{"_observe_detail"} = 1;
			$args = $1;
		    }

		    elsif ($args =~ /(\S+) \s+ ignore_summary \s*$/ix)
		    {
			$pref->{"_ignore_summary"} = 1;
			$args = $1;
		    }

		    #
		    # for backawards-compatibility with <= 0.38.21
		    #
		    elsif ($args =~ /(\S+) \s+ summary/ix)
		    {
			$args = $1;
		    }

		    #
		    # strict
		    #
		    elsif ($args =~ /(\S+) \s+ strict \s*$/ix)
		    {
			$pref->{"_alertevery_strict"} = 1;
		    	$args = $1;
		    }

		    if (!($args = dhmstos ($args))) {
			close (CFG);
			return "cf error: invalid time interval '$args' (syntax: alertevery {positive number}{smhd} [ strict | observe_detail | ignore_summary ]), line $line_num";
		    }

		    $pref->{"alertevery"} = $args;
		    next;
		}

		elsif ($var eq "alertafter")
		{
		    my ($p1, $p2);

		    #
		    # alertafter NUM
		    #
		    if ($args =~ /^(\d+)$/)
		    {
			$p1 = $1;
			$pref->{"alertafter_consec"} = $p1;
		    }

		    #
		    # alertafter timeval
		    #
		    elsif ($args =~ /^(\d+[hms])$/)
		    {
			$p1 = $1;
			if (!($p1 = dhmstos ($p1)))
			{
			    close (CFG);
			    return "cf error: invalid time interval '$args' (syntax: alertafter = [{positive integer}] [{positive number}{smhd}]), line $line_num";
			}

			$pref->{"alertafterival"} = $p1;
			$pref->{"_1stfailtime"} = 0;
		    }

		    #
		    # alertafter NUM timeval
		    #
		    elsif ($args =~ /(\d+)\s+(\d+[hms])$/)
		    {
			($p1, $p2) = ($1, $2);
			if (($p1 - 1) * $sref->{"interval"} >= dhmstos($p2))
			{
			    close (CFG);
			    return "cf error:  interval & alertafter not sensible. No alerts can be generated with those parameters, line $line_num";
			}
			$pref->{"alertafter"} = $p1;
			$pref->{"alertafterival"} = dhmstos ($p2);

			$pref->{"_1stfailtime"} = 0;
			$pref->{"_failcount"} = 0;
		    }

		    else
		    {
			close (CFG);
			return "cf error: invalid interval specification '$args', line $line_num";
		    }
		}

		elsif ($var eq "upalertafter")
		{
		    if (!($args = dhmstos ($args))) {
			close (CFG);
			return "cf error: invalid upalertafter specification '$args' (syntax: upalertafter = {positive number}{smhd}), line $line_num";
		    }

		    $pref->{"upalertafter"} = $args;
		}

		elsif ($var eq "numalerts")
		{
		    if ($args !~ /^\d+$/) {
			close (CFG);
			return "cf error: -numeric arg '$args' (syntax: numalerts = {positive integer}, line $line_num";
		    }
		    $pref->{"numalerts"} = $args;
		    next;
		}

		elsif ($var eq "no_comp_alerts")
		{
		    $pref->{"no_comp_alerts"} = 1;
		    next;
		}

		elsif ($var eq "alerts_dont_count")
		{
		    $pref->{"alerts_dont_count"} = 1;
		    next;
		}

		elsif ($var eq 'alertexitrange') {
		  if ($args !~ /^\s*(\d+|\d+-\d+)\s*$/) {
		    close (CFG);
		    return "cf error: invalid exit code range '$args', line $line_num";
		  }
		  $pref->{"alertexitrange"} = $args;
		}

		else
		{
		    close (CFG);
		    return "cf error: unknown syntax [$l], line $line_num";
		}
		
	    }

	    #
	    # non-period variables
	    #
	    elsif (!$period)
	    {
		if ($var eq "interval")
		{
		    if (!($args = dhmstos ($args))) {
			close (CFG);
			return "cf error: invalid time interval '$args' (syntax: interval = {positive number}{smhd}), line $line_num";
		    }
		}

		elsif ($var eq "failure_interval")
		{
		    if (!($args = dhmstos ($args))) {
			close (CFG);
			return "cf error: invalid interval '$args' (syntax: failure_interval = {positive number}{smhd}), line $line_num";
		    }
		}

		elsif ($var eq "monitor")
		{
		    # valid
		}

                elsif ($var eq "redistribute")
                {
                    # valid
                }

		elsif ($var eq "allow_empty_group")
		{
		    # valid
		}

		elsif ($var eq "description")
		{
		    # valid
		}

		elsif ($var eq "unack_summary")
		{
		    if (defined $args) {
			if ($args =~ /y(es)?/i) {
			    $args = 1;
			} elsif ($args =~ /n(o)?/i) {
			    $args = 0;
			}
			if ($args eq "0" || $args eq "1") {
			    $sref->{"unack_summary"} = $args;
			} else {
			    return "cf error: invalid unack_summary value '$args' (syntax: unack_summary [0|1|y|yes|n|no])";
			}
		    } else {
			$sref->{"unack_summary"} = 1;
		    }
		    next;
		}

		elsif ($var eq "traptimeout")
		{
		    if (!($args = dhmstos ($args))) {
			close (CFG);
			return "cf error: invalid traptimeout interval '$args' (syntax: traptimeout = {positive number}{smhd}), line $line_num";
		    }
		    $sref->{"_trap_timer"} = $args;
		}

		elsif ($var eq "trapduration")
		{
		    if (!($args = dhmstos ($args))) {
			close (CFG);
			return "cf error: invalid trapduration interval '$args' (syntax: trapduration = {positive number}{smhd}), line $line_num";
		    }
		}

		elsif ($var eq "randskew")
		{
		    if (!($args = dhmstos ($args))) {
			close (CFG);
			return "cf error: invalid randskew time interval '$args' (syntax: randskew = {positive number}{smhd}), line $line_num";
		    }
		}

		elsif ($var eq "dep_behavior")
		{
		    if ($args ne "m" && $args ne "a" && $args ne "hm")
		    {
			close (CFG);
			return "cf error: unknown dependency behavior '$args' (syntax: dep_behavior = {m|a}), line $line_num";
		    }
		}
 
		elsif ($var eq "dep_memory")
		{
		    my $timeval = dhmstos($args);
		    if (!$timeval) {
  		        close (CFG);
			return "cf error: bad value '$args' for dep_memory option (syntax: dep_memory = timeval), line $line_num";
		    }
		    $args = $timeval;
		}

		elsif ($var eq "depend")
		{
		    $args =~ s/SELF:/$watchgroup:/g;
		}

		elsif ($var eq "alertdepend")
		{
		    $args =~ s/SELF:/$watchgroup:/g;
		}

		elsif ($var eq "monitordepend")
		{
		    $args =~ s/SELF:/$watchgroup:/g;
		}

		elsif ($var eq "hostdepend")
		{
		    $args =~ s/SELF:/$watchgroup:/g;
		}

		elsif ($var eq "exclude_hosts")
		{
		    my $ex = {};
		    foreach my $h (split (/\s+/, $args))
		    {
			$ex->{$h} = 1;
		    }
		    $args = $ex;
		}

		elsif ($var eq "exclude_period")
		{
		    if (inPeriod (time, $args) == -1)
		    {
			close (CFG);
			return "cf error: malformed exclude_period '$args' (the specified time period is not valid as per Time::Period::inPeriod), line $line_num";
		    }
		}

		else
		{
		    close (CFG);
		    return "cf error: unknown syntax [$l], line $line_num";
		}

		$sref->{$var} = $args;
	    }

	    else
	    {
		close (CFG);
		return "cf error: unknown syntax outside of period section [$l], line $line_num";
	    }
	}

	next;
    }

    close (CFG) || return "Could not open pipe to m4 (check that m4 is properly installed and in your PATH): $!";

    #
    # Go through each defined hostgroup and check that there is a 
    #  watch associated with that hostgroup record.
    #
    # hostgroups without associated watches are not a violation of 
    #  mon config syntax, but it's usually not what you want.
    #
    for (keys(%new_watch)) { $is_watch{$_} = 1 };
    foreach $watchgroup ( keys (%new_groups) ) {
	print STDERR "Warning: hostgroup $watchgroup has no watch assigned to it!\n" unless $is_watch{$watchgroup};
    }

    #
    # no errors, commit new config if $commit was specified
    #
    return "" unless $commit;
    %views = %new_views;
    %alias = %new_alias;
    %groups = %new_groups;
    %watch = %new_watch;
    %CF = %new_CF;

    "";
}


#
# convert a string like "20m" into seconds
#
sub dhmstos {
    my ($str) = @_;
    my ($s);

    $str = lc ($str);

    if ($str =~ /^\s*(\d+(?:\.\d+)?)([dhms])\s*$/i) {
	if ($2 eq "m") {
	    $s = $1 * 60;
	} elsif ($2 eq "h") {
	    $s = $1 * 60 * 60;
	} elsif ($2 eq "d") {
	    $s = $1 * 60 * 60 * 24;
	} else {
	    $s = $1;
	}
    } else {
    	return undef;
    }
    $s;
}


#
# reset the state of the server on SIGHUP, and reread config
# file.
#
sub reset_server {
    my ($keepstate) = @_;

    #
    # reap children that may be running
    #
    foreach my $pid (keys %runningpid) {
	my ($group, $service) = split (/\//, $runningpid{$pid});
    	kill 15, $pid;
	waitpid ($pid, 0);
	syslog ('info', "reset killed child $pid, exit status $?");
	remove_proc ($pid);
    }

    $procs = 0;
    save_state ("all") if ($keepstate);
    syslog ('info', "resetting, and re-reading configuration $CF{CF}");

    if ((my $err = read_cf ($CF{"CF"}, 1)) ne "") {
    	syslog ('err', "error reading config file: $err");
	return undef;
    }

    normalize_paths;
    gen_scriptdir_hash;
    $lasttm=time; # the last time(2) the loop started
    $fdset_rbits = $fdset_ebits = '';
    set_last_test ();
    randomize_startdelay() if ($CF{"RANDSTART"});
    load_state ("all") if ($keepstate);
    if ($CF{"DTLOGGING"}) {
	init_dtlog();
    }

    readhistoricfile;

    if ($CF{"STARTUPALERTS_ON_RESET"}) {
    	do_startup_alerts;
    }

    return 1;
}


sub init_dtlog {
    my $t = time;

    return if (!$CF{"DTLOGGING"});

    if (!open (DTLOG, ">>$CF{DTLOGFILE}")) {
       syslog ('err', "could not append to $CF{DTLOGFILE}: $!");
       $CF{"DTLOGGING"} = 0;
    } else {
       $CF{"DTLOGGING"} = 1;
       print DTLOG <<EOF;
#
# downtime log start $t
# time back up, group, service, first failure, downtime, interval, summary
#
EOF
    	close (DTLOG);
    }
}


#
# remove a process from our state
#
sub remove_proc {
    my ($pid) = @_;

    return if (!defined $runningpid{$pid});

    vec ($fdset_rbits, fileno($fhandles{$runningpid{$pid}}), 1) = 0;
    close ($fhandles{$runningpid{$pid}});
    delete $fhandles{$runningpid{$pid}};
    delete $running{$runningpid{$pid}};
    delete $runningpid{$pid};
    $procs--;
}


#
# exit on SIGTERM
#
sub handle_sigterm {
    syslog ("info", "caught TERM signal, exiting");
    exit (1);
}


#
# set O_NONBLOCK and FD_CLOEXEC on the given filehandle
#
sub configure_filehandle {
    my ($fh) = @_;
    my ($fl);

    $fl = '';
    $fl = fcntl ($fh, F_GETFL, $fl)          || return;
    $fl |= O_NONBLOCK;
    fcntl ($fh, F_SETFL, $fl)          || return;

    $fl = fcntl ($fh, F_GETFD, 0)      || return;
    $fl |= FD_CLOEXEC;
    fcntl ($fh, F_SETFD, $fl)          || return;

    return 1;
}


#
# setup server
#
sub setup_server {
    my ($tcpproto, $udpproto, $fl);

    if (!defined ($tcpproto = getprotobyname ('tcp')))
    {
    	die_die ("err", "could not get protocol for tcp");
    }

    if (!defined ($udpproto = getprotobyname ('udp')))
    {
    	die_die ("err", "could not get protocol for tcp");
    }

    #
    # client server, such as moncmd
    #
    my $bindaddr;
    if (defined $CF{"SERVERBIND"})
    {
	if (!($bindaddr = gethostbyname ($CF{"SERVERBIND"})))
	{
	    die_die ("err", "error returned by gethostbyname for serverbind: $?");
	}
    }

    else
    {
    	$bindaddr = INADDR_ANY;
    }

    socket (SERVER, PF_INET, SOCK_STREAM, $tcpproto) ||
    	die_die ("err", "could not create TCP socket: $!");

    setsockopt (SERVER, SOL_SOCKET, SO_REUSEADDR, pack ("l", 1)) ||
    	die_die ("err", "could not setsockopt: $!");

    bind (SERVER, sockaddr_in ($CF{"SERVPORT"}, $bindaddr)) ||
    	die_die ("err", "could not bind TCP server port $CF{'SERVPORT'}: $!");

    listen (SERVER, SOMAXCONN);

    configure_filehandle (*SERVER) ||
    	die_die ("err", "could not configure TCP server port: $!");

    #
    # remote monitor traps
    #
    if (defined $CF{"TRAPBIND"})
    {
	if (!($bindaddr = gethostbyname ($CF{"TRAPBIND"})))
	{
	    die_die ("err", "error returned by gethostbyname for trapbind: $?");
	}
    }

    else
    {
    	$bindaddr = INADDR_ANY;
    }

    socket (TRAPSERVER, PF_INET, SOCK_DGRAM, $udpproto) ||
    	die_die ("err", "could not create UDP socket: $!");
    bind (TRAPSERVER, sockaddr_in ($CF{"TRAPPORT"}, $bindaddr)) ||
    	die_die ("err", "could not bind UDP server port: $!");
    configure_filehandle (*TRAPSERVER) ||
    	die_die ("err", "could not configure UDP trap port: $!");
}


#
# set up a client connection if necessary
#
sub client_accept {
    my ($rin, $rout, $n, $sock, $port, $addr, $fl);

    my $CLIENT = new FileHandle;

    if (!defined ($sock = accept ($CLIENT, SERVER))) {
    	syslog ('err', "accept returned error: $!");
	return;
    }

debug(1, "accepted client $CLIENT\n");
    my $fno = fileno ($CLIENT);

    #
    # set socket to nonblocking
    #
    if (!configure_filehandle ($CLIENT)) {
    	syslog ("err", "could not configure for client: $!");
	close ($CLIENT);
	return;
    }

    ($port, $addr) = unpack_sockaddr_in ($sock);
    my $clientip = inet_ntoa($addr);

    syslog ('info', "client connection from $clientip:$port");

    my @clientregex = split(' ', $CF{"CLIENTALLOW"});
    my $ipok= 0;

    foreach my $ippattern (@clientregex)
    {
	#
	# change all periods, except those preceded by [ or \, into \.
	#
	$ippattern=~ s/([^[\\])\./$1\\./g;

	if ($clientip =~ /^${ippattern}$/)
	{
	    $ipok= 1;
	    last;
	}
    }

    if (! $ipok)
    {
	syslog('notice', "closing unwanted client: $clientip");
	close($CLIENT);
	return;
    }

    select ($CLIENT);
    $|=1;
    select (STDOUT);

    $clients{$fno}->{"host"} = inet_ntoa($addr);
    $clients{$fno}->{"fhandle"} = $CLIENT;
    $clients{$fno}->{"user"} = undef;		# username if authenticated
    $clients{$fno}->{"timeout"} = $CF{"CLIENT_TIMEOUT"};
    $clients{$fno}->{"last_read"} = time;		# last time data was read
    $clients{$fno}->{"buf"} = '';
    $numclients++;
}


#
# do all pending client commands
#
sub client_dopending {
    my ($cl, $cmd, $l);

    foreach $cl (keys %clients) {
    	if ($clients{$cl}->{"buf"} =~ /^([^\r\n]*)[\r\n]+/s) {
	    $cmd = $1;
	    $l = length ($cmd);
	    $clients{$cl}->{"buf"} =~ s/^[^\r\n]*[\r\n]+//s;
	    client_command ($cl, $cmd);
	}
    }
}


#
# close a client connection
#
sub client_close {
    my ($cl, $reason) = @_;

    syslog ('info', "closing client $cl: $reason") if (defined $reason);
    die if !defined ($clients{$cl}->{"fhandle"});
    close ($clients{$cl}->{"fhandle"});
    delete $clients{$cl};
    vec ($iovec, $cl, 1) = 0;
    $numclients--;
}


#
# Handle a connection from a client
#
sub client_command {
    my ($cl, $l) = @_;
    my ($cmd, $args, $group, $service, $s, $sname, $stchanged);
    my ($var, $value, $msg, @l, $sock, $port, $addr, $sref, $auth, $fh);
    my ($user, $pass, @argsList, $comment);
    my ($authtype, @authtypes);
    my $is_auth = 0;    #flag for multiple auth types

    syslog ('info', "client command \"$l\"")
	if ($l !~ /^\s*login/i);

    $fh = $clients{$cl}->{"fhandle"};

    if ($l !~ /^(dump|login|disable|enable|quit|list|set|get|setview|getview|
		    stop|start|loadstate|savestate|reset|clear|checkauth|
		    reload|term|test|servertime|ack|version|protid)(\s+(.*))?$/ix) {
	sock_write ($fh, "520 invalid command\n");
	return;
    }
    ($cmd, $args) = ("\L$1", $3);

    $stchanged = 0;

    print STDERR "client command $cmd\nclient args $args\n";
    #
    # quit command
    #
    if ($cmd eq "quit") {
	sock_write ($fh, "220 quitting\n");
	client_close ($cl);

    } elsif ($opt{"d"} && $cmd eq "dump") {
    	print STDERR Dumper (\%watch), "\n\n";

    #
    # protocol identification
    #
    } elsif ($cmd eq "protid") {
    	if ($args != int ($PROT_VERSION))
	{	
	    sock_write ($fh, "520 protocol mismatch\n");
	}

	else
	{
	    sock_write ($fh, "220 protocol match\n");
	}

    #
    # login
    #
    } elsif ($cmd eq "login") {
	($user, $pass) = split (/\s+/, $args, 2);
	@authtypes = split(' ' , $CF{"AUTHTYPE"}) ;
	# Check each for of authentication in order, and stop checking
	# as soon as we get a positive authentication result.
	foreach $authtype (@authtypes) {
            if (defined auth ($authtype, $user, $pass, $clients{$cl}->{"host"})) {
		$is_auth = 1;
		last;
	    }
	}
	if ($is_auth != 1) {
	    sock_write ($fh,  "530 login unsuccessful\n");
	} else {
	    $clients{$cl}->{"user"} = $user;
	    syslog ("info", "authenticated $user");
	    sock_write ($fh,  "220 login accepted\n");
	}

    #
    # reset
    #
    } elsif ($cmd eq "reset" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	my ($keepstate);
	if ($args =~ /stopped/i) {
	    $STOPPED = 1;
	    $STOPPED_TIME = time;
	}

	if ($args =~ /keepstate/) {
	    $keepstate = 1;
	}

	if (reset_server ($keepstate)) {
	    sock_write ($fh,  "220 reset PID $$\@$HOSTNAME\n");
	} else {
	    sock_write ($fh,  "520 reset PID $$\@$HOSTNAME failed, error in config file\n");
	}

    #
    # reload
    #
    } elsif ($cmd eq "reload" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	if (!defined reload (split (/\s+/, $args))) {
	    sock_write ($fh,  "520 unknown reload command\n");
	} else {
	    sock_write ($fh,  "220 reload completed\n");
	}

    #
    # clear
    #
    } elsif ($cmd eq "clear" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
    	if ($args =~ /^timers \s+ ([a-zA-Z0-9_.-]+) \s+ ([a-zA-Z0-9_.-]+)/ix) {
	    if (!defined $watch{$1}->{$2}) {
		sock_write ($fh,  "520 unknown group\n");
	    } else {
		clear_timers ($1, $2);
		sock_write ($fh,  "220 clear timers completed\n");
	    }

	} else {
	    sock_write ($fh,  "520 unknown clear command\n");
	    next;
	}

    #
    # test
    #
    } elsif ($cmd eq "test" && check_auth ($clients{$cl}->{"user"}, $cmd))  {
	my ($cmd, $args) = split (/\s+/, $args, 2);

	#
	# test monitor
	#
	if ($cmd eq "monitor") {
	    my ($group, $service) = split (/\s+/, $args);

	    if (!defined $watch{$group}->{$service}) {
		sock_write ($fh,  "$group $service not defined\n");
	    } else {
		$watch{$group}->{$service}->{"_timer"} = 0;
                $watch{$group}->{$service}->{"_next_check"} = 0;
		mysystem("$CF{MONREMOTE} test $group $service") if ($CF{MONREMOTE});
	    }
	    sock_write ($fh,  "220 test monitor completed\n");

	#
	# test alert
	#
	} elsif ($cmd =~ /^alert|startupalert|upalert|ackalert|disablealert$/) {
	    my ($group, $service, $retval, $period) = split (/\s+/, $args, 4);

	    if (!defined $watch{$group}->{$service}) {
		sock_write ($fh,  "520 $group $service not defined\n");

	    } elsif (!defined $watch{$group}->{$service}->{"periods"}->{$period}) {
		    sock_write ($fh,  "520 period not defined\n");

	    } else {
		my $f = 0;
		my $a;

		if ($cmd eq "alert") {
		    $a = $watch{$group}->{$service}->{"periods"}->{$period}->{"alerts"};
		} elsif ($cmd eq "startupalert") {
		    $f = $FL_STARTUPALERT;
		    $a = $watch{$group}->{$service}->{"periods"}->{$period}->{"startupalerts"};
		} elsif ($cmd eq "upalert") {
		    $f = $FL_UPALERT;
		    $a = $watch{$group}->{$service}->{"periods"}->{$period}->{"upalerts"};
		} elsif ($cmd eq "ackalert") {
		    $f = $FL_ACKALERT;
		    $a = $watch{$group}->{$service}->{"periods"}->{$period}->{"ackalerts"};
		} elsif ($cmd eq "disablealert") {
		    $f = $FL_DISABLEALERT;
		    $a = $watch{$group}->{$service}->{"periods"}->{$period}->{"disablealerts"};
		}

		for (@{$a}) {
		    my ($alert, $args) = split (/\s+/, $_, 2);

		    if ($args =~ /^exit=/) {
		    	$args =~ s/^exit=\S+ \s+//x;
		    }

		    call_alert (
			group	=> $group,
			service	=> $service,
			output	=> "test\ntest detail\n",
			retval	=> $retval,
			flags	=> $f | $FL_TEST,
			alert	=> $alert,
			args	=> $args,
		    );
		}

		sock_write ($fh,  "220 test alert completed\n");
	    }

	#
        # test config file
        #
        } elsif ($cmd =~ /^config$/) {
	    if ((my $err = read_cf ($CF{"CF"}, 0))  ne "") {
		sock_write ($fh,  $err);
		sock_write ($fh,  "\n520 test config completed, errors found in config file\n");
	    }

	    else
	    {
		sock_write ($fh,  "220 test config completed OK, no errors found\n");
	    }

	} else {
	    sock_write ($fh,  "520 test error\n");
	}

    #
    # version
    #
    } elsif ($cmd eq "version") {
    	sock_write ($fh, "version " . int ($PROT_VERSION) . "\n");
    	sock_write ($fh, "220 version completed\n");

    #
    # load state
    #
    } elsif ($cmd eq "loadstate" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	foreach (split (/\s+/, $args)) {
	    load_state ($_);
	}
	sock_write ($fh,  "220 loadstate completed\n");

    #
    # save state
    #
    } elsif ($cmd eq "savestate" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	if ($args =~ /\S/)
	{
	    foreach (split (/\s+/, $args))
	    {
		save_state ($_);
	    }
	    sock_write ($fh,  "220 savestate completed\n");
	}

	else
	{
	    sock_write ($fh,  "520 savestate error, arguments required\n");
	}

    #
    # term
    #
    } elsif ($cmd eq "term"  && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	sock_write ($fh,  "220 terminating server\n");
	client_close ($cl, "terminated by user command");
	syslog ("info", "terminating by user command");
	exit;

    #
    # stop testing
    #
    } elsif ($cmd eq "stop"&& check_auth ($clients{$cl}->{"user"}, $cmd)) {
	$STOPPED = 1;
	$STOPPED_TIME = time;
	sock_write ($fh,  "220 stop completed\n");

    #
    # start testing
    #
    } elsif ($cmd eq "start" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	$STOPPED = 0;
	$STOPPED_TIME = 0;
	sock_write ($fh,  "220 start completed\n");

    } elsif ($cmd eq "setview") {
        my @args=split /\s+/, $args;
        if (@args > 1) {
            sock_write($fh, "500 Unknown setview command\n")
        } elsif (@args == 1) {
            if (defined($views{$args[0]})) {
                $clients{$cl}->{"view"} = $args[0];
                sock_write($fh, "selecting view $args[0]\n");
                sock_write($fh, "220 setview completed\n")
            } else {
                sock_write($fh, "504 unknown view $args[0]\n");
            }
        } else {
            delete $clients{$cl}->{"view"};
            sock_write($fh, "no view selected -- all groups will be displayed\n");
            sock_write($fh, "220 setview completed\n")
        }
    } elsif ($cmd eq "getview") {
        if ($clients{$cl}->{"view"}) {
            sock_write($fh, "view ".$clients{$cl}->{"view"}. " selected\n");
        } else {
            sock_write($fh, "no view selected -- all groups will be displayed\n");
      }
      sock_write($fh, "220 getview completed\n")
    #
    # set
    #
    } elsif ($cmd eq "set" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	if ($args =~ /^maxkeep\s+(\d+)/) {
	    $CF{"MAX_KEEP"} = $1;
	    sock_write ($fh,  "220 set completed\n");
	} else {
	    ($group, $service, $var, $value) = split (/\s+/, $args, 4);
	    if (!defined $watch{$group}->{$service}) {
		sock_write ($fh,  "520 $group,$service not defined\n");
	    } elsif ($var eq "opstatus") {
		if (!defined ($OPSTAT{$value})) {
		    sock_write ($fh,  "520 undefined opstatus\n");
		} else {
		    set_op_status ($group, $service,
		    	un_esc_str ((parse_line ('\s+', 0, $value))[0]));
		    sock_write ($fh,  "220 set completed\n");
		}

	    } else {
		$value = un_esc_str ((parse_line ('\s+', 0, $value))[0]);
		$watch{$group}->{$service}->{$var} = $value;
		sock_write ($fh,  "$group $service $var='$value'\n");
		sock_write ($fh,  "220 set completed\n");
	    }
	}

    #
    # get
    #
    } elsif ($cmd eq "get" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	if ($args =~ /^maxkeep\s*$/) {
	    sock_write ($fh,  "maxkeep = $CF{MAX_KEEP}\n");
	    sock_write ($fh,  "220 set completed\n");
	} else {
	    ($group, $service, $var) = split (/\s+/, $args, 3);
	    if (!defined $watch{$group}->{$service}) {
		sock_write ($fh,  "520 $group,$service not defined\n");
	    } else {
		sock_write ($fh,  "$group $service $var='" .
			esc_str ($watch{$group}->{$service}->{$var}, 1) . "'\n");
		sock_write ($fh,  "220 get completed\n");
	    }
	}

    #
    # list
    #
    } elsif ($cmd eq "list" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	@argsList = split(/\s+/, $args);
	($cmd, $args) = split (/\s+/, $args, 2);

	#
	# list service descriptions
	#
	if ($cmd eq "descriptions") {
	    foreach $group (keys %watch) {
		foreach $service (keys %{$watch{$group}}) {
                    if (view_match($clients{$cl}->{"view"}, $group, $service)) {
                        sock_write ($fh,  "$group $service " .
                                    esc_str ($watch{$group}->{$service}->{"description"}, 1) .
                                    "\n");
                    }
		}
	    }
	    sock_write ($fh,  "220 list descriptions completed\n");

	#
	# list group members
	#
	} elsif ($cmd eq "group") {
	    if ($groups{$args}) {
		sock_write ($fh,  "hostgroup $args @{$groups{$args}}\n");
		sock_write ($fh,  "220 list group completed\n");
	    } else {
		sock_write ($fh,  "520 list group error, undefined group\n");
	    }

	#
	# list status of all services
	#
	} elsif ($cmd eq "opstatus") {
	    if (!defined $args || $args eq "")
	    {
		foreach $group (keys %watch) {
		    foreach $service (keys %{$watch{$group}}) {
                        if (view_match($clients{$cl}->{"view"}, $group, $service)) {
                            client_write_opstatus ($fh, $group, $service);
                        }
		    }
		}
		sock_write ($fh,  "220 list opstatus completed\n");
	    }

	    else
	    {
	    	my $err = 0;
		my @g = ();
		my ($group, $service);

		foreach my $gs (split (/\s+/, $args))
		{
		    ($group, $service) = split (/,/, $gs);
		    $err++ && last if ($service ne "" && !defined $watch{$group}->{$service});
		    push (@g, [$group, $service]);
		}

		if (!$err)
		{
		    foreach my $gs (@g)
		    {
			if ($gs->[1] ne "") {
			    client_write_opstatus ($fh, $gs->[0], $gs->[1]);
			} else {
			    foreach $service (keys %{$watch{$gs->[0]}}) {
				client_write_opstatus ($fh, $gs->[0], $service);
			    }
			}
		    }
		    sock_write ($fh,  "220 list opstatus completed\n");
		}

		else
		{
		    sock_write ($fh,  "520 $group,$service does not exist\n");
		}
	    }

	#
	# list disabled hosts and services
	#
	} elsif ($cmd eq "disabled") {
	    foreach $group (keys %groups) {
                if (view_match($clients{$cl}->{"view"}, $group, undef)) {
                    @l = grep (/^\*/, @{$groups{$group}});
                    if (@l) {
                        grep (s/^\*//, @l);
                        sock_write ($fh,  "group $group: @l\n");
                    }
                }
	    }
	    foreach $group (keys %watch) {
                if (view_match($clients{$cl}->{"view"}, $group, undef)) {
                    if (exists $watch_disabled{$group} && $watch_disabled{$group} == 1) {
                        sock_write ($fh,  "watch $group\n");
                    }
                }
		foreach $service (keys %{$watch{$group}}) {
                    if (view_match($clients{$cl}->{"view"}, $group, $service)) {
                        if (defined $watch{$group}->{$service}->{'disable'} 
                            && $watch{$group}->{$service}->{'disable'} == 1) {
                            sock_write ($fh,  "watch $group service " .
                                        "$service\n");
                        }
                    }
                }
            }
            sock_write ($fh,  "220 list disabled completed\n");

	#
	# list last alert history
	#
	} elsif ($cmd eq "alerthist") {
	    foreach my $l (@last_alerts)
	    {
		sock_write ($fh,  esc_str ($l) . "\n");
	    }
	    sock_write ($fh,  "220 list alerthist completed\n");

	#
	# list time of last failures for each service
	#
	} elsif ($cmd eq "failures") {
	    foreach $group (keys %watch) {
		foreach $service (keys %{$watch{$group}}) {
                    if (view_match($clients{$cl}->{"view"}, $group, $service)) {
                        my $sref = \%{$watch{$group}->{$service}};
                        client_write_opstatus ($fh, $group, $service)
                            if ($FAILURE{$sref->{"_op_status"}});
                    }
		}
	    }
	    sock_write ($fh,  "220 list failures completed\n");

	#
	# list the failure history
	#
	} elsif ($cmd eq "failurehist") {
	    foreach my $l (@last_failures)
	    {
		sock_write ($fh, esc_str ($l) . "\n");
	    }
	    sock_write ($fh,  "220 list failurehist completed\n");

	#
	# list the time of last successes for each service
	#
	} elsif ($cmd eq "successes") {
	    foreach $group (keys %watch) {
		foreach $service (keys %{$watch{$group}}) {
                    if (view_match($clients{$cl}->{"view"}, $group, $service)) {
                        my $sref = \%{$watch{$group}->{$service}};
                        client_write_opstatus ($fh, $group, $service)
                            if ($SUCCESS{$sref->{"_op_status"}});
                    }
		}
	    }
	    sock_write ($fh,  "220 list successes completed\n");

	#
	# list warnings
	#
	} elsif ($cmd eq "warnings") {
	    foreach $group (keys %watch) {
		foreach $service (keys %{$watch{$group}}) {
                    if (view_match($clients{$cl}->{"view"}, $group, $service)) {
                        my $sref = \%{$watch{$group}->{$service}};
                        client_write_opstatus ($fh, $group, $service)
                            if ($WARNING{$sref->{"_op_status"}});
                    }
		}
	    }
	    sock_write ($fh,  "220 list successes completed\n");

	#
	# list process IDs
	#
	} elsif ($cmd eq "pids") {
	    sock_write ($fh,  "server $$\n");
	    foreach $value (keys %runningpid) {
		($group, $service) = split (/\//, $runningpid{$value});
		sock_write ($fh,  "$group $service $value\n");
	    }
	    sock_write ($fh,  "220 list pids completed\n");

	#
	# list watch groups and services
	#
	} elsif ($cmd eq "watch") {
	    foreach $group (keys %watch) {
		foreach $service (keys %{$watch{$group}}) {
                    if (view_match($clients{$cl}->{"view"}, $group, $service)) {
                        if (!defined $watch{$group}->{$service}) {
                            sock_write ($fh,  "$group (undefined service)\n");
                        } else {
                            sock_write ($fh,  "$group $service\n");
                        }
                    }
		}
	    }
	    sock_write ($fh,  "220 list watch completed\n");

	#
	# list server state
	#
	} elsif ($cmd eq "state") {
	    if ($STOPPED) {
		sock_write ($fh,  "scheduler stopped since $STOPPED_TIME\n");
	    } else {
		sock_write ($fh,  "scheduler running\n");
	    }
	    sock_write ($fh,  "220 list state completed\n");

	#
	# list aliases
	#
	} elsif ($cmd eq "aliases") {
	    my (@listAliasesRequest) = @argsList;

	    shift (@listAliasesRequest);

	    # if no alias request, all alias are responded
	    unless (@listAliasesRequest) {
	    	@listAliasesRequest = keys (%alias);
	    }

	    foreach my $alias (@listAliasesRequest){
	    	sock_write ($fh, "alias $alias\n");
		foreach $value (@{$alias{$alias}}) {
		    sock_write ($fh,  "$value\n");
		}
		sock_write ($fh, "\n");
	    }
	    sock_write ($fh,  "220 list aliases completed\n");

	#
	# list aliasgroups
	#
	} elsif ($cmd eq "aliasgroups") {
	    my (@listAliasesRequest);
	    @listAliasesRequest = keys (%alias);

	    sock_write ($fh,  "@listAliasesRequest\n")
	    	unless (@listAliasesRequest == 0);
	    sock_write ($fh,  "220 list aliasgroups completed\n");

	#
	# list deps
	#
	} elsif ($cmd eq "deps") {
	    foreach my $g (keys %watch) {
	    	foreach my $s (keys %{$watch{$g}}) {
                    if (view_match($clients{$cl}->{"view"}, $group, $service)) {
                        my $sref = \%{$watch{$g}->{$s}};
                        if ($sref->{"depend"} ne "") {
                            sock_write ($fh, "exp $g $s '" .
                                        esc_str ($sref->{"depend"}, 1) . "'\n");
                        } else {
                            sock_write ($fh, "exp $g $s 'NONE'\n");
                        }
                        my @u =
                            ($sref->{"depend"} =~ /[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+/g);
                        if (@u) {
                            sock_write ($fh, "cmp $g $s @u\n");
                        } else {
                            sock_write ($fh, "cmp $g $s NONE\n");
                        }
                    }
                }
	    }

	    sock_write ($fh,  "220 list deps completed\n");

	#
	# downtime log
	#
	} elsif ($cmd eq "dtlog") {
	    if ($CF{"DTLOGGING"}) {
	    	if (!open (DTLOGTMP, "<  $CF{DTLOGFILE}")) {
		    sock_write ($fh, "520 list dtlog error, cannot open dtlog\n");

		} else {
		    while (<DTLOGTMP>) {
		    	sock_write ($fh, $_ ) if (!/^#/ && !/^\s*$/);
		    }

		    close (DTLOGTMP);

		    sock_write ($fh, "220 list dtlog completed\n");
		}

	    } else {
	    	sock_write ($fh, "520 list dtlog error, dtlogging is not turned on\n");
	    }

	#
	# list available views
	#
	} elsif ($cmd eq "views") {
	    sock_write ($fh,  "views ".join(' ',sort(keys %views))."\n");
	    sock_write ($fh,  "220 list group completed\n");


        # unknown list command
	} else {
	    sock_write ($fh,  "520 unknown list command\n");
	}

    #
    # acknowledge a failure
    #
    } elsif ($cmd eq "ack" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	my ($group, $service, $comment) = split (/\s+/, $args, 3);

	if (!defined ($watch{$group})) {
	    sock_write ($fh,  "520 unknown group\n");

	} elsif (!defined $watch{$group}->{$service}) {
	    sock_write ($fh,  "520 unknown service\n");
	}

	my $sref = \%{$watch{$group}->{$service}};

	if ($sref->{"_op_status"} == $STAT_OK ||
		  $sref->{"_op_status"} == $STAT_UNTESTED) {
	    sock_write ($fh,  "520 service is in a non-failure state\n");

	} else {
	    $sref->{"_ack"} = time;
            $sref->{"_ack_comment"} = $clients{$cl}->{"user"} . ": " .
		    un_esc_str ((parse_line ('\s+', 0, $comment))[0]);
	    sock_write ($fh,  "220 ack completed\n");
 	    do_alert($group, $service, $sref->{"_ack_comment"}, undef, $FL_ACKALERT)
	}

    #
    # disable watch, service or host
    #
    } elsif ($cmd eq "disable" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	($cmd, $args) = split (/\s+/, $args, 2);

	#
	# disable watch
	#
	if ($cmd eq "watch") {
	    if (!defined (disen_watch($args, 0))) {
		sock_write ($fh,  "520 disable error, unknown watch \"$args\"\n");
	    } else {
		$stchanged++;
		mysystem("$CF{MONREMOTE} disable watch $args") if ($CF{MONREMOTE});
		sock_write ($fh,  "220 disable watch completed\n");
	    }

	#
	# disable service
	#
	} elsif ($cmd eq "service") {
	    ($group, $service) = split (/\s+/, $args, 2);

	    if (!defined (disen_service ($group, $service, 0))) {
		sock_write ($fh,  "520 disable error, unknown service\n");
	    } else {
		$stchanged++;
		mysystem("$CF{MONREMOTE} disable service $group $service") if ($CF{MONREMOTE});
		sock_write ($fh,  "220 disable service completed\n");
		do_alert($group, $service, $clients{$cl}->{"user"}, undef, $FL_DISABLEALERT)
	    }

	#
	# disable host
	#
	} elsif ($cmd eq "host") {
	    my @notfound = ();

	    my @hosts = split (/\s+/, $args);

	    foreach my $h (@hosts)
	    {
	    	if (!host_exists ($h))
		{
		    push @notfound, $h;
		}
	    }

	    if (@notfound)
	    {
	    	sock_write ($fh, "520 disable host failed, host(s) @notfound do not exist\n");
	    }

	    else
	    {
		foreach my $h (@hosts)
		{
		    #
		    # disable a watch if there is a group with this host
		    # as its only member. this prevents warning messages
		    # about monitors not being run on empty host groups
		    #
                    foreach my $g (host_singleton_group($h)) {
                        disen_watch($g, 0);
			mysystem("$CF{MONREMOTE} disable watch $g") if ($CF{MONREMOTE});
                    }

		    disen_host ($h, 0);
		    $stchanged++;
		    mysystem("$CF{MONREMOTE} disable host $h") if ($CF{MONREMOTE});
                }
                sock_write ($fh, "220 disable host completed\n");
	    }

	} else {
	    sock_write ($fh,  "520 command could not be executed\n");
	}

    #
    # enable watch, service or host
    #
    } elsif ($cmd eq "enable" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	($cmd, $args) = split (/\s+/, $args, 2);

	#
	# enable watch
	#
	if ($cmd eq "watch") {
	    if (!defined (disen_watch ($args, 1))) {
		sock_write ($fh,  "520 enable error, unknown watch\n");
	    } else {
		$stchanged++;
		mysystem("$CF{MONREMOTE} enable watch $args") if ($CF{MONREMOTE});
		sock_write ($fh,  "220 enable watch completed\n");
	    }


	#
	# enable service
	#
	} elsif ($cmd eq "service") {
	    ($group, $service) = split (/\s+/, $args, 2);

	    if (!defined (disen_service ($group, $service, 1))) {
		sock_write ($fh,  "520 enable error, unknown group\n");
	    } else {
		$stchanged++;
		mysystem("$CF{MONREMOTE} enable service $group $service") if ($CF{MONREMOTE});
		sock_write ($fh,  "220 enable completed\n");
	    }

	#
	# enable host
	#
	} elsif ($cmd eq "host") {
	    foreach my $h (split (/\s+/, $args)) {
                foreach my $g (host_singleton_group($h)) {
                    disen_watch($g, 1);
		    mysystem("$CF{MONREMOTE} enable watch $g") if ($CF{MONREMOTE});
                }

		disen_host ($h, 1);
		mysystem("$CF{MONREMOTE} enable host $h") if ($CF{MONREMOTE});
		$stchanged++;
	    }
	    sock_write ($fh,  "220 enable completed\n");

	} else {
	    sock_write ($fh,  "520 command could not be executed\n");
	}

    #
    # server time
    #
    } elsif ($cmd eq "servertime" && check_auth ($clients{$cl}->{"user"}, $cmd)) {
	sock_write ($fh,  join ("", time, " ", scalar (localtime), "\n"));
	sock_write ($fh,  "220 servertime completed\n");

    #
    # check auth
    #
    } elsif ($cmd eq "checkauth") {
	@_ = split(' ',$args);
	$cmd = $_[0];
	$user = $clients{$cl}->{"user"};
	#  Note that we call check_auth without syslogging here.
	if (check_auth($clients{$cl}->{"user"}, $cmd, 1))
	{
	    sock_write ($fh, "220 command authorized\n");
	}

	else
	{
	    sock_write ($fh, "520 command could not be executed\n");
	}


    } else {
	sock_write ($fh,  "520 command could not be executed, unknown command\n");
    }

    save_state ("disabled") if ($stchanged);
    syslog ('info', "finished client command \"$l\"")
	if ($l !~ /^\s*login/i);

}


sub client_write_opstatus {
    my $fh = shift;
    my ($group, $service) = @_;

    my $sref = \%{$watch{$group}->{$service}};
    my $summary	= esc_str ($sref->{"_last_summary"}, 1);
    my $detail	= esc_str ($sref->{"_last_detail"}, 1);
    my $depend	= esc_str ($sref->{"depend"}, 1);
    my $hostdepend	= esc_str ($sref->{"hostdepend"}, 1);
    my $monitordepend	= esc_str ($sref->{"monitordepend"}, 1);
    my $alertdepend	= esc_str ($sref->{"alertdepend"}, 1);
    my $monitor	= esc_str ($sref->{"monitor"}, 1);

    my $comment;
    if ($sref->{"_ack"} != 0) {
	$comment = esc_str ($sref->{"_ack_comment"}, 1);
    } else {
	$comment = '';
    }

    my $alerts_sent = 0;
    my $l = 0;
    foreach my $period (keys %{$sref->{"periods"}})
    {
    	$alerts_sent += $sref->{"periods"}->{$period}->{"_alert_sent"} if (!defined($sref->{"periods"}{$period}{"alerts_dont_count"}));
	$l = $sref->{"periods"}->{$period}->{"_last_alert"}
	    if (defined $sref->{"periods"}->{$period}->{"_last_alert"} && $sref->{"periods"}->{$period}->{"_last_alert"} > $l);
    }

    my $buf = sprintf("group=$group service=$service opstatus=$sref->{_op_status} last_opstatus=%s exitval=%s timer=%s last_success=%s last_trap=%s last_traphost=%s last_check=%s ack=%s ackcomment=$comment alerts_sent=$alerts_sent depstatus=%s depend=$depend hostdepend=$hostdepend monitordepend=$monitordepend alertdepend=$alertdepend monitor=$monitor last_summary=%s last_detail=%s", (defined $sref->{_last_op_status} ? $sref->{_last_op_status} : ""), (defined $sref->{_exitval} ? $sref->{_exitval} : ""), (defined $sref->{_timer} ? $sref->{_timer} : ""), (defined $sref->{_last_success} ? $sref->{_last_success} : ""), (defined $sref->{_last_trap} ? $sref->{_last_trap} : ""), (defined $sref->{_last_traphost} ? $sref->{_last_traphost} : ""), (defined $sref->{_last_check} ? $sref->{_last_check} : ""), (defined $sref->{_ack} ? $sref->{_ack} : ""), (defined $sref->{"_depend_status"} ? int ($sref->{"_depend_status"}) : ""), $summary, $detail);

    $buf .= " last_failure=$sref->{_last_failure}"
    	if ($sref->{"_last_failure"});


    if ($sref->{"interval"})
    {
	$buf .= " interval=$sref->{interval}" .
	    " monitor_duration=$sref->{_monitor_duration}" .
	    " monitor_running=$sref->{_monitor_running}"
    }

    $buf .= " exclude_period=". esc_str($sref->{exclude_period})
	if ($sref->{"exclude_period"} ne "");

    $buf .= " exclude_hosts=" .
	    esc_str(join (" ", keys %{$sref->{exclude_hosts}}))
	if (keys %{$sref->{"exclude_hosts"}});

    $buf .= " randskew=$sref->{randskew}"
	if ($sref->{"randskew"});


    $buf .= " last_alert=$l"
	if ($l);

    if ($sref->{"_first_failure"})
    {
	my $t = time - $sref->{"_first_failure"};

    	$buf .= " first_failure=$sref->{_first_failure}" .
		" failure_duration=$t";
    }

#    if ($sref->{"_first_success"})
#    {
#	my $t = time - $sref->{"_first_success"};

#    	$buf .= " first_success=$sref->{_first_success}" .
#		" success_duration=$t";
#    }

    $buf .= "\n";

    sock_write ($fh, $buf);
}


#
# show usage
#
sub usage {
    print <<"EOF";
usage: mon [-a dir] [-A file] [-b dir] [-B dir] [-c config] [-d]
           [-D dir] [-f] [-h] [-i secs] [-k num] [-l [type]] [-L dir]
           [-M [path]] [-m num] [-p num] [-P file] [-r num] [-s dir]
           [-S] [-t num]
       mon -v

  -a dir	alert script dir
  -A file	authorization file
  -b dir	base directory for alerts and monitors (basedir)
  -B dir	base directory for configuration files (cfbasedir)
  -c config	config file, defaults to "mon.cf"
  -d		debug
  -D dir	state directory (statedir)
  -f		fork and become a daemon
  -h		this help
  -i secs	sleep interval (seconds), defaults to 1
  -k num	keep history of last num events
  -l [type]	load some types of old state from statedir.  type can
                be disabled (default), opstatus or all.
  -L dir	log directory (logdir)
  -M [path]	pre-process config file with m4.  if m4 isn't in \$PATH
                specify the path to m4 here
  -m num	throttle at maximum number of monitor processes
  -O facility	syslog facility to use
  -p num	server listens on port num
  -P file	PID file
  -r num	randomize startup schedule
  -s dir	monitor script dir
  -S		start with scheduler stopped
  -t port	trap port
  -v		print version

Report bugs to $AUTHOR
$RCSID
EOF
}


#
# become a daemon
#
sub daemon {
    my $pid;

    if ($pid = fork()) {
	# the parent goes away all happy and stuff
    	exit (0);
    } elsif (!defined $pid) {
    	die "could not fork: $!\n";
    }

    setsid();

    #
    # make it so that we cannot regain a controlling terminal
    #
    if ($pid = fork()) {
	# the parent goes away all happy and stuff
    	exit (0);
    } elsif (!defined $pid) {
	syslog ('err', "could not fork: $!");
	exit 1;
    }

#    chdir ('/');
    umask (022);

    if (!open (N, "+>>" . $CF{"MONERRFILE"}))
    {
	syslog ("err", "could not open error output file $CF{'MONERRFILE'}: $!");
	exit (1);
    }

    select (N);
    $| = 1;
    select (STDOUT);

    if (!open (STDIN, "/dev/null"))
    {
	syslog ("err", "could not open STDIN from /dev/null: $!");
	exit (1);
    }

    print N "Mon starting at ".localtime(time)."\n";
    if (!open(STDOUT, ">&N") ||
	!open (STDERR, ">&N")) {
        syslog ("err", "could not redirect: $!");
	exit(1);
    }
    syslog ('info', "running as daemon");
}


#
# debug
#
sub debug {
    my ($level, @l) = @_;

    return if (!defined $opt{"d"} || $level > $opt{"d"});

    if ($opt{"d"} && !$opt{"f"}) {
    	print STDERR @l;
    } else {
    	syslog ('debug', join ('', @l));
    }
}


#
# die_die
#
sub die_die {
    my ($level, $msg) = @_;

    die "[$level] $msg\n" if ($opt{"d"});

    syslog ($level, "fatal, $msg");
    closelog();
    exit (1);
}


#
# handle cleanup of exited processes
# trigger alerts on failures (or send no alert if disabled)
# do some accounting
#
sub proc_cleanup {
    my ($summary, $tmnow, $buf);

    $tmnow = time;
    return if (keys %running == 0);

    while ((my $p = waitpid (-1, &WNOHANG)) >0)
    {
	next if (!exists $runningpid{$p});
	my ($group, $service) = split (/\//, $runningpid{$p});
	my $sref = \%{$watch{$group}->{$service}};

	#
	# suck in any extra data
	#
	my $fh = $fhandles{$runningpid{$p}};
	while (my $z = sysread ($fh, $buf, 8192))
	{
	    $ibufs{$runningpid{$p}} .= $buf;
	}

debug (1, "PID $p ($runningpid{$p}) exited with [" . int ($?>>8) . "]\n");

	$sref->{"_monitor_duration"} = $tmnow - $sref->{"_last_check"};

	$sref->{"_monitor_running"} = 0;

	process_event ("m", $group, $service, int ($?>>8), $ibufs{$runningpid{$p}});

	reset_timer ($group, $service);

	remove_proc ($p);
    }
}


#
# handle the event where a monitor exits or a trap is received
#
# $type is "m"  for monitor, "t" for trap
#
sub process_event {
    my ($type, $group, $service, $exitval, $output) = @_;

debug (1, "process_event type=$type group=$group service=$service exitval=$exitval output=[$output]\n");

    my $sref = \%{$watch{$group}->{$service}};
    my $tmnow = time;

    my ($summary, $detail) = split("\n", $output, 2);

    $sref->{"_exitval"} = $exitval;

    if ($sref->{"depend"} ne "" &&
	    $sref->{"dep_behavior"} eq "a")
    {
	dep_ok ($sref, 'a');
    }

    #
    # error exit value
    #
    if ($exitval)
    {
	#
	# accounting
	#
	$sref->{"_failure_count"}++;
	$sref->{"_consec_failures"}++;
	$sref->{"_last_failure"} = $tmnow;
	if ($sref->{"_op_status"} == $STAT_OK ||
		$sref->{"_op_status"} == $STAT_UNKNOWN ||
		$sref->{"_op_status"} == $STAT_UNTESTED)
	{
	    $sref->{"_first_failure"} = $tmnow;
	}
	set_op_status ($group, $service, $STAT_FAIL);

	$summary = "(NO SUMMARY)" if ($summary =~ /^\s*$/m);
	$sref->{"_last_summary"} = $summary;
	$sref->{"_last_detail"} = $detail;
	shift @last_failures if (@last_failures > $CF{"MAX_KEEP"});
	push @last_failures, "$group $service" .
	    " $tm $summary";
	syslog ('crit', "failure for $last_failures[-1]");

	#
	# send an alert if necessary
	#
	if ($type eq "m")
	{
	    do_alert ($group, $service, $output, $exitval, $FL_MONITOR);
	    #
	    # change interval if needed
	    #
	    if (defined ($sref->{"failure_interval"}) &&
	    		!defined $sref->{"_old_interval"})
	    {
		$sref->{"_old_interval"} = $sref->{"interval"};
		$sref->{"interval"} = $sref->{"failure_interval"};
		$sref->{"_next_check"} = 0;
	    }
	}

	elsif ($type eq "t")
	{
	    do_alert ($group, $service, $output, $exitval, $FL_TRAP);
	}

	elsif ($type eq "T")
	{
	    do_alert ($group, $service, $output, $exitval, $FL_TRAPTIMEOUT);
	}

	$sref->{"_failure_output"} = $output;
    }

    #
    # success exit value
    #
    else
    {
	if ($CF{"DTLOGGING"} && defined ($sref->{"_op_status"}) &&
	       $sref->{"_op_status"} == $STAT_FAIL)
	{
	    write_dtlog ($sref, $group, $service);
	}

	my $old_status = $sref->{"_op_status"};
	set_op_status ($group, $service, $STAT_OK);

	if ($type eq "t")
	{
	    $sref->{"_last_uptrap"} = $tmnow;
	}

	#
	# if this service has just come back up and
	# we are paying attention to this event,
	# let someone know
	#
	if (($sref->{"redistribute"} ne '') ||
	    ((defined ($sref->{"_op_status"})) &&
	     ($old_status == $STAT_FAIL) &&
	     (defined($sref->{"_upalert"})) && 
	     (!defined($sref->{"upalertafter"}) 
	      || (($tmnow - $sref->{"_first_failure"}) >= $sref->{"upalertafter"}))))
	{
	    # Save the last failing monitor's output for posterity
	    $sref->{"_upalertoutput"}= $sref->{"_last_output"};
	    do_alert ($group, $service, $sref->{"_upalertoutput"}, 0, $FL_UPALERT);
	}

	#
	# send also when no upalertafter set
	# cabo: Modified to always send
	#
	#elsif (defined($sref->{"_upalert"}) && $old_status == $STAT_FAIL)
	elsif (defined($sref->{"_upalert"}) && ($old_status == $STAT_FAIL || $old_status == $STAT_UNTESTED))
	{
	    do_alert ($group, $service, $sref->{"_upalertoutput"}, 0, $FL_UPALERT);
	}

	$sref->{"_ack"} = 0;
	$sref->{"_ack_comment"} = '';
	$sref->{"_first_failure"} = 0;
	$sref->{"_last_failure"} = 0;
	$sref->{"_consec_failures"} = 0;
	$sref->{"_failure_output"} = "";
	$sref->{"_last_summary"} = $summary;
	$sref->{"_last_detail"} = $detail;

	#
	# reset the alertevery timer
	#
	foreach my $period (keys %{$sref->{"periods"}})
	{
	    #
	    # "alertevery strict" should not reset _last_alert
	    #
	    if (!$sref->{"periods"}->{$period}->{"_alertevery_strict"})
	    {
	      $sref->{"periods"}->{$period}->{"_last_alert"} = 0;
	    }

	    $sref->{"periods"}->{$period}->{"_1stfailtime"} = 0;
	    $sref->{"periods"}->{$period}->{"_alert_sent"} = 0;
	}

	#
	# change interval back to original
	#
	if (defined ($sref->{"failure_interval"}) &&
		    $sref->{"_old_interval"} != undef)
	{
	    $sref->{"interval"} = $sref->{"_old_interval"};
	    $sref->{"_old_interval"} = undef;
	    $sref->{"_next_check"} = 0;
	}

	$sref->{"_last_success"} = $tmnow;

    }

    #
    # save the output
    #
    $sref->{"_last_output"} = $output;
    $sref->{"_last_summary"} = $summary;
    $sref->{"_last_detail"} = $detail;
}


#
# collect output from running processes
#
sub collect_output {
    my ($buf, $rout);

    return if (!keys %running);

    my $nfound = select ($rout=$fdset_rbits, undef, undef, 0);
debug (1, "select returned $nfound file handles\n");

    return if ($! == &EINTR);

    if ($nfound) {
	#
	# look for the file descriptors that are readable,
	# and try to read as much as possible from them
	#
	foreach my $k (keys %fhandles) {
	    my $fh = $fhandles{$k};
	    if (vec ($rout, fileno($fh), 1) == 1) {
		my $z = 0;
		while ($z = sysread ($fh, $buf, 8192)) {
		    $ibufs{$k} .= $buf;
debug (1, "[$buf] from $fh\n");
		}

		#
		# ignore if EAGAIN, since we're nonblocking
		#
		if (!defined($z) && $! == &EAGAIN) {

		#
		# error on this descriptor
		#
		} elsif (!defined($z)) {
debug (1, "error on $fh: $!\n");
		    syslog ('err', "error on $fh: $!");
		    vec($fdset_rbits, fileno($fh), 1) = 0;
		} elsif ($z == 0 && $! == &EAGAIN) {
debug (1, "EAGAIN on $fh\n");

		#
		# if EOF encountered, stop trying to
		# get input from this file descriptor
		#
		} elsif ($z == 0) {
debug (1, "EOF on $fh\n");
		    vec($fdset_rbits, fileno($fh), 1) = 0;

		}
	    }
	}
    }
}




#
# handle forking a monitor process, and set up variables
#
sub run_monitor {
    my ($group, $service) = @_;
    my (@args, @groupargs, $pid, @ghosts, $monitor, $monitorargs);

    my $sref = \%{$watch{$group}->{$service}};

    ($monitor, $monitorargs) = ($sref->{"monitor"} =~ /^(\S+)(\s+(.*))?$/);

    if (!defined $MONITORHASH{$monitor} || ! -f $MONITORHASH{$monitor}) {
	syslog ('err', "no monitor found while trying to run [$monitor]");
	return undef;
    } else {
    	$monitor = $MONITORHASH{$monitor};
    }

    $monitor .= " " . $monitorargs if ($monitorargs);

    @ghosts = ();

    #
    # if monitor ends with ";;", do not append groups
    # to command line
    #
    if ($monitor =~ /;;\s*$/) {
	$monitor =~ s/\s*;;\s*$//;
	@args = quotewords ('\s+', 0, $monitor);
	@ghosts = (1);

    #
    # exclude disabled hosts
    #
    } else {
	@ghosts = grep (!/^\*/, @{$groups{$group}});

	#
	# per-service excludes
	#
	if (keys %{$sref->{"exclude_hosts"}})
	{
	    my @g = ();

	    for (my $i=0; $i<@ghosts; $i++)
	    {
		push (@g, $ghosts[$i])
		    if !$sref->{"exclude_hosts"}->{$ghosts[$i]};
	    }

	    @ghosts = @g;
	}

	#
	# per-host dependencies
	#
	if ((defined $sref->{"depend"} && $sref->{"depend"} ne "" && $sref->{"dep_behavior"} eq 'hm')
	    || (defined $sref->{"hostdepend"} && $sref->{"hostdepend"} ne ""))
	{
	    my @g = ();
	    my $sum = dep_summary($sref);

	    for (my $i=0; $i<@ghosts; $i++)
	    {
		push (@g, $ghosts[$i])
		    if (! grep /\Q$ghosts[$i]\E/, @$sum);
	    }

	    @ghosts = @g;
	}

	@args = (quotewords ('\s+', 0, $monitor), @ghosts);
    }

    if (@ghosts == 0 && !defined ($sref->{"allow_empty_group"}))
    {
    	syslog ('err', "monitor for $group/$service" .
		" not called because of no host arguments\n");
    	reset_timer ($group, $service);
    }

    else
    {
	$fhandles{"$group/$service"} = new FileHandle;

	$pid = open ($fhandles{"$group/$service"}, '-|');

	if (!defined $pid)
	{
	    syslog ('err', "Could not fork: $!");
	    delete $fhandles{"$group/$service"};
	    return 0;
	}

	elsif ($pid == 0)
	{
	    open(STDERR, '>&STDOUT')
		or syslog ('err', "Could not dup stderr: $!");

	    open(STDIN, "</dev/null")
		or syslog ('err', "Could not connect stdin to /dev/null: $!");

	    my $v;

	    foreach $v (keys %{$sref->{"ENV"}})
	    {
	    	$ENV{$v} = $sref->{"ENV"}->{$v};
	    }
	    $ENV{"MON_GROUP"}		= $group;
	    $ENV{"MON_SERVICE"}		= $service;
	    $ENV{"MON_LAST_SUMMARY"} = $sref->{"_last_summary"} if (defined $sref->{"_last_summary"});
	    $ENV{"MON_LAST_OUTPUT"} = $sref->{"_last_output"} if (defined $sref->{"_last_output"});
	    $ENV{"MON_LAST_FAILURE"} = $sref->{"_last_failure"} if (defined $sref->{"_last_failure"});
	    $ENV{"MON_FIRST_FAILURE"} = $sref->{"_first_failure"} if (defined $sref->{"_first_failure"});
	    $ENV{"MON_DEPEND_STATUS"} = $sref->{"_depend_status"} if (defined $sref->{"_depend_status"});
	    $ENV{"MON_FIRST_SUCCESS"} = $sref->{"_first_success"} if (defined $sref->{"_first_success"});
	    $ENV{"MON_LAST_SUCCESS"} = $sref->{"_last_success"} if (defined $sref->{"_last_success"});
	    $ENV{"MON_DESCRIPTION"} = $sref->{"description"} if (defined $sref->{"description"});
	    $ENV{"MON_STATEDIR"} = $CF{"STATEDIR"};
	    $ENV{"MON_LOGDIR"} = $CF{"LOGDIR"};
	    $ENV{"MON_CFBASEDIR"} = $CF{"CFBASEDIR"};

	    if (!exec @args)
	    {
	    	syslog ('err', "could not exec '@args': $!");
		exit (1);
	    }
	}

	$sref->{"_last_check"} = scalar (time);
	$sref->{"_monitor_running"} = 1;

debug (1, "watching file handle ", fileno ($fhandles{"$group/$service"}),
    " for $group/$service\n");

	#
	# set nonblocking I/O and setup bit vector for select(2)
	#
	configure_filehandle ($fhandles{"$group/$service"}) ||
		syslog ("err", "could not configure filehandle for $group/$service: $!");
	vec ($fdset_rbits,
	    fileno($fhandles{"$group/$service"}), 1) = 1;
	$fdset_ebits |= $fdset_rbits;

	#
	# note that this is running
	#
	$running{"$group/$service"} = 1;
	$runningpid{$pid} = "$group/$service";
	$ibufs{"$group/$service"} = "";
	$procs++;
    }

    if ($sref->{"_next_check"})
    {
	$sref->{"_next_check"} += $sref->{"interval"};
    } else {
	$sref->{"_next_check"} = time() + $sref->{"interval"};
    }




}


#
# set the countdown timer for this service
#
sub reset_timer {
    my ($group, $service) = @_;

    my $sref = \%{$watch{$group}->{$service}};

    if ($sref->{"randskew"} != 0)
    {
    	$sref->{"_timer"} = $sref->{"interval"} +
	     (int (rand (2)) == 0 ? -int(rand($sref->{"randskew"}) + 1) :
	     	int(rand($sref->{"randskew"})+1));
    }

    elsif ($sref->{"_next_check"})
    {
    	if (($sref->{"_timer"} = $sref->{"_next_check"} - time()) < 0)
	{
	    $sref->{"_timer"} = $sref->{"interval"};
	}
    }

    else
    {
	$sref->{"_timer"} = $sref->{"interval"};
    }
}


#
# randomize the delay before each test
# $opt{"randstart"} is seconds
#
sub randomize_startdelay {
    my ($group, $service);

    foreach $group (keys %watch) {
	foreach $service (keys %{$watch{$group}}) {
            $watch{$group}->{$service}->{"_timer"} =
                int (rand ($CF{"RANDSTART"}));
        }
    }

}


#
# return 1 if $val is within $range,
# where $range = "number" or "number-number"
#
sub inRange {
    my ($val, $range) = @_;
    my ($retval);

    $retval = 0;
    if ($range =~ /^(\d+)$/ && $val == $1) {
        $retval = 1

    } elsif ($range =~ /^(\d+)\s*-\s*(\d+)$/ &&
	    ($val >= $1 && $val <= $2)) {
        $retval = 1
    }

    $retval;
}


#
# disable ($cmd==0) or enable a watch
#
sub disen_watch {
    my ($w, $cmd) = @_;

    return undef if (!defined ($watch{$w}));
    if (!$cmd) {
	$watch_disabled{$w} = 1;
    } else {
	$watch_disabled{$w} = 0;
    }
}


#
# disable ($cmd==0) or enable a service
#
sub disen_service {
    my ($g, $s, $cmd) = @_;
    my ($snum);

    return undef if (!defined $watch{$g});
    return undef if (!defined $watch{$g}->{$s});
    if (!$cmd) {
	$watch{$g}->{$s}->{"disable"} = 1;
    } else {
	$watch{$g}->{$s}->{"disable"} = 0;
    }
}


#
# disable ($cmd==0) or enable a host
#
sub disen_host {
    my ($h, $cmd) = @_;

    my $found = undef;

    foreach my $g (keys %groups) {
	if ((!defined $cmd) || $cmd == 0) {
	    if (grep (s/^$h$/*$h/, @{$groups{$g}}))
	    {
		$found = 1;
	    }
	}
	else
	{
	    if (grep (s/^\*$h$/$h/, @{$groups{$g}}))
	    {
		$found = 1;
	    }
	}
    }

    $found;
}


sub host_exists {
    my $host = shift;

    my $found = 0;

    foreach my $g (keys %groups) {
    	if (grep (/^$host$/, @{$groups{$g}}))
	{
	    $found = 1;
	    last;
	}
    }

    $found;
}



#
# given a host, search groups and return an array of group
# names which have that host as their only member. return
# an empty array if no group found
# 
#
sub host_singleton_group {
    my $host = shift;

    my @found;

    foreach my $g (keys %groups) {
    	if (grep (/^\*?$host$/, @{$groups{$g}}) &&
            scalar(@{$groups{$g}}) == 1)
	{
	    push (@found, $g);
	}
    }

    return (@found);
}


#
# save state
#
sub save_state {
    my (@states) = @_;
    my ($group, $service, @l, $state);

    foreach $state (@states) {
	if ($state eq "disabled" || $state eq "all") {
	    if (!open (STATE, ">$CF{STATEDIR}/disabled")) {
		syslog ("err", "could not write to state file: $!");
		next;
	    }

	    foreach $group (keys %groups) {
		@l = grep (/^\*/, @{$groups{$group}});
		if (@l) {
		    grep (s/^\*//, @l);
		    grep { print STATE "disable host $_\n" } @l;
		}
	    }
	    foreach $group (keys %watch) {
		if (exists $watch_disabled{$group} && $watch_disabled{$group} == 1) {
		    print STATE "disable watch $group\n";
		}
		foreach $service (keys %{$watch{$group}}) {
		    if (defined $watch{$group}->{$service}->{'disable'} 
			&& $watch{$group}->{$service}->{'disable'} == 1) {
			print STATE "disable service $group $service\n";
		    }
		}
	    }
	    close (STATE);

	}

	if ($state eq "opstatus" || $state eq "all") {
	    if (!open (STATE, ">$CF{STATEDIR}/opstatus")) {
		syslog ("err", "could not write to opstatus state file: $!");
		next;
	    }
	    foreach $group (keys %watch) {
	    	foreach $service (keys %{$watch{$group}}) {
		    print STATE "group=$group\tservice=$service";
		    foreach my $var (qw(op_status failure_count alert_count last_success first_success
					consec_failures last_failure first_failure last_summary 
					last_failure_time last_failure_summary last_failure_detail
					last_detail ack ack_comment last_trap last_traphost exitval 
					last_check last_op_status failure_output trap_timer)) {
			print STATE "\t$var=" . esc_str($watch{$group}->{$service}->{"_$var"});
		    }
		    foreach my $periodlabel (keys %{$watch{$group}->{$service}->{periods}}) {
			foreach my $var (qw(last_alert alert_sent 1stfailtime failcount)) {
			    print STATE "\t$periodlabel:$var=" . esc_str($watch{$group}->{$service}{periods}{$periodlabel}{"_$var"});
			}
		    }
		    print STATE "\n";
		}
	    }
	    close (STATE);
	}
    }
}


#
# load state
#
sub load_state {
    my (@states) = @_;
    my ($l, $cmd, $args, $group, $service, $what, $state);

    foreach $state (@states) {
    	if ($state eq "disabled" || $state eq "all") {
	    if (!open (STATE, "$CF{STATEDIR}/disabled")) {
		syslog ("err", "could not read state file: $!");
		next;
	    }

	    while (defined ($l = <STATE>)) {
		chomp $l;
		($cmd, $what, $args) = split (/\s+/, $l, 3);

		next if ($cmd ne "disable");

		if ($what eq "host") {
		    disen_host ($args);
		} elsif ($what eq "watch") {
		    syslog ("err", "undefined watch reading state file: $l")
			if (!defined disen_watch ($args));
		} elsif ($what eq "service") {
		    ($group, $service) = split (/\s+/, $args, 2);
		    syslog ("err",
		    	"undefined group or service reading state file: $l")
			if (!defined disen_service ($group, $service));
		}
	    }

	    syslog ("info", "state '$state' loaded");
	    close (STATE);
	}

	if ($state eq "opstatus" || $state eq "all") {
	    if (!open (STATE, "$CF{STATEDIR}/opstatus")) {
		syslog ("err", "could not read state file: $!");
		next;
	    }

	    while (defined ($l = <STATE>)) {
		chomp $l;
		my %opstatus = map{ /^(.*)=(.*)$/; $1 => $2} split (/\t/, $l,);
		next unless (exists $opstatus{group} && exists $watch{$opstatus{group}} 
			     && exists $opstatus{service} && exists $watch{$opstatus{group}}->{$opstatus{service}});

		foreach my $op (keys %opstatus) {
		    next if ($op eq 'group' || $op eq 'service');
		    if ($op =~ /^(.*):(.*)$/) {
			next unless exists $watch{$opstatus{group}}->{$opstatus{service}}{periods}{$1};
			$watch{$opstatus{group}}->{$opstatus{service}}{periods}{$1}{"_$2"} = un_esc_str($opstatus{$op});
		    } else {
			$watch{$opstatus{group}}->{$opstatus{service}}{"_$op"} = un_esc_str($opstatus{$op});
		    }
		}
	    }
	    syslog ("info", "state '$state' loaded");
	    close (STATE);
	}
    }
}


#
# authenticate a login
#
sub auth {
    my ($type, $user, $plaintext, $host) = @_;
    my ($pass, %u, $l, $u, $p);


    if ($user eq "" || ($type ne 'trustlocal' && $plaintext eq "")) {
	syslog ('err', "an undef username or password supplied");
    	return undef;
    }

    #
    # standard UNIX passwd
    #
    if ($type eq "getpwnam") {
	(undef, $pass) = getpwnam($user);
	return undef
	    if (!defined $pass);

	if ((crypt ($plaintext, $pass)) ne $pass) {
	    return undef;
	}
	return 1;

    #
    # shadow password
    #
    } elsif ($type eq "shadow") {

    #
    # "mon" authentication
    #
    } elsif ($type eq "userfile") {
    	if (!open (U, $CF{"USERFILE"})) {
	    syslog ('err', "could not open user file '$CF{USERFILE}': $!");
	    return undef;
	}
	while (<U>) {
	    next if (/^\s*#/ || /^\s*$/);
	    chomp;
	    ($u,$p) = split (/\s*:\s*/, $_, 2);
	    $u{$u} = $p;
	}
	close (U);
        return undef if (!defined($u{$user}));  #user was not found in userfile
	return undef if ((crypt ($plaintext, $u{$user})) ne $u{$user}); #user gave wrong password
	return 1;

    #
    # PAM authentication
    #
    } elsif ($type eq "pam") {
	local $PAM_username = $user;
	local $PAM_password = $plaintext;
    	my $pamh;
	if (!ref($pamh = new Authen::PAM($CF{'PAMSERVICE'}, $PAM_username, \&pam_conv_func))) {
	    syslog ('err', "Error code $pamh during PAM init!: $!");
	    return undef;
	}
	my $res = $pamh->pam_authenticate ;
	return undef if ($res != &Authen::PAM::PAM_SUCCESS) ;
	return 1;
    } elsif ($type eq "trustlocal") {
      # We're configured to trust all authentications from localhost
      # i.e. cgi scripts are handling authentication themselves
      return undef if ($host ne "127.0.0.1");
      return 1;
    } else {
    	syslog ('err', "authentication type '$type' not known");
    }

    return undef;
}


#
# load the table of who can do which commands
#
sub load_auth {
    my ($startup) = @_;
    my ($l, $cmd, $users, $u, $host, $user, $password, $sect);

    %AUTHCMDS = ();
    %NOAUTHCMDS = ();
    %AUTHTRAPS = ();
    $sect = "command";

    if (!open (C, $CF{"AUTHFILE"})) {
	err_startup ($startup, "could not open $CF{AUTHFILE}: $!");
	return undef;
    }

    while (defined ($l = <C>)) {
	next if ($l =~ /^\s*#/ || $l =~ /^\s*$/);
	chomp $l;
	$l =~ s/^\s*//;
	$l =~ s/\s*$//;

	if ($l =~ /^command\s+section/) {
	    $sect = "command";
	    next;
	} elsif ($l =~ /^trap\s+section/) {
	    $sect = "trap";
	    next;
	}

	if ($sect eq "command") {
	    ($cmd, $users) = split (/\s*:\s*/, $l, 2);
	    if (!defined $users) {
		err_startup ($startup, "could not parse line $. of auth file\n");
		next;
	    }
	    foreach $u (split (/\s*,\s*/, $users)) {
		if ( $u =~ /^AUTH_ANY$/ ) {
		    # Allow all authenticated users
		    $AUTHCMDS{"\L$cmd"}{$u} = 1;
		} elsif ( $u =~ /^!(.*)/ ) {
		    # Directive is to "deny-user"
		    $NOAUTHCMDS{"\L$cmd"}{$1} = 1;
		} else {
		    # Directive is to "allow-user"
		    $AUTHCMDS{"\L$cmd"}{$u} = 1;
		}
	    }

	} elsif ($sect eq "trap") {
	    if ($l !~ /^(\S+)\s+(\S+)\s+(\S+)$/) {
		syslog ('err', "invalid entry in trap sect of $CF{AUTHFILE}, line $.");
	    	next;
	    }
	    ($host, $user, $password) = ($1, $2, $3);

	    if ($host eq "*") {
		#
	    	# allow traps from all hosts
		#

 	    } elsif ($host =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/) {
  	        if (($host = inet_aton ($host)) eq "") {
  		    syslog ('err', "invalid host in $CF{AUTHFILE}, line $.");
  		    next;
  		}
 	    } elsif ($host =~ /^[A-Z\d][[A-Z\.\d\-]*[[A-Z\d]+$/i) {
 	        if (($host = inet_aton ($host)) eq "") {
  		    syslog ('err', "invalid host in $CF{AUTHFILE}, line $.");
  		    next;
  		}
	    } else {
	    	syslog ('err', "invalid host in $CF{AUTHFILE}, line $.");
		next;
	    }

	    if ($host ne "*")
	    {
		$host = inet_ntoa ($host);
	    }

	    syslog ('notice', "Adding trap auth of: $host $user $password");
	    $AUTHTRAPS{$host}{$user} = $password;

	} else {
	    syslog ('err', "unknown section in $CF{AUTHFILE}: $l");
	}
    }
    close (C);
}

sub load_view_users {}

sub view_match {
    my ($view, $group, $service) = @_;
    if (!defined($view)) {
#	print STDERR "No view in use\n";
	return 1;
    }

    if (defined($group) && defined($views{$view}->{$group})) {
#	print STDERR "View $view contains $group\n";
	return 1;
    }
    if (defined($views{$view}->{$group.":".$service})) {
#	print STDERR "View $view contains $group:$service\n";
	return 1;
    }
    return 0;
}

#
# return undef if $user isn't permitted to perform $cmd
# Optional third argument controls logging to syslog.
# e.g.,
#  check_auth("joe", "disable")
#   will check to see if user joe is authorized to disable, and
#   complain to syslog if joe is not authorized
#  check_auth("joe", "disable", 1)
#   will check to see if user joe is authorized to disable but 
#   NOT complain to syslog if joe is not authorized
#
sub check_auth {
    my ($user, $cmd, $no_syslog) = @_;

    #
    # Check to see if the authenticated user is specifically 
    # denied the ability to run this command.
    #
    if (
	(defined ($user) && $NOAUTHCMDS{$cmd}{$user}) ||
	(defined ($user) && $NOAUTHCMDS{$cmd}{"AUTH_ANY"}) 
	)
    {
	syslog ("err", "user '$user' tried '$cmd', denied");
	return undef;
    }

    #
    # Check for "all". This allows any client, authenticated or
    # not, to execute the requested command.
    #
    return 1 if ($AUTHCMDS{$cmd}{"all"});

    #
    # Check for AUTH_ANY. This allows any authenticated user to 
    # execute the requested command.
    #
    return 1 if (defined ($user) && $AUTHCMDS{$cmd}{"AUTH_ANY"});

    #
    # Check to see if the authenticated user is specifically 
    #allowed the ability to run this command.
    #
    return 1 if (defined ($user) && $AUTHCMDS{$cmd}{$user});

    syslog ("err", "user '$user' tried '$cmd', not authenticated") unless defined($no_syslog);

    return undef;
}


#
# reload things
#
sub reload {
    my (@what) = @_;

    for (@what) {
    	if ($_ eq "auth") {
	    load_auth;
	} else {
	    return undef;
	}
    }

    return 1;
}


sub err_startup {
    my ($startup, $msg) = @_;

    if ($startup) {
    	die "$msg\n";
    } else {
    	syslog ('err', $msg);
    }
}


#
# handle a trap
#
sub handle_trap {
    my ($buf, $from) = @_;

    my $time = time;
    my %trap = ();
    my $flags = 0;
    my $tmnow = time;
    my $intended;
    my $fromip;

#
# MON-specific tags
# pro	protocol
# aut	auth
# usr	username
# pas	password
# typ	type  ("failure", "up", "startup", "trap", "traptimeout")
# spc	specific type (STAT_OK, etc.) THIS IS NO LONGER USED
# seq	sequence
# grp	group
# svc	service
# hst	host
# sta	status (same as exit status of a monitor)
# tsp	timestamp as time(2) value
# sum	summary output
# dtl	detail
#

    #
    # this part validates the trap
    #
    {
	foreach my $line (split (/\n/, $buf))
	{
	    if ($line =~ /^(\w+)=(.*)/)
	    {
		my $trap_name = $1;
		my $trap_val = $2;
		chomp $trap_val;
		$trap_val =~ s/^\'(.*)\'$/\1/;
		$trap{$trap_name} = un_esc_str ($trap_val);
	    }

	    else
	    {
		syslog ('err', "unspecified tag in trap: $line");
	    }
	}

	$trap{"sum"} = "$trap{sum}\n" if ($trap{"sum"} !~ /\n$/);

	my ($port, $addr) = sockaddr_in ($from);
	$fromip = inet_ntoa ($addr);

	#
	# trap authentication
	#
	my ($traphost, $trapuser, $trappass);

	if (defined ($AUTHTRAPS{"*"}))
	{
	    $traphost = "*";
	}
	
	else
	{
	    $traphost = $fromip;
	}

	if (defined ($AUTHTRAPS{$traphost}{"*"}))
	{
	    $trapuser = "*";
	    $trappass = "";
	}

	else
	{
	    $trapuser = $trap{"usr"};
	    $trappass = $trap{"pas"};
	}

	if (!defined ($AUTHTRAPS{$traphost}))
	{
	    syslog ('err', "received trap from unauthorized host: $fromip");
	    return undef;
	}

	if ($trapuser ne "*") {
	    if (!defined $AUTHTRAPS{$traphost}{$trapuser} ||
		crypt ($trappass, $AUTHTRAPS{$traphost}{$trapuser}) ne
		$AUTHTRAPS{$traphost}{$trapuser}) 
	      {
		  syslog ('err', "received trap from unauthorized user $trapuser, host $traphost");
		  return undef;
	      }
	}

	#
	# protocol version
	#
	if ($trap{"pro"} < $TRAP_PRO_VERSION)
	{
	    syslog ('err', "cannot handle traps from version less than $TRAP_PRO_VERSION");
	    return undef;
	}

	#
	# validate trap type
	#
	if (!defined $trap{"sta"})
	{
	    syslog ('err', "no trap sta value specified from $fromip");
	    return undef;
	}

	#
	# if mon receives a trap for an unknown group/service, then the
	# default/default group/service should catch these if it is defined
	#
	if (!defined $watch{$trap{"grp"}} && defined $watch{"default"})
	{
	    $intended = "$trap{'grp'}:$trap{'svc'}";
	    $trap{"grp"} = "default";
	}

	if ($trap{"grp"} eq 'default'
	    && !defined($watch{default}->{$trap{"svc"}})
	    && defined($watch{'default'}->{'default'}))
	{
	    $trap{"svc"} = "default";
	}

	if (!defined ($groups{$trap{"grp"}}))
	{
	    syslog ('err', "trap received for undefined group $trap{grp}");
	    return;
	}

	elsif (!defined $watch{$trap{"grp"}}->{$trap{"svc"}})
	{
	    syslog ('err', "trap received for undefined service type $trap{grp}/$trap{svc}");
	    return;
	}
    }

    #
    # trap has been validated, proceed
    #
    my $sref = \%{$watch{$trap{"grp"}}->{$trap{"svc"}}};

    #
    # a trap recieved resets the trap timeout timer
    #
    if (exists $sref->{"traptimeout"})
    {
    	$sref->{"_trap_timer"} = $sref->{"traptimeout"};
    }


    $sref->{"_last_trap"} = $time;

    if ($intended)
    {
       $sref->{"_intended"} = $intended;
    }

    syslog ('info', "trap $trap{typ} $trap{spc} from " .
	    "$fromip grp=$trap{grp} svc=$trap{svc}, sta=$trap{sta}\n");

    $sref->{"_trap_duration_timer"} = $sref->{"trapduration"}
	if ($sref->{"trapduration"});

    process_event ("t", $trap{"grp"}, $trap{"svc"}, $trap{"sta"}, "$trap{sum}\n$trap{dtl}");

    if( defined($sref->{"_intended"}) )
    {
        undef($sref->{"_intended"});
    }
}


#
# trap timeout
#
sub handle_trap_timeout {
    my ($group, $service) = @_;
    my ($tmnow);

    $tmnow = time;

    my $sref = \%{$watch{$group}->{$service}};
    $sref->{"_trap_timer"} = $sref->{"traptimeout"};
    process_event ("T", $group, $service, 1,
    	"trap timeout\n" .
	"trap timeout after " . $sref->{"traptimeout"} . "s at " . localtime ($tmnow) . "\n");
}


#
# write to a socket
#
sub sock_write {
    my ($sock, $buf) = @_;
    my ($nleft, $nwritten);

    $nleft = length ($buf);
    while ($nleft) {
    	$nwritten = syswrite ($sock, $buf, $nleft);
	if (!defined ($nwritten)) {
	    return undef if ($! != EAGAIN);
	    usleep (100000);
	    next;
	}
	$nleft -= $nwritten;
	substr ($buf, 0, $nwritten) = "";
    }
}


#
# do I/O processing for traps and client connections
#
sub handle_io {

    #
    # build iovec for server connections, traps, and clients
    #
    $iovec = '';
    my $niovec = '';
    vec ($iovec, fileno (TRAPSERVER), 1) = 1;
    vec ($iovec, fileno (SERVER), 1) = 1;
    foreach my $cl (keys %clients) {
	vec ($iovec, $cl, 1) = 1;
    }

    #
    # handle client I/O while there is some to handle
    #
    my $sleep = $SLEEPINT;
    my $tm0 = [gettimeofday];
    my $n;
    while ($n = select ($niovec = $iovec, undef, undef, $sleep)) {
	my $tm1 = [gettimeofday];

	if ($! != &EINTR)
	{
	    #
	    # mon trap
	    #
	    if (vec ($niovec, fileno (TRAPSERVER), 1)) {
		my ($from, $trapbuf);
		if (!defined ($from = recv (TRAPSERVER, $trapbuf, 65536, 0))) {
		    syslog ('err', "error trying to recv a trap: $!");
		} else {
		    handle_trap ($trapbuf, $from);
		}
		next;

	    #
	    # client connections
	    #
	    } elsif (vec ($niovec, fileno (SERVER), 1)) {
		client_accept;
	    }

	    #
	    # read data from clients if any exists
	    #
	    if ($numclients) {
		foreach my $cl (keys %clients) {
		    next if (!vec ($niovec, $cl, 1));

		    my $buf = '';
		    $n = sysread ($clients{$cl}->{"fhandle"}, $buf, 8192);
		    if ($n == 0 && $! != &EAGAIN) {
			client_close ($cl);
		    } elsif (!defined $n) {
			client_close ($cl, "read error: $!");
		    } else {
			$clients{$cl}->{"buf"} .= $buf;
			$clients{$cl}->{"timeout"} = $CF{"CLIENT_TIMEOUT"};
			$clients{$cl}->{"last_read"} = time;
		    }
		}
	    }
	}

	#
	# execute client commands which have been read
	#
	client_dopending if ($numclients);

	last if (tv_interval ($tm0, $tm1) >= $SLEEPINT);

	$sleep = $SLEEPINT - tv_interval ($tm0, $tm1);
    }

    if (!defined ($n)) {
	    syslog ('err', "select returned an error for I/O loop: $!");
    }

    #
    # count down client inactivity timeouts and close expired connections
    #
    if ($numclients) {
	foreach my $cl (keys %clients) {
	    my $timenow = time;
	    $clients{$cl}->{"timeout"} = $timenow - $clients{$cl}->{"last_read"};

	    if ($clients{$cl}->{"timeout"} >= $CF{"CLIENT_TIMEOUT"}) {
		client_close ($cl, "timeout after $CF{CLIENT_TIMEOUT}s");
	    }
	}
    }
}


#
# generate alert and monitor path hashes
#
sub gen_scriptdir_hash {
    my ($d, @scriptdirs, @alertdirs, $found);

    %MONITORHASH = ();
    %ALERTHASH = ();

    foreach $d (split (/\s*:\s*/, $CF{"SCRIPTDIR"})) {
	if (-d "$d" && -x "$d") {
	    push (@scriptdirs, $d);
	} else {
	    syslog ('err', "scriptdir $d is not usable");
	}
    }

    foreach $d (split (/\s*:\s*/, $CF{"ALERTDIR"})) {
	if (-d $d && -x $d) {
	    push (@alertdirs, $d);
	} else {
	    syslog ('err', "alertdir $d is not usable");
	}
    }

    #
    # monitors
    #
    foreach my $group (keys %watch) {
    	foreach my $service (keys %{$watch{$group}}) {
	    next if (!defined $watch{$group}->{$service}->{"monitor"});
	    my $monitor = (split (/\s+/, $watch{$group}->{$service}->{"monitor"}))[0];
	    $found = 0;
	    foreach (@scriptdirs) {
	    	if (-x "$_/$monitor") {
		    $MONITORHASH{$monitor} = "$_/$monitor"
		    	unless (defined $MONITORHASH{$monitor});
		    $found++;
		    last;
		}
	    }
	    if (!$found) {
	    	syslog ('err', "$monitor not found in one of (\@scriptdirs[@scriptdirs])");
	    }
	}
    }

    #
    # alerts
    #
    foreach my $group (keys %watch) {
    	foreach my $service (keys %{$watch{$group}}) {
            if ($watch{$group}->{$service}->{"redistribute"} ne '') {
                my $alert = $watch{$group}->{$service}->{"redistribute"};
                $found = 0;
                foreach (@alertdirs) {
		    if (-x "$_/$alert") {
			$ALERTHASH{$alert} = "$_/$alert"
			  unless (defined $ALERTHASH{$alert});
			$found++;
		    }
                }
                if (!$found) {
                    syslog ('err', "$alert not found in one of (\@alerttdirs[@alertdirs])");
                }
            }
	    foreach my $period (keys %{$watch{$group}->{$service}->{"periods"}}) {
		foreach my $my_alert (
			@{$watch{$group}->{$service}->{"periods"}->{$period}->{"alerts"}},
			@{$watch{$group}->{$service}->{"periods"}->{$period}->{"upalerts"}},
			@{$watch{$group}->{$service}->{"periods"}->{$period}->{"startupalerts"}},
			@{$watch{$group}->{$service}->{"periods"}->{$period}->{"ackalerts"}},
			@{$watch{$group}->{$service}->{"periods"}->{$period}->{"disablealerts"}},
			    ) {
		    my $alert = $my_alert;
		    $alert =~ s/^(\S+=\S+ )*(\S+).*$/$2/;
		    $found = 0;
		    foreach (@alertdirs) {
			if (-x "$_/$alert") {
			    $ALERTHASH{$alert} = "$_/$alert"
			    	unless (defined $ALERTHASH{$alert});
			    $found++;
			}
		    }
		    if (!$found) {
			syslog ('err', "$alert not found in one of (\@alerttdirs[@alertdirs])");
		    }
		}
	    }
	}
    }

}


#
# do some processing on dirs
#
sub normalize_paths {

    my ($authtype, @authtypes);

    #
    # do some sanity checks on dirs
    #
    $CF{"STATEDIR"} = "$CF{BASEDIR}/$CF{STATEDIR}" if ($CF{"STATEDIR"} !~ m{^/});
    syslog ('err', "$CF{STATEDIR} does not exist") if (! -d $CF{"STATEDIR"});

    $CF{"LOGDIR"} = "$CF{BASEDIR}/$CF{LOGDIR}" if ($CF{"LOGDIR"} !~ m{^/});
    syslog ('err', "$CF{LOGDIR} does not exist") if (! -d $CF{LOGDIR});


    $CF{"AUTHFILE"} = "$CF{CFBASEDIR}/$CF{AUTHFILE}"
	    if ($CF{"AUTHFILE"} !~ m{^/});
    syslog ('err', "$CF{AUTHFILE} does not exist")
	    if (! -f $CF{"AUTHFILE"});

    @authtypes = split(' ' , $CF{"AUTHTYPE"}) ;
    foreach $authtype (@authtypes) {
	if ($authtype eq "userfile") {
	    $CF{"USERFILE"} = "$CF{CFBASEDIR}/$CF{USERFILE}"
		if ($CF{"USERFILE"} !~ m{^/});
	    syslog ('err', "$CF{USERFILE} does not exist")
		if (! -f $CF{"USERFILE"});
	}
    }

    $CF{"DTLOGFILE"} = "$CF{LOGDIR}/$CF{DTLOGFILE}"
	    if ($CF{"DTLOGFILE"} !~ m{^/});

    if ($CF{"HISTORICFILE"} ne "") {
	$CF{"HISTORICFILE"} = "$CF{LOGDIR}/$CF{HISTORICFILE}"
		if ($CF{"HISTORICFILE"} !~ m{^/});
    }

    #
    # script and alert dirs may have multiple paths
    #
    foreach my $dir (\$CF{"SCRIPTDIR"}, \$CF{"ALERTDIR"}) {
	my @n;
	foreach my $d (split (/\s*:\s*/, $$dir)) {
	    $d =~ s{/$}{};
	    $d = "$CF{BASEDIR}/$d" if ($d !~ m{^/});
	    syslog ('err', "$d does not exist, check your alertdir and mondir paths")
		unless (-d $d);
	    push @n, $d;
	}
	$$dir = join (":", @n);
    }
}


#
# set opstatus and save old status
#
sub set_op_status {
    my ($group, $service, $status) = @_;

    $watch{$group}->{$service}->{"_last_op_status"} = 
	$watch{$group}->{$service}->{"_op_status"};
    $watch{$group}->{$service}->{"_op_status"} = $status;
}


sub debug_dir {
    print STDERR <<EOF;
    basedir	[$CF{BASEDIR}]
    cfbasedir	[$CF{CFBASEDIR}]

    cf		[$CF{CF}]
    statedir	[$CF{STATEDIR}]
    logdir	[$CF{LOGDIR}]
    authfile	[$CF{AUTHFILE}]
    userfile	[$CF{USERFILE}]
    dtlogfile	[$CF{DTLOGFILE}]
    historicfile[$CF{HISTORICFILE}]
    monerrfile  [$CF{MONERRFILE}]
    scriptdir	[$CF{SCRIPTDIR}]
    alertdir	[$CF{ALERTDIR}]
EOF

    foreach my $m (keys %MONITORHASH) {
	print STDERR "M $m=[$MONITORHASH{$m}]\n";
    }
    foreach my $m (keys %ALERTHASH) {
	print STDERR "A $m=[$ALERTHASH{$m}]\n";
    }
}


#
# globals affected by config file are
# all stored in %CF
#
sub init_cf_globals {
    $CF{"BASEDIR"} = $opt{"b"} || "/usr/lib/mon";
    $CF{"BASEDIR"} =~ s{/$}{};
    $CF{"CFBASEDIR"} = $opt{"B"} || "/etc/mon";
    $CF{"CF"} = $opt{"c"} || "$CF{CFBASEDIR}/mon.cf";
    $CF{"CF"} = "$PWD/$CF{CF}" if ($CF{"CF"} !~ /^\//);
    $CF{"SCRIPTDIR"} = "/usr/local/lib/mon/mon.d:mon.d";
    $CF{"ALERTDIR"}  = "/usr/local/lib/mon/alert.d:alert.d";
    $CF{"LOGDIR"} = $opt{"L"} || (-d "/var/log/mon" ? "/var/log/mon" : "log.d");
    $CF{"STATEDIR"}  = -d "/var/state/mon" ? "/var/state/mon"
		: -d "/var/lib/mon" ? "/var/lib/mon"
		: "state.d";
    $CF{"AUTHFILE"}  = "auth.cf";
    $CF{"AUTHTYPE"}  = "getpwnam";
    $CF{"PAMSERVICE"}  = "passwd";
    $CF{"USERFILE"}  = "monusers.cf";
    $CF{"PIDFILE"}   = (-d "/var/run/mon" ? "/var/run/mon"
		    : -d "/var/run" ? "/var/run"
		    : "/etc") . "/mon.pid";
    $CF{"MONERRFILE"} = "/dev/null";
    $CF{"DTLOGFILE"} = "downtime.log";
    $CF{"DTLOGGING"} = 0;
    $CF{"MAX_KEEP"}  = 100;
    $CF{"CLIENT_TIMEOUT"} = 30;
    $CF{"SERVPORT"}  = getservbyname ("mon", "tcp") || 2583;
    $CF{"TRAPPORT"}  = getservbyname ("mon", "udp") || 2583;
    $CF{"CLIENTALLOW"} = '\d+.\d+.\d+.\d+';
    $CF{"MAXPROCS"}  = 0;
    $CF{"HISTORICFILE"} = "";
    $CF{"HISTORICTIME"} = 0;
    $CF{"DEP_RECUR_LIMIT"} = 10;
    $CF{"SYSLOG_FACILITY"} = $opt{"O"} || "daemon";
    $CF{"STARTUPALERTS_ON_RESET"} = 0;
    $CF{"MONREMOTE"} = undef;
}


#
# globals not affected by config file
#
sub init_globals {
    $TRAP_PRO_VERSION = 0.3807;
    $SLEEPINT  = 1;
    $STOPPED   = 0;
    $STOPPED_TIME = 0;
    $START_TIME = time;
    $PROT_VERSION = 0x2611;
    $HOSTNAME  = hostname;
    $PWD = getcwd;

    #
    # flags
    #
    $FL_MONITOR = 1;
    $FL_UPALERT = 2;
    $FL_TRAP = 4;
    $FL_TRAPTIMEOUT = 8;
    $FL_STARTUPALERT = 16;
    $FL_TEST = 32;
    $FL_REDISTRIBUTE = 64;
    $FL_ACKALERT = 128;
    $FL_DISABLEALERT = 256;

    #
    # specific trap types
    #
    ($TRAP_COLDSTART, $TRAP_WARMSTART, $TRAP_LINKDOWN, $TRAP_LINKUP,
	$TRAP_AUTHFAIL, $TRAP_EGPNEIGHBORLOSS, $TRAP_ENTERPRISE, $TRAP_HEARTBEAT) = (0..7);

    #
    # operational statuses
    #
    ($STAT_FAIL, $STAT_OK, $STAT_COLDSTART, $STAT_WARMSTART, $STAT_LINKDOWN,
	$STAT_UNKNOWN, $STAT_TIMEOUT, $STAT_UNTESTED, $STAT_DEPEND, $STAT_WARN) = (0..9);

    %FAILURE = (
    	$STAT_FAIL => 1,
	$STAT_LINKDOWN => 1,
	$STAT_TIMEOUT => 1,
    );

    %SUCCESS = (
    	$STAT_OK => 1,
	$STAT_COLDSTART => 1,
	$STAT_WARMSTART => 1,
	$STAT_UNKNOWN => 1,
	$STAT_UNTESTED => 1,
    );

    %WARNING = (
    	$STAT_COLDSTART => 1,
	$STAT_WARMSTART => 1,
	$STAT_UNKNOWN => 1,
	$STAT_WARN => 1,
    );

    %OPSTAT = ("fail" => $STAT_FAIL, "ok" => $STAT_OK, "coldstart" => $STAT_COLDSTART,
	    "warmstart" => $STAT_WARMSTART, "linkdown" => $STAT_LINKDOWN,
	    "unknown" => $STAT_UNKNOWN, "timeout" => $STAT_TIMEOUT,
	    "untested" => $STAT_UNTESTED);

    #
    # fast lookup hashes for alerts and monitors
    #
    %MONITORHASH = ();
    %ALERTHASH = ();
}


#
# clear timers
#
sub clear_timers {
    my ($group, $service) = @_;

    return undef if (!defined $watch{$group}->{$service});

    my $sref = \%{$watch{$group}->{$service}};

    $sref->{"_trap_timer"} = $sref->{"traptimeout"}
    	if ($sref->{"traptimeout"});

    $sref->{"_trap_duration_timer"} = $sref->{"trapduration"}
    	if ($sref->{"trapduration"});

    $sref->{"_timer"} = $sref->{"interval"}
    	if ($sref->{"interval"});

    $sref->{"_consec_failures"} = 0
      if ($sref->{"_consec_failures"});
	
    foreach my $period (keys %{$sref->{"periods"}}) {
    	my $pref = \%{$sref->{"periods"}->{$period}};

	$pref->{"_last_alert"} = 0
	    if ($pref->{"alertevery"});

	$pref->{"_consec_failures"} = 0
	    if ($pref->{"alertafter_consec"});

	$pref->{'_1stfailtime'} = 0
	    if ($pref->{"alertafterival"});
    }
}


#
# load some amount of the alert history into memory
#
sub readhistoricfile {
    return if ($CF{"HISTORICFILE"} eq "");

    if (!open (HISTFILE, $CF{"HISTORICFILE"})) {
	syslog ('err',  "Could not read history from $CF{HISTORICFILE} : $!");	
	return;
    }

    my $epochLimit = 0;
    if ($CF{"HISTORICTIME"} != 0) {
	$epochLimit = time - $CF{"HISTORICTIME"};
    }

    @last_alerts = ();

    while (<HISTFILE>) {
	next if (/^\s*$/ || /^\s*#/);
    	chomp;
	my $epochAlert = (split(/\s+/))[3];
	push (@last_alerts, $_) if ($epochAlert >= $epochLimit);
    }

    close (HISTFILE);

    if (defined $CF{"MAX_KEEP"}) {
    	splice(@last_alerts, 0, $#last_alerts + 1 - $CF{"MAX_KEEP"});
    }
}


#
# This routine simply calls an alert.
#
# call with %args = (
#       group		=> "name of group",
#       service		=> "name of service",
#       pref		=> "optional period reference",
#	alert		=> "alert script",
#	args		=> "args to alert script",
# 	flags		=> "flags, as in $FL_*",
#	retval		=> "return value of monitor",
#	output		=> "output of monitor",
# )
#
sub call_alert {
    my (%args) = @_;

    foreach my $mandatory_arg (qw(group service flags
				  retval alert output)) {
        if (!exists $args{$mandatory_arg})
        {
            debug (1, "returning from call_alert because of missing arg $mandatory_arg\n");
            return (undef);
        }
    }

    my @groupargs = grep (!/^\*/, @{$groups{$args{"group"}}});

    my $tmnow = time;
    my ($summary) = split("\n", $args{"output"});
    $summary = "(NO SUMMARY)" if (!defined $summary || $summary =~ /^\s*$/m);

    my $sref = \%{$watch{$args{"group"}}->{$args{"service"}}};
    my $pref;

    if (defined $args{"pref"}) {
	$pref = $args{"pref"};
    }

    if (! defined $args{"args"}) {
	$args{"args"} = '';
    }

    my $alert = "";
    if (!defined $ALERTHASH{$args{"alert"}} ||
	    ! -f $ALERTHASH{$args{"alert"}}) {
	syslog ('err', "no alert found while trying to run $args{alert}");
	return undef;
    } else {
	$alert = $ALERTHASH{$args{"alert"}};
    }

    my $alerttype = "";           # sent to syslog and stored in @last_alerts
    my $alert_type = "failure";   # MON_ALERTTYPE set to this
    if ($args{"flags"} & $FL_UPALERT) {
    	$alerttype = "upalert";
	$alert_type = "up";
    } elsif ($args{"flags"} & $FL_STARTUPALERT) {
    	$alerttype = "startupalert";
	$alert_type = "startup";
    } elsif ($args{"flags"} & $FL_ACKALERT) {
    	$alerttype = "ackalert";
	$alert_type = "ack";
    } elsif ($args{"flags"} & $FL_DISABLEALERT) {
    	$alerttype = "disablealert";
	$alert_type = "disable";
    } elsif ($args{"flags"} & $FL_TRAPTIMEOUT) {
    	$alerttype = "traptimeoutalert";
	$alert_type = "traptimeout";
    } elsif ($args{"flags"} & $FL_TRAP) {
    	$alerttype = "trapalert";
	$alert_type = "trap";
    } elsif ($args{"flags"} & $FL_TEST) {
    	$alerttype = "testalert";
	$alert_type = "test";
    } else {
    	$alerttype = "alert";
    }

    #
    # log why we are triggering an alert
    #
    my $a = $alert;
    $a =~ s{^.*/([^/]+)$}{$1};
    syslog ("alert", "calling $alerttype $a for" .
	" $args{group}/$args{service} ($alert,$args{args}) $summary") if (!($args{"flags"} & $FL_REDISTRIBUTE));;

        
    # We may block while writing to the alert script, so we'll fork first, allowing the
    # master process to move on.
	    
    my $pid;
    if ($pid = fork()) {  ## Master
	# Do Nothing
    } elsif (defined($pid)) { ## Child
	my $pid = open (ALERT, "|-");
	if (!defined $pid) {
	    syslog ('err', "could not fork: $!");
	    return undef;
	}

	#
	# grandchild, the actual alert
	#
	if ($pid == 0) {
	    #
	    # set env variables to pass to the alert
	    #
	    foreach my $v (keys %{$sref->{"ENV"}}) {
		$ENV{$v} = $sref->{"ENV"}->{$v};
	    }

	    $ENV{"MON_LAST_SUMMARY"}	= $sref->{"_last_summary"} if (defined $sref->{"_last_summary"});
	    $ENV{"MON_LAST_OUTPUT"}		= $sref->{"_last_output"} if (defined $sref->{"_last_output"});
	    $ENV{"MON_LAST_FAILURE"}	= $sref->{"_last_failure"} if (defined $sref->{"_last_failure"});
	    $ENV{"MON_FIRST_FAILURE"}	= $sref->{"_first_failure"} if (defined $sref->{"_first_failure"});
	    $ENV{"MON_FIRST_SUCCESS"}	= $sref->{"_first_success"} if (defined $sref->{"_last_success"});
	    $ENV{"MON_LAST_SUCCESS"}	= $sref->{"_last_success"} if (defined $sref->{"_last_success"});
	    $ENV{"MON_DESCRIPTION"}		= $sref->{"description"} if (defined $sref->{"description"});
	    $ENV{"MON_GROUP"}		= $args{"group"} if (defined $args{"group"});
	    $ENV{"MON_SERVICE"}		= $args{"service"} if (defined $args{"service"});
	    $ENV{"MON_RETVAL"}		= $args{"retval"} if (defined $args{"retval"});
	    $ENV{"MON_OPSTATUS"}		= $sref->{"_op_status"} if (defined $sref->{"_op_status"});
	    $ENV{"MON_LAST_OPSTATUS"}		= $sref->{"_last_op_status"} if (defined $sref->{"_last_op_status"});
	    $ENV{"MON_ACK"}                 = $sref->{"_ack_comment"} if ($sref->{"_ack"} && $sref->{"_ack_comment"} ne "");
	    $ENV{"MON_ALERTTYPE"}		= $alert_type;
	    $ENV{"MON_STATEDIR"}		= $CF{"STATEDIR"};
	    $ENV{"MON_LOGDIR"}		= $CF{"LOGDIR"};
	    $ENV{"MON_CFBASEDIR"}		= $CF{"CFBASEDIR"};
	    
	    if( defined($sref->{"_intended"}) )
	      {
		  $ENV{"MON_TRAP_INTENDED"} = $sref->{"_intended"};
	      }
	    
	    else
	      {
		  undef ($ENV{"MON_TRAP_INTENDED"}) if (defined($ENV{"MON_TRAP_INTENDED"}));
	      }

	    my $t;
	    $t = "-u" if ($args{"flags"} & $FL_UPALERT);
	    $t = "-a" if ($args{"flags"} & $FL_ACKALERT);
	    $t = "-D" if ($args{"flags"} & $FL_DISABLEALERT);
	    $t = "-T" if ($args{"flags"} & $FL_TRAP);
	    $t = "-O" if ($args{"flags"} & $FL_TRAPTIMEOUT);
	    
	    my @execargs = (
			    $alert,
			    "-s", "$args{service}",
			    "-g", "$args{group}",
			    "-h", "@groupargs",
			    "-t", "$tmnow",
			   );

	    if ($t) {
		push @execargs, $t;
	    }
	    
	    if ($args{"args"} ne "") {
		push @execargs, quotewords('\s+',0,$args{"args"});
	    }
	    
	    if (!exec @execargs) {
		syslog ('err', "could not exec alert $alert: $!");
		return undef;
	    }
	    exit;
	}

	#
	# this will block if the alert is sucking gas, which is why we forked above
	#
	print ALERT $args{"output"};
	close (ALERT);
	exit;
    }

    #
    # test alerts and redistributions don't count
    #
    return (1) if ($args{"flags"} & ($FL_TEST | $FL_REDISTRIBUTE));

    #
    # tally this alert
    #
    if (defined $args{"pref"}) {
	$pref->{"_last_alert"} = $tmnow;
    }
    $sref->{"_alert_count"}++;

    #
    # store this in the log
    #
    shift @last_alerts if (@last_alerts > $CF{"MAX_KEEP"});

    my $alertline = "$alerttype $args{group} $args{service}" .
	" $tmnow $alert ($args{args}) $summary";
    push @last_alerts, $alertline;

    #
    # append to alert history file
    #
    if ($CF{"HISTORICFILE"} ne "") {
    	if (!open (HISTFILE, ">>$CF{HISTORICFILE}")) {
	    syslog ('err',  "Could not append alert history to $CF{HISTORICFILE}: $!");
	} else {
	    print HISTFILE $alertline, "\n";
	    close (HISTFILE);
	}
    }

    return 1;
}


#
# recursively evaluate a dependency expression
# substitutes "GROUP:SERVICE" with "1" or "0" if the service is pass/fail, resp.
#
# returns an anonymous hash reference
#
# {
#	status =>,           # "D"  recursion depth exceeded
#                            # "O"  everything is OK
#                            # "E"  eval error
#	depend =>,           # 1 for success (no deps in a failure state)
#                            # 0 if any deps failed
#	error =>,            # the textual error associated with "D" or "E" status
# }
#
sub depend {
    my ($depend, $depth, $deptype) = @_;
    debug (2, "checking DEP [$depend]\n");

    if ($depth > $CF{"DEP_RECUR_LIMIT"}) {
	return {
	    status => "D",
	    depend => undef,
	    error  => "recursion too deep for ($depend)",
	};
    }

    foreach my $depstr ($depend =~ /[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+/g)
    {
	my ($group ,$service) = split(':', $depstr);

	my $sref = \%{$watch{$group}->{$service}};
	my $depval = undef;
	my $subdepend = "";
	if (defined $sref->{"depend"} && $sref->{"dep_behavior"} eq $deptype) {
	    $subdepend = $sref->{"depend"};
	} elsif ($deptype eq 'a' && defined $sref->{"alertdepend"}) {
	    $subdepend = $sref->{"alertdepend"};
	} elsif ($deptype eq 'm' && defined $sref->{"monitordepend"}) {
	    $subdepend = $sref->{"monitordepend"};
	} 

	#
	# disabled watches and services used to be counted as "passing"
	# now we'll use the actual values, to avoid having dependent services
        # alert when a broken service gets disabled
	#
#	if ((exists $watch_disabled{$group} && $watch_disabled{$group}) || (defined $sref->{"disable"} && $sref->{"disable"} == 1))
#	{
#	    $depval = 1;
#
	#
	# root dependency found
	#
#	}
#	elsif ($subdepend eq "")
	if ($subdepend eq "")
	{
	    debug (2, "  found root dep $group,$service\n");

	    $depval = $SUCCESS{$sref->{"_op_status"}} && ($sref->{"_last_failure_time"} < (time - $sref->{"dep_memory"}));

	#
	# not a root dep, recurse
	#
	}
	else
	{
	    #
	    # do it recursively
	    #
	    my $dstatus = depend ($subdepend, $depth + 1, $deptype);
	    debug (2,
	    	"recur depth $depth returned $dstatus->{status},$dstatus->{depend}\n");

	    #
	    # a bad thing happened, bail out
	    #
	    if ($dstatus->{"status"} ne "O")
	    {
		debug (2,
		    "recursive dep failure for $group,$service (status=$dstatus->{status})\n");
		return $dstatus;
	    }

	    $depval = $dstatus->{"depend"} && $SUCCESS{$sref->{"_op_status"}}
	              && ($sref->{"_last_failure_time"} < (time - $sref->{"dep_memory"}));
	}

	my $v = int ($depval);
	debug (2, "  ($group,$service) $depth depend=[$v][$depend]");
	$depend =~ s/\b$depstr\b/$v/g;
	debug (2, "  depend=[$depend]\n");
    }

    debug (2, "  before eval: [$depend]");
    my $e = eval("$DEP_EVAL_SANDBOX $depend");
    debug (2, "  after eval: [$e]\n");

    if ($@ eq "")
    {
	return
	{
	    status	=> "O",
	    depend	=> $e,
	};

    }
    else
    {
    	return
	{
	    status	=> "E",
	    depend	=> $e,
	    error	=> $@,
	};
    }
}


#
# returns undef on error
#         0 if dependency failure, sets _depend_status to 0
#         1 if dependencies are OK, sets _depend_status to 1
#
sub dep_ok
{
    my $sref = shift;
    my $deptype = shift;
    my $depend = "";
    if (defined $sref->{"depend"} && $sref->{"dep_behavior"} eq $deptype) {
	$depend = $sref->{"depend"};
    } elsif ($deptype eq 'a' && defined $sref->{"alertdepend"}) {
	$depend = $sref->{"alertdepend"};
    } elsif ($deptype eq 'm' && defined $sref->{"monitordepend"}) {
	$depend = $sref->{"monitordepend"};
    }

    return 1 unless ($depend ne "");

    my $s = depend ($depend, 0, $deptype);

    if ($s->{"status"} eq "D")
    {
	debug (2, "dep recursion too deep\n");
	return undef;

    }
    elsif ($s->{"status"} eq "E")
    {
	syslog ("notice", "eval error for dependency starting at $depend: ".$s->{error});
	return undef;
    }
    elsif ($s->{"status"} eq "O" && !$s->{"depend"})
    {
	$sref->{"_depend_status"} = 0;
	return 0;
    }

    $sref->{"_depend_status"} = 1;

    return 1;
}


#
# returns undef on error
#         otherwise a reference to a list summaries from all 
#            DIRECT dependencies currently failing
sub dep_summary 
{
    my $sref = shift;
    my @sum;
    my @deps = ();
    
    if (defined $sref->{"depend"} && $sref->{"dep_behavior"} eq "hm") {
	@deps = ($sref->{"depend"} =~ /[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+/g);
    } elsif (defined $sref->{"hostdepend"}) {
	@deps = ($sref->{"hostdepend"} =~ /[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+/g);
    }
    
    return [] if (! @deps);

    foreach (@deps) {
	my ($group, $service) = split /:/;
	if (!(exists $watch{$group} && exists $watch{$group}->{$service})) {
	    return undef;
	}
	
	if ($watch{$group}->{$service}{"_op_status"} == $STAT_FAIL) {
	    push @sum, $watch{$group}->{$service}{"_last_summary"};
	} elsif ($watch{$group}->{$service}{"_last_failure_time"} >= (time - $watch{$group}->{$service}{"dep_memory"})) {
	    push @sum, $watch{$group}->{$service}{"_last_failure_summary"};
	}
    }

    return \@sum;
}
    
#
# convert a string to a hex-escaped string, returning
# the escaped string.
#
# $str is the string to be escaped
# if $inquotes is true, backslashes are doubled, making
#       the escaped string suitable to be enclosed in
#       single quotes and later passed to Text::quotewords.
#       For example,   var='quoted value'
#
sub esc_str {
    my $str = shift;
    my $inquotes = shift;

    my $escstr = "";

    return $escstr if (!defined $str);

    for (my $i = 0; $i < length ($str); $i++)
    {
    	my $c = substr ($str, $i, 1);

	if (ord ($c) <= 32 ||
	    ord ($c) > 126 ||
	    $c eq "\"" ||
	    $c eq "\'")
	{
	    $c = sprintf ("\\%02x", ord($c));
	}
	elsif ($inquotes && $c eq "\\")
	{
	    $c = "\\\\";
	}

	$escstr .= $c;
    }

    $escstr;
}


#
# convert a hex-escaped string into an unescaped string,
# returning the unescaped string
#
sub un_esc_str {
    my $str = shift;

    $str =~ s{\\([0-9a-f]{2})}{chr(hex($1))}eg;

    $str;
}


sub syslog_die {
    my $msg = shift;

    syslog ("err", $msg);
    die "$msg\n";
}

no warnings; # Redefining syslog
sub syslog {
   eval {
       local $SIG{"__DIE__"}= sub { }; 
       my @log = map { s/\%//mg; } @_;
       Sys::Syslog::syslog(@log);
   }
}
use warnings;

#
# Have a "conversation" with a PAM authentication module. This fools the
# PAM module into authenticating us non-interactively.
#
sub pam_conv_func {
    my @res;
    while ( @_ ) {
	my $code = shift;
	my $msg = shift;
	my $ans = "";

	$ans = $PAM_username if ($code == Authen::PAM::PAM_PROMPT_ECHO_ON() );
	$ans = $PAM_password if ($code == Authen::PAM::PAM_PROMPT_ECHO_OFF() );

	push @res, Authen::PAM::PAM_SUCCESS();
	push @res, $ans;
    }
    push @res, Authen::PAM::PAM_SUCCESS();
    return @res;
}


sub write_dtlog
{
    my ($sref, $group, $service) = @_;

    my $tmnow = time;

    $sref->{"_first_failure"} = $START_TIME
       if ($sref->{"_first_failure"} == 0);

    if (!open (DTLOG, ">>$CF{DTLOGFILE}"))
    {
    	syslog ('err', "could not append to $CF{DTLOGFILE}: $!");
	$CF{"DTLOGGING"} = 0;
    }

    else
    {
	$CF{"DTLOGGING"} = 1;
	print DTLOG ($tmnow,
	   " $group",
	   " $service",
	   " ", 0 + $sref->{"_first_failure"},
	   " ", 0 + $tmnow - $sref->{"_first_failure"},
	   " ", 0 + $sref->{'interval'},
	   " $sref->{'_last_summary'}\n") or
	   syslog ('err', "error writing to $CF{DTLOGFILE}: $!");
	close(DTLOG);
    }
}
 
# Perl's "system" function blocks.  We don't want the mon process to 
# ever block.  So we fork then call system.  Mon will handle the 
# child process cleanup elsewhere.
sub mysystem {
  my @args = @_;
  my $pid;
  print STDERR "mysystem called: @args\n";
  if ($pid = fork()) {         ## parent
      return;
  } elsif (defined($pid)) {    ## child
      system(@args);
      exit(0)
  } else {                      ## parent - fork failed
      print STDERR "You lose!\n";
  }
  print STDERR "mysystem returning\n";
};
