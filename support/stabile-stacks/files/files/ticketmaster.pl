#!/usr/bin/perl

# Validates and generates auth_tkt tickets
# If a ticket is passed as only argument, and optionally a second argument, which is either '--debug',
# or 'priviliges' it is validated against /etc/apache2/conf.d/auth_tkt_cgi.conf and the uid and
# optionally privileges from database are printed.
# If two arguments are passed and the last is not '--debug' or 'privileges', they are interpreted
# as a user name and an auth_tkt secret, and a ticket is generated and printed.
# /co

#use lib "$real_path";
use Apache::AuthTkt 0.03;
use Data::Dumper;

my $u = shift if $ARGV[0];
my $secret = shift if $ARGV[0];
my $data = shift if $ARGV[0];

if ($secret eq '--debug') {
    $debug = 1;
    $secret = '';
}
if ($secret eq '--dir') {
    $dirmode = 1;
    $secret = '';
}

if ($u && $secret && $secret ne 'privileges') {
    my $at;
    if ($secret eq '--') {
        $at = Apache::AuthTkt->new(conf => '/etc/apache2/conf.d/auth_tkt.conf');
    } else {
        $at = Apache::AuthTkt->new(
                secret => $secret,
                digest_type => 'SHA512',
            );
    }

    my $user_data = join(':', time(), ($ip_addr ? $ip_addr : ''), $data);    # Optional
    my $tkt = $at->ticket(uid => $u, data => $user_data, ip_addr => $ip_addr, tokens => '', debug => 0);
    print "$tkt\n";
} elsif ($u) {
    my $at = Apache::AuthTkt->new(conf => '/etc/apache2/conf.d/auth_tkt.conf');
    my $valid = $at->validate_ticket($u);
    if (time - $valid->{ts} > 2*60*60) { # Default auth_tkt timeout is 2 hours
        print "\n";
    } else { # Ticket has not timed out
        my $uid = $valid->{uid};
        print "$uid\n";
    }
    print Dumper($valid) if ($debug);
    if ($dirmode) {
        my @data = split(/:/, $valid->{data});
        print $data[2], "\n";
    }
}

