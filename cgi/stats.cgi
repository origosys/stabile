#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license

#
# Network and disk activity example:
# https://valve001.irigo.com//stabile/cgi/stats.cgi?uuid=31fe606f-0b5b-46d2-95a3-c38c4678ab0b&cpuload=true&diskactivity=true&networkactivity=true&mem=true&diskspace=true&from=1276425540&to=1277477100
#
# Disk activity example:
# https://valve001.irigo.com//stabile/cgi/stats.cgi?uuid=5eff51c7-f398-4eb9-8495-567cbb2bad77&cpuload=true&diskactivity=true&networkactivity=true&mem=true&diskspace=true&from=1276425540&to=1277477100
#

#
# apt-get install librrdtool-oo-perl
#

use CGI::Carp qw(fatalsToBrowser);
use CGI ':standard';
use JSON;
use URI::Escape;
use RRDTool::OO;
use Tie::DBI;
use ConfigReader::Simple;


my $q = new CGI;
my $params = $q->Vars;

my $suuid = $params->{"uuid"};
die("\nPlease pass a uuid...") unless $suuid;

if ($params->{"format"} eq "text") {
	print("\n");
} else {
    print(header(
                 -type=>"application/json",
                 "Cache-Control"=>"private, max-age=31536000"));
}

my $config = ConfigReader::Simple->new("/etc/stabile/config.cfg", [qw(DBI_USER DBI_PASSWD CPU_OVERCOMMISION)]);
$dbiuser =  $config->get('DBI_USER') || "irigo";
$dbipasswd = $config->get('DBI_PASSWD') || "";

my @uuids;

unless (tie %domreg,'Tie::DBI', {
    db=>'mysql:steamregister',
    table=>'domains',
    key=>'uuid',
    autocommit=>0,
    CLOBBER=>1,
    user=>$dbiuser,
    password=>$dbipasswd}) {print("Stroke=Error Register could not be accessed\n"); exit;};

if ($domreg{$suuid}) { # We are dealing with a server
    push @uuids, $suuid;
} else { # We are dealing with a system
    foreach my $valref (values %domreg) {
        my $sysuuid = $valref->{'system'};
        push @uuids, $valref->{'uuid'} if ($sysuuid eq $suuid)
    }
}
untie %domreg;

unless (@uuids) {
    print "Stroke=Error Invalid uuid\n";
    exit;
}

my $from = $params->{"from"};
my $to = $params->{"to"};
my $dif = $to - $from;
my $now = time();


