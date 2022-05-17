#!/usr/bin/perl

use Time::HiRes qw( time );
use Getopt::Long qw(GetOptions);

Getopt::Long::Configure qw(gnu_getopt); # Allow combining short options
our %options=();
GetOptions(\%options, 'iterations|i=s', 'host|h=s', 'username|u=s', 'password|p=s', 'db|d=s', 'help', 'debug', 'port=s', 'json|j');

my $iterations = ($options{iterations}) || 100;
my $host = ($options{host}) || 'localhost';
my $user = ($options{username}) || '';
my $pwd = ($options{password}) || '';
my $db = ($options{db}) || 'mongotesterDB';
my $json = ($options{json}) || '';
my $help = ($options{help}) || '';
my $debug = ($options{debug}) || '';
my $port = ($options{port}) || '';
my $authdb = ($options{authdb}) || '';

if ($help) {
    print <<end
Usage: mongotest [-i] [-h] [-u] [-p] [-j] [-d]
-i, --iterations, (default: 100)
-h, --host, (default: localhost)
-u, --username
-p, --password
-j, --json
-d, --db, (default: mongotesterDB)
--help
--debug
--port
--authdb
end
        ;
    print <<END

mongotester will try to insert, update, read and delete a number of simple test documents into a test database, that is created for the purpose.
The test database's default name is "mongotesterDB". The test database will be dropped before testing, but kept after for possible inspection.
END
    ;
    exit;
}
unless (`which mongo`) {
    print("You must have mongo installed in your path on this system!\n");
    exit;
}

if (-e "/etc/mongod.pass" && !$user) { # We are in a stabile.io environment
    $user = 'stabile';
    $pwd = `cat /etc/mongod.pass`;
    chomp $pwd;
}

my $hostport = '';
if ($host) {
    $hostport = "--host $host";
    $hostport .= " --port $port" if ($port);
}
print "Dropping $db\n" unless ($json);
my $res = `echo "db.getSiblingDB('$db').dropDatabase()" | mongo -u "$user" -p "$pwd" $hostport  --authenticationDatabase "$authdb"`;
unless (!($res =~ /"Error" : 1/ ) || $debug) {
    die "Error: $res\n";
}

$res = `echo "sh.enableSharding('$db')" | mongo -u "$user" -p "$pwd" $hostport  --authenticationDatabase "$authdb"`;
unless ($res =~ /"ok" : 1/ || $debug) {
    die "Error: $res\n";
}
$res = `echo "db.getSiblingDB('$db').testCollection.ensureIndex( { _id : 'hashed' } )" | mongo -u "$user" -p "$pwd" $hostport  --authenticationDatabase "$authdb"`;
print "Error: $res\n" unless ($res =~ /"ok" : 1/ || $debug);
$res = `echo "sh.shardCollection('$db.testCollection', { '_id' : 'hashed' } )" | mongo -u "$user" -p "$pwd" $hostport  --authenticationDatabase "$authdb"`;
print "Error: $res\n" unless ($res =~ /"ok" : 1/ || $debug);

my $itime;
my $rtime;
my $utime;
my $dtime;

# Insert
print "Inserting $iterations documents into $db.testCollection\n" unless ($json);
my $begin_time = time();
$res = `echo "for (var i = 1; i <= $iterations; i++) db.getSiblingDB('$db').testCollection.insert( { testkey : 'testvalue' + i } )" | mongo -u "$user" -p "$pwd" $hostport  --authenticationDatabase "$authdb"`;
my $end_time = time();
if ($res =~ /"nInserted" : 1/) {
    $itime = sprintf("%.2f", $end_time - $begin_time);
} else {
    die "Error: $res\n";
}

# Update
print "Updating $iterations documents in $db.testCollection\n" unless ($json);
$begin_time = time();
$res = `echo "db.getSiblingDB('$db').testCollection.find().forEach( function(myDoc) { db.getSiblingDB('$db').testCollection.updateOne({testkey: myDoc.testkey }, {\\\$set: {testkey: myDoc.testkey + '_updated' }} ) } );" | mongo -u "$user" -p "$pwd" $hostport  --authenticationDatabase "$authdb"`;
$end_time = time();
if ($res =~ /bye/) {
    $utime = sprintf("%.2f", $end_time - $begin_time);
} else {
    print "$res\n";
}

# Read
print "Reading $iterations documents from $db.testCollection\n" unless ($json);
$begin_time = time();
$res = `echo "db.getSiblingDB('$db').testCollection.find().forEach( function(myDoc) { print(myDoc.testkey); } );" | mongo -u "$user" -p "$pwd" $hostport  --authenticationDatabase "$authdb"`;
$end_time = time();
$rtime = sprintf("%.2f", $end_time - $begin_time);

# Delete
print "Deleting $iterations documents from $db.testCollection\n" unless ($json);
$begin_time = time();
$res = `echo "db.getSiblingDB('$db').testCollection.find().forEach( function(myDoc) { db.getSiblingDB('$db').testCollection.deleteOne({_id: myDoc._id }) } );" | mongo -u "$user" -p "$pwd" $hostport  --authenticationDatabase "$authdb"`;
$end_time = time();
if ($res =~ /bye/) {
    $dtime = sprintf("%.2f", $end_time - $begin_time);
} else {
    print "$res\n";
}

if ($json) {
    print qq|{"insert": $itime, "update": $utime, "read": $rtime, "delete": $dtime}\n|;
} else {
    printf("\nMongoDB took $itime seconds inserting $iterations documents\n", $end_time - $begin_time);
    printf("MongoDB took $utime seconds updating $iterations documents\n", $end_time - $begin_time);
    printf("MongoDB took $rtime seconds reading $iterations documents\n", $end_time - $begin_time);
    printf("MongoDB took $dtime seconds deleting $iterations documents\n", $end_time - $begin_time);
    if ($debug) {
        $res = `echo "db.getSiblingDB('$db').testCollection.getShardDistribution()" | mongo -u "$user" -p "$pwd" $hostport  --authenticationDatabase "$authdb"`;
        print "$res\n";
    }
}