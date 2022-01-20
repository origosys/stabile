#!/usr/bin/perl

# All rights reserved and Copyright (c) 2020 Origo Systems ApS.
# This file is provided with no warranty, and is subject to the terms and conditions defined in the license file LICENSE.md.
# The license file is part of this source code package and its content is also available at:
# https://www.origo.io/info/stabiledocs/licensing/stabile-open-source-license


# https://valve001.irigo.com/stabile/piston/stats.cgi?1.timestamp=1277045903&1.blk.hda.errs=-1&1.if.vnet1.tx_drop=0&1.if.vnet1.tx_packets=582932&1.if.vnet1.tx_errs=0&1.domain.nrVirtCpu=1&1.if.vnet1.tx_bytes=83963279&1.uuid=5eff51c7-f398-4eb9-8495-567cbb2bad77&1.if.vnet1.rx_packets=2898355&1.blk.hda.wr_req=183467&1.blk.hda.rd_req=206233&1.domain.cpuTime=26164280000000&1.domain.state=1&1.blk.hda.wr_bytes=3615029248&1.if.vnet1.rx_drop=0&1.domain.maxMem=2097152&1.if.vnet1.rx_bytes=1029898520&1.domain.memory=2097152&1.if.vnet1.rx_errs=0&1.blk.hda.rd_bytes=4088299520
# https://valve001.irigo.com/stabile/piston/stats.cgi?5.blk.hda.errs=-1&5.if.vnet1.tx_drop=0&5.if.vnet1.tx_packets=582932&5.if.vnet1.tx_errs=0&5.domain.nrVirtCpu=1&5.if.vnet1.tx_bytes=83963279&5.uuid=5eff51c7-f398-4eb9-8495-567cbb2bad77&5.if.vnet1.rx_packets=2898355&5.blk.hda.wr_req=183467&5.blk.hda.rd_req=206233&5.domain.cpuTime=26164280000000&5.domain.state=1&5.blk.hda.wr_bytes=3615029248&5.if.vnet1.rx_drop=0&5.domain.maxMem=2097152&5.if.vnet1.rx_bytes=1029898520&5.domain.memory=2097152&5.if.vnet1.rx_errs=0&5.blk.hda.rd_bytes=4088299520
#
# rrdtool dump 0de6349b-e10b-4465-90e4-d5a314263649.rrd | grep -v NaN|less
#

# Modifications made to valve001.irigo.com:
#   apt-get install apt-get install rrdtool librrd4 librrds-perl
#   mkdir /var/cache/rrdtool/
#   chown www-data:www-data /var/cache/rrdtool/
#

use CGI::Carp qw(fatalsToBrowser);
#use CGI 3.47 ':standard';
use CGI ':standard';
use JSON;
use URI::Escape;
use Error qw(:try);
use Sys::Syslog qw( :DEFAULT setlogsock);
use Data::Dumper;
use IO::Socket::INET;
use Python::Serialise::Pickle;