if (0 && !$params->{'sum'}) {
    my @items;
    foreach my $uuid (@uuids) {
        my $timestamps = ();
        my $cpuLoad = ();
        my $mem = ();
        my $diskActivity = ();
        my $networkActivityRX = ();
        my $networkActivityTX = ();
        my $diskReads = ();
        my $diskWrites = ();

        #print qq|{"uuid": "$uuid"}| unless (hasRRD($uuid));
        next unless hasRRD($uuid);
        #
        # Fetch data from RRD buckets...
        #
        my $rrd = RRDTool::OO->new(file =>"/var/cache/rrdtool/".$uuid."_highres.rrd");
        #$rrd->fetch_start(start => $params->{"from"}, end => $params->{"to"});

        my $last = $rrd->last();

        #$rrd->fetch_start(start => $last-$dif, end => $last);
        $rrd->fetch_start(start => $now-$dif, end=> $now);
        # $rrd->fetch_skip_undef();

        while(my($timestamp, @value) = $rrd->fetch_next()) {
            last if ($timestamp >= $last && $now-$last<20);
            my $domain_cpuTime = shift(@value);
            my $blk_hda_rdBytes = shift(@value);
            my $blk_hda_wrBytes = shift(@value);
            my $if_vnet0_rxBytes = shift(@value);
            my $if_vnet0_txBytes = shift(@value);
            my $domain_nrVirtCpu = shift(@value);
            my $domain_memory = shift(@value);
            my $domain_maxMem = shift(@value);

            push(@$timestamps, $timestamp);

            # domain_cpuTime is avg. nanosecs spent pr. 1s
            # convert to value [0;1]
            $domain_cpuTime = $domain_cpuTime / 10**9 if ($domain_cpuTime);
            push(@$cpuLoad, int(100*$domain_cpuTime)/100);
            #push(@$mem, $domain_memory);
            # push(@$diskActivity, $blk_hda_rdBytes + $blk_hda_wrBytes);
            $blk_hda_rdBytes = $blk_hda_rdBytes if ($blk_hda_rdBytes);
            push(@$diskReads, int(100*$blk_hda_rdBytes)/100);
            $blk_hda_wrBytes = $blk_hda_wrBytes if ($blk_hda_wrBytes);
            push(@$diskWrites, int(100*$blk_hda_wrBytes)/100);
            push(@$networkActivityRX, int(100*$if_vnet0_rxBytes)/100);
            push(@$networkActivityTX, int(100*$if_vnet0_txBytes)/100);
            #
            # Build JSON result...
            #
        }
        my @t = ( $now-$dif, $now);
        my @a = (undef, undef);

        my $item = ();
        $item->{"uuid"} = $uuid;
        $item->{"timestamps"} = $timestamps || \@t;

        if (lc($params->{"cpuload"}) eq "true") {
            $item->{"cpuload"} = $cpuLoad || \@a;
        }
        if (lc($params->{"mem"}) eq "true") {
            $item->{"mem"} = $mem || \@a;
        }
        # if (lc($params->{"diskactivity"}) eq "true") {
        # 	$item->{"diskactivity"} = $diskActivity;
        #   }
        if (lc($params->{"diskReads"}) eq "true") {
            $item->{"diskReads"} = $diskReads || \@a;
          }
        if (lc($params->{"diskWrites"}) eq "true") {
    #        $item->{"diskWrites"} = $diskWrites || \@a;
        }
        if (lc($params->{"networkactivityrx"}) eq "true") {
            $item->{"networkactivityrx"} = $networkActivityRX || \@a;
        }
        if (lc($params->{"networkactivitytx"}) eq "true") {
            $item->{"networkactivitytx"} = $networkActivityTX || \@a;
        }
        push @items, $item;
    }
    print(to_json(\@items, {pretty=>1}));

} else {
    my @items;
    my %cpuLoad = ();
    my %networkActivityRX = ();
    my %networkActivityTX = ();
    my %diskReads = ();
    my %diskWrites = ();
    my $i = 0;
    foreach my $uuid (@uuids) {
        next unless hasRRD($uuid);
        $i++;
        #
        # Fetch data from RRD buckets...
        #
        my $rrd = RRDTool::OO->new(file =>"/var/cache/rrdtool/".$uuid."_highres.rrd");
        my $last = $rrd->last();
        $rrd->fetch_start(start => $now-$dif, end=> $now);

        while(my($timestamp, @value) = $rrd->fetch_next()) {
            last if ($timestamp >= $last && $now-$last<20);
            my $domain_cpuTime = shift(@value);
            my $blk_hda_rdBytes = shift(@value);
            my $blk_hda_wrBytes = shift(@value);
            my $if_vnet0_rxBytes = shift(@value);
            my $if_vnet0_txBytes = shift(@value);

            # domain_cpuTime is avg. nanosecs spent pr. 1s
            # convert to value [0;1]
            $domain_cpuTime = $domain_cpuTime / 10**9 if ($domain_cpuTime);
            $cpuLoad{$timestamp} +=  $domain_cpuTime;

            $blk_hda_rdBytes = $blk_hda_rdBytes if ($blk_hda_rdBytes);
            $diskReads{$timestamp} += $blk_hda_rdBytes;

            $blk_hda_wrBytes = $blk_hda_wrBytes if ($blk_hda_wrBytes);
            $diskWrites{$timestamp} += $blk_hda_wrBytes;

            $networkActivityRX{$timestamp} += $if_vnet0_rxBytes;
            $networkActivityTX{$timestamp} += $if_vnet0_txBytes;
        }
    }
    my @t = ( $now-$dif, $now);
    my @a = (undef, undef);
    $i = $i || 1;

    my $item = ();
    $item->{"uuid"} = $suuid;
    my @tstamps = sort keys %cpuLoad;
    $item->{"timestamps"} = \@tstamps || \@t;

    if (lc($params->{"cpuload"}) eq "true") {
        my @vals;
        foreach(@tstamps) {push @vals, int(100*$cpuLoad{$_})/100 unless ($cpuLoad{$_} > $i)};
        $item->{"cpuload"} = \@vals || \@a;
    }
    if (lc($params->{"diskReads"}) eq "true") {
        my @vals;
        foreach(@tstamps) {push @vals, int(100*$diskReads{$_})/100;};
        $item->{"diskReads"} = \@vals || \@a;
      }
    if (lc($params->{"diskWrites"}) eq "true") {
        my @vals;
        foreach(@tstamps) {push @vals, int(100*$diskWrites{$_})/100;};
        $item->{"diskWrites"} = \@vals || \@a;
    }
    if (lc($params->{"networkactivityrx"}) eq "true") {
        my @vals;
        foreach(@tstamps) {push @vals, int(100*$networkActivityRX{$_})/100;};
        $item->{"networkactivityrx"} = \@vals || \@a;
    }
    if (lc($params->{"networkactivitytx"}) eq "true") {
        my @vals;
        foreach(@tstamps) {push @vals, int(100*$networkActivityTX{$_})/100;};
        $item->{"networkactivitytx"} = \@vals || \@a;
    }
    push @items, $item;

    print(to_json(\@items, {pretty=>1}));
}


#$rrd->graph(
#      image          => "/var/www/orellana.org/stabile/static/img/rrd_out.png",
#      vertical_label => 'Bits',
#      start => $params->{"from"},
##      end            => time(),
#      draw           => { thickness => 1,
#                          dsname    => "domain-cpuTime",
#                          color     => 'FF0000',
#                          legend    => 'Bits over Time',
#                        },
#    ) if (0);

#
# hasRRD: Checks if a RRD for the specified uuid exists.
#
# @param uuid The uuid for which to look for a RRD for
#
sub hasRRD {
	my($uuid) = @_;
	my $rrd_file = "/var/cache/rrdtool/".$uuid."_highres.rrd";

	if ((not -e $rrd_file) and ($uuid)) {
		return(0);
	} else {
		return(1);
	}
}

