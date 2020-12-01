#!/usr/bin/perl
#
# Return a list of hosts which not reachable via ICMP echo
#
# Jim Trocki, trockij@arctic.org
#
# $Id: fping.monitor,v 1.3.2.1 2007/05/11 01:00:26 trockij Exp $
#
#    Copyright (C) 1998, Jim Trocki
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
use strict;

use Getopt::Std;

my %opt;
getopts ("ahr:s:t:T", \%opt);

sub usage
{
    print <<EOF;
usage: fping.monitor [-a] [-r num] [-s num] [-t num] [-T] host [host...]

    -a		only report failure if all hosts are unreachable
    -r num	retry "num" times for each host before reporting failure
    -s num	consider hosts which respond in over "num" msecs failures
    -t num	wait "num" msecs before sending retries
    -T		traceroute to each failed host. CAUTION: this may cause
    		this monitor to hang for a very long time

EOF

    exit;
}

usage if ($opt{"h"});

my $TIMEOUT = $opt{"t"} || 2000;
my $RETRIES = $opt{"r"} || 3;
my $CMD = "fping -e -r $RETRIES -t $TIMEOUT";
my $START_TIME = time;
my $END_TIME;
my %details;

exit 0 if (@ARGV == 0);

open (IN, "$CMD @ARGV 2>&1 |") ||
	die "could not open pipe to fping: $!\n";

my @unreachable;
my @alive;
my @addr_not_found;
my @slow;

while (<IN>)
{
    chomp;
    if (/^(\S+) is unreachable/)
    {
    	push (@unreachable, $1);
    }

    elsif (/^(\S+) is alive \((\S+)/)
    {
	if ($opt{"s"} && $2 > $opt{"s"})
	{
	    push (@slow, [$1, $2]);
	}

	else
	{
	    push (@alive, [$1, $2]);
	}
    }

    elsif (/^(\S+)\s+address\s+not\s+found/)
    {
    	push @addr_not_found, $1;
	push @unreachable, $1;
    }

    #
    # fping can output a number of messages in addition to the eventual
    # reachable/unreachable.  Ignore them since we'll also get the main
    # "unreachable" message).
    #
    elsif (/^ICMP .+ from \S+ for ICMP Echo sent to /)
    {
       # do nothing
    }

    #
    # ICMP Host Unreachable from 1.2.3.4 for ICMP Echo sent to 2.4.6.8
    #
    elsif (/^ICMP (.*) for ICMP Echo sent to (\S+)/)
    {
	    if (! exists $details{$2})
	    {
		    $details{$2}= $_;
	    }
    }

    elsif (/^ICMP Time Exceeded from \S+ for ICMP Echo sent to (\S+) /)
    {
	push @unreachable, $1;
    }

    else
    {
    	print STDERR "unidentified output from fping: [$_]\n";
    }
}

close (IN);

$END_TIME = time;

my $retval = $? >> 8;

if ($retval == 3)
{
    print "fping: invalid cmdline arguments [$CMD @ARGV]\n";
    exit 1;
}

elsif ($retval == 4)
{
    print "fping: system call failure\n";
    exit 1;
}

elsif ($retval == 1 || $retval == 2 || @slow != 0)
{
    print join (" ", sort (@unreachable, map { $_->[0] } @slow)), "\n\n";
}

elsif ($retval == 0)
{
    print "\n";
}

else
{
    print "unknown return code ($retval) from fping\n";
}

print "start time: " . localtime ($START_TIME) . "\n";
print "end time  : " . localtime ($END_TIME) . "\n";
print "duration  : " . ($END_TIME - $START_TIME) . " seconds\n\n";

if (@unreachable != 0)
{
    print <<EOF;
------------------------------------------------------------------------------
unreachable hosts
------------------------------------------------------------------------------
EOF
    print join ("\n", @unreachable), "\n\n";

    if (@addr_not_found != 0)
    {
	print "address not found for @addr_not_found\n";
    }

    print "\n";

	foreach my $ipnum (@unreachable)
	{
		print $ipnum, " : ", $details{$ipnum}, "\n" if exists $details{$ipnum};
	}
}


if (@slow != 0)
{
    print <<EOF;
------------------------------------------------------------------------------
slow hosts (response time which exceeds $opt{s}ms)
------------------------------------------------------------------------------
EOF

    foreach my $host (@slow)
    {
    	printf ("%-40s %.2f ms\n", @{$host});
    }
}



if (@alive != 0)
{
    print <<EOF;
------------------------------------------------------------------------------
reachable hosts                          rtt
------------------------------------------------------------------------------
EOF
    
    for (my $i = 0; $i < @alive; $i++)
    {
    	printf ("%-40s %.2f ms\n", @{$alive[$i]});
    }
}

#
# traceroute
#
if ($opt{"T"} && @unreachable)
{
    foreach my $host (@unreachable)
    {
    	system ("traceroute -w 3 $host 2>&1");
    }

    print "\n";
}

#
# fail only if all hosts do not respond
#
if ($opt{"a"})
{
    if (@unreachable == @ARGV)
    {
    	exit 1;
    }

    exit 0;
}

exit 1 if (@slow != 0);

exit $retval;