# Clear up tainted environment
$ENV{PATH} = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin';
delete @ENV{'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};

my $q = new CGI;
my $params = $q->Vars;

$statsnap = 10; # time in seconds between stats updates - this must be coordinated with values in movepiston


print header;
#
# Put posted information into a hashtable for easy retrieval...
#
$hash = ();

while (my($key,$value) = each(%$params)) {
    @keysplit = split('\.', $key);
	$domainnumber = shift(@keysplit);
	$type = shift(@keysplit);
	$dev = shift(@keysplit);
	$param = shift(@keysplit);

	if ($type eq "domain") {
		$hash->{$domainnumber}->{$type}->{$dev} = $value;
	} elsif ($type eq "blk" or $type eq "if")	{
		$hash->{$domainnumber}->{$type}->{$dev}->{$param} = $value;
	}
}

# print(Dumper($hash));


#
# Find number of domains...
#
$numberOfDomainsSubmitted = getNumberOfDomainsSubmitted($params);

#
# Loop through all domain statistics, putting it in the database...
#
for ($i=1; $i <= $numberOfDomainsSubmitted; $i++) {
	my $uuid = $params->{$i.".uuid"};
    my $timestamp = int(getParam($params, "$i.timestamp"));
	print("Loop $i [".$uuid."]...\n");

#
# Make sure RRD for the uuid exists...
#
	checkRRD($uuid, $timestamp);

#
# Update RRD buckets...
#
#	my $cpuTime = getParam($params, "$i.domain.cpuTime") / getParam($params, "$i.domain.nrVirtCpu");
#    $cpuTime = 1 if ($cpuTime > 1);
	my $cpuTime = getParam($params, "$i.domain.cpuTime")+0;
	my $cpuLoad = getParam($params, "$i.domain.cpuLoad")+0;
	my $rd_bytes = getParam($params, "$i.blk.hd.rd_bytes")+0;
	my $wr_bytes = getParam($params, "$i.blk.hd.wr_bytes")+0;
	my $rd_kbytes_s = getParam($params, "$i.blk.hd.rd_kbytes_s")+0;
	my $wr_kbytes_s = getParam($params, "$i.blk.hd.wr_kbytes_s")+0;
	my $rx_bytes = getParam($params, "$i.if.vnet.rx_bytes")+0;
	my $tx_bytes = getParam($params, "$i.if.vnet.tx_bytes")+0;
	my $rx_kbytes_s = getParam($params, "$i.if.vnet.rx_kbytes_s")+0;
	my $tx_kbytes_s = getParam($params, "$i.if.vnet.tx_kbytes_s")+0;
	my $nrVirtCpu = getParam($params, "$i.domain.nrVirtCpu")+0;
	my $memory = getParam($params, "$i.domain.memory")+0;
	my $maxMem = getParam($params, "$i.domain.maxMem")+0;

	my $rrd_data = "$timestamp".
		":".$cpuTime.
		":".$rd_bytes.
		":".$wr_bytes.
		":".$rx_bytes.
		":".$tx_bytes.
		":".$nrVirtCpu.
		":".$memory.
		":".$maxMem.
		"";
	print "\t$rrd_data\n";

	# Update highres rrd...
	my $rrd_file_highres = "/var/cache/rrdtool/".$uuid."_highres.rrd";
	$rrd_file_highres = $1 if ($rrd_file_highres =~ /(.+)/);
	$rrd_data = $1 if ($rrd_data =~ /(.+)/);
	print("\tUpdating $rrd_file_highres...\n");
	print `/usr/bin/rrdtool update $rrd_file_highres $rrd_data`;

	my $pickle_data = [
		["domains.$uuid.cpuLoad", [$timestamp, $cpuLoad]],
		["domains.$uuid.rx_kbytes_s", [$timestamp, $rx_kbytes_s]],
		["domains.$uuid.tx_kbytes_s", [$timestamp, $tx_kbytes_s]],
		["domains.$uuid.rd_kbytes_s", [$timestamp, $rd_kbytes_s]],
		["domains.$uuid.wr_kbytes_s", [$timestamp, $wr_kbytes_s]],
		["domains.$uuid.rd_bytes", [$timestamp, $rd_bytes]],
		["domains.$uuid.wr_bytes", [$timestamp, $wr_bytes]],
		["domains.$uuid.rx_bytes", [$timestamp, $rx_bytes]],
		["domains.$uuid.tx_bytes", [$timestamp, $tx_bytes]],
		["domains.$uuid.nrVirtCpu", [$timestamp, $nrVirtCpu]],
		["domains.$uuid.memory", [$timestamp, $memory]],
		["domains.$uuid.maxMem", [$timestamp, $maxMem]]
	];
	print pickle_it($pickle_data);

}

print "---\nGot it, thanks!\n";

0;

sub getNumberOfDomainsSubmitted {
	my($parms) = @_;
    my $numberofdomains = 0;
    foreach my $dom (keys %$parms) {
        my @splits =  split('\.', $dom);
        my $domnum = shift(@splits);
        $numberofdomains = $domnum if ($domnum > $numberofdomains);
    }
	return($numberofdomains);
}

sub getParam {
	my($parms, $key) = @_;
	my $value = $parms->{$key};
	return $value;
#	return $value || 0;
}

#
# checkRRD: Checks if an RRD for the specified uuid exists. If not, a new RRD is created.
#
# @param uuid The uuid for which to look for an RRD for
#
sub checkRRD {
	my($uuid, $data_timestamp) = @_;
	my @rrd_order_counter = (
        "domain-cpuTime",
        "hda-rd_bytes",
        "hda-wr_bytes",
        "vnet0-rx_bytes",
        "vnet0-tx_bytes"
    );
	my @rrd_order_gauge = (
        "domain-nrVirtCpu",
        "domain-memory",
        "domain-maxMem",
    );
	my $rrd_datastores = "";
	foreach $dsname (@rrd_order_counter) {
		$rrd_datastores .= " DS:$dsname:COUNTER:30:U:U";
	}
	foreach $dsname (@rrd_order_gauge) {
		$rrd_datastores .= " DS:$dsname:GAUGE:30:U:U";
	}

	my $rrd_file_highres = "/var/cache/rrdtool/".$uuid."_highres.rrd";
	if ((not -e $rrd_file_highres) and ($uuid)) {
		#
		# RRD file for specified uuid not found, so create a new one...
		#

        my @rows_time_span = (
                            10,   # archive for next 10 mins
                            30,   # next 30 ...
                            60,   # next 60
                            120,  # next 2hrs
                            720,  # 12 hrs
                            1440, # 24 hrs
                            2880, # 2 days
                            14 * 24 * 60, # 14 days
                            28 * 24 * 60, # 28 days
                            6 * 30 * 24 * 60, # 6 months 
                           );
        my $extra = 5;
        my $rows = 30;
        my $rows_with_buffer = $rows + $extra;
        my @archives = ();

        foreach my $total_span ( @rows_time_span ) {
            # time span for each slot.
            $steps = ($total_span * 60) / $rows; # when sampling rate is pr. second
            $steps = $steps / $statsnap;         # since we are sampling every 10s
            # 0.9 XFiles Factor 90% of measurements can be UNKNOWN
            push @archives, "RRA:AVERAGE:0.9:$steps:$rows_with_buffer";
        }

        my $exec = "/usr/bin/rrdtool create $rrd_file_highres --start $data_timestamp --step $statsnap $rrd_datastores " . join(" ", @archives);
        print("Creating new highres RRD for $uuid...\n$exec\n");
        print `$exec` . "\n";
	}
}

sub pickle_it {
	my $data = shift;
	# example: [ ["path.mytest", [1332444075,27893687]], ["path.mytest", [1332444076,938.435]], ];
	my($carbon_server) = '127.0.0.1';
	my($carbon_port) = 2004;


	my($message) = pack("N/a*", pickle_dumps($data));

	my($sock) = IO::Socket::INET->new (
	                PeerAddr => $carbon_server,
	                PeerPort => $carbon_port,
	                Proto => 'tcp'
	            );
	            return "Unable to connect to pickle socket: $!\n" unless ($sock->connected);

	$sock->send($message);
	$sock->shutdown(2);
	return '';
}

# Work around P::S::Pickle 0.01's extremely limiting interface.
sub pickle_dumps {
   open(my $fh, '>', \my $s) or die $!;
   my $pickle = bless({ _fh => $fh }, 'Python::Serialise::Pickle');
   $pickle->dump($_[0]);
   $pickle->close();
   return $s;
}