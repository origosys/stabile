#!/usr/bin/perl

use CGI qw(:standard);
use JSON;
use Tie::DBI;
use Data::Dumper;
use ConfigReader::Simple;
use Hash::Merge qw( merge );

$config = ConfigReader::Simple->new("/etc/stabile/config.cfg",
    [qw(
        DBI_PASSWD
        DBI_USER
    )]);
my $dbiuser =  $config->get('DBI_USER') || "irigo";
my $dbipasswd = $config->get('DBI_PASSWD') || "";
$dbopts = {db=>'mysql:steamregister', key=>'uuid', autocommit=>0, CLOBBER=>2, user=>$dbiuser, password=>$dbipasswd};

print "Content-type: application/json\n\n";

unless ( tie(%intreg,'Tie::DBI', Hash::Merge::merge({table=>'networks', key=>'internalip'}, $dbopts)) ) {print "Unable to access network register"};
unless ( tie(%extreg,'Tie::DBI', Hash::Merge::merge({table=>'networks', key=>'externalip'}, $dbopts)) ) {print "Unable to access network register"};

my $remoteip = $ENV{REMOTE_ADDR};
my $internalip = '';
my $externalip = '';
my $gw = '';
my $obj;

if ($remoteip =~ /^10\./) {
    $internalip = $remoteip;
    $obj = $intreg{$internalip};
    $externalip = $obj->{'externalip'};
} else {
    $externalip = $remoteip;
    $obj = $extreg{$externalip};
    $internalip = $obj->{'internalip'};
}
if ($internalip && $internalip ne '--') {
    $gw = "$1.1" if ($internalip =~ /(\d+\.\d+\.\d+)\.\d+/);
}

print qq|{"internalip": "$internalip", "externalip": "$externalip", "gw": "$gw", "remoteip": "$remoteip"}|;

untie %intreg;
untie %extreg;