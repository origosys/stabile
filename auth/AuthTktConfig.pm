#
# Config settings for mod_auth_tkt CGI scripts
# 
# Customise as required
#

package AuthTktConfig;

#use strict;
use Tie::DBI;
use Digest::MD5 qw(md5 md5_hex md5_base64);
use Digest::SHA qw(sha512_base64);
use Sys::Syslog qw( :DEFAULT setlogsock);
use Net::Subnet;
use ConfigReader::Simple;

# CSS stylesheet to use (optional)
our $STYLESHEET = 'tkt.css';

# Page title (optional)
our $TITLE = `cat /etc/stabile/config.cfg | sed -n -e 's/^ENGINENAME=//p'`;
chomp $TITLE;
$TITLE = $TITLE || 'Stabile';
$TITLE = "$TITLE - login";

# Fixed back location, overriding any set via back cookie or back arg
our $FIXED_BACK_LOCATION = '';

# Default back location, if none set via back cookie or back arg
our $DEFAULT_BACK_LOCATION = '/stabile/auth/login';

# Boolean flag, whether to fallback to HTTP_REFERER for back location
our $BACK_REFERER = 1;

# For autologin, mode to fallback to if autologin fails ('login' or 'guest')
our $AUTOLOGIN_FALLBACK_MODE = 'login';

# Additional cookies to clear on logout e.g. PHPSESSID
our @NUKE_COOKIES = qw(steamaccount tktuser);

# Debug flag
our $DEBUG = 0;

our $COOKIE_BASE = '';
$COOKIE_BASE = `cat /etc/stabile/cookiebase` if -e "/etc/stabile/cookiebase";
chomp $COOKIE_BASE;
$COOKIE_BASE = ".$COOKIE_BASE" unless ($COOKIE_BASE =~ /^\./);


# Username/password validation for login mode
#   (modify or point $validate_sub somewhere appropriate).
# The validation routine should return a true value (e.g. 1) if the 
#   given username/password combination is valid, and a false value
#   (e.g. 0) otherwise.
# This version uses Apache::Htpasswd and a standard htpasswd file.
sub validate
{
	my ($username, $password) = @_;
	require Apache::Htpasswd;
	my $ht = Apache::Htpasswd->new({ passwdFile => '/etc/apache2/htpasswd-stabile', ReadOnly => 1 });
	return $ht->htCheckPassword($username, $password);
}

sub sqlvalidate {
	my ($username, $password) = @_;
	$username = lc $username;
	$username = $1 if ($username =~ /(.+)/); # Untaint
    my $config = ConfigReader::Simple->new("/etc/stabile/config.cfg",
        [qw(DBI_USER DBI_PASSWD)]);
    my $dbiuser =  $config->get('DBI_USER') || "irigo";
    my $dbipasswd = $config->get('DBI_PASSWD') || "";

	my %register;
	unless (tie %register,'Tie::DBI', {
		db=>'mysql:steamregister',
		table=>'users',
		key=>'username',
		autocommit=>0,
		CLOBBER=>1,
		user=>$dbiuser,
		password=>$dbipasswd}) {return 0};

	my $valid = 0;
	my $validip = 0;
	my $validuser = 0;

	my $allowfrom = $register{$username}->{'allowfrom'} if ($register{$username});
	my $from = $ENV{'REMOTE_ADDR'};
	if ($allowfrom) {
	    my @allows = split(/,\s*/, $allowfrom);
	    foreach my $ip (@allows) {
			if ($ip =~ /(\d+\.\d+\.\d+\.\d+\/\d+)/) { # Match a subnet definition
				$validip = 1 if (subnet_matcher($1)->($from));
			} else {
				$ip = $1 if ($ip =~ /(\d+\.)0\.0\.0/);
				$ip = $1 if ($ip =~ /(\d+\.\d+\.)0\.0/);
				$ip = $1 if ($ip =~ /(\d+\.\d+\.\d+\.)0/);
				$validip = 1 if ($from =~ /^$ip/);
			}
	    }
	} else {
	    $validip = 1;
	}
	if ($register{$username}) {
	    my $privileges = $register{$username}->{'privileges'};
	    $validuser = 1 unless ($privileges =~ /d/);
	}
	if ($validip && $validuser) {
        # First check if md5 checksums match
        my $upassword = $register{$username}->{'password'};
        if ($password && ($upassword eq md5_base64($password) || $upassword eq sha512_base64($password))){
            $valid = 1;
        # If plaintexts match, then assume we are dealing with a new user and convert the password to it's md5 checksum
        } elsif ($password && $register{$username}->{'password'} eq $password) {
            $valid = 1;
            eval {syslogit('info', "Adding system user $username: " . `/usr/sbin/useradd -m "irigo-$username"`); 1;};
    #		eval {`/bin/echo irigo-$username:$password | /usr/sbin/chpasswd`; 1;}; # Doesn't work on Lucid, so we go through the hoops below...
            my $np = `/bin/echo irigo-$username:$password | /usr/sbin/chpasswd -S`; # -S option not supported on older versions
            $np =~ /irigo-$username:(.+)/;
            my $cpass = $1;
            eval {`/usr/sbin/usermod -p '$cpass' irigo-$username`; 1;};
    #		$register{$username}->{'password'} = md5_base64($password);
            $register{$username}->{'password'} = sha512_base64($password);
    #        unless(-d "$basedir$username"){
    #            umask "0000";
    #            mkdir "$basedir$username" or syslogit("info", "Unable to create user dir for $username");
    #        }
        }
		$register{$username}->{'lastlogin'} = $register{$username}->{'curlogin'};
		$register{$username}->{'lastloginfrom'} = $register{$username}->{'curloginfrom'};
		$register{$username}->{'curlogin'} = time;
		$register{$username}->{'curloginfrom'} = $ENV{'REMOTE_ADDR'};
	}
	return $valid;
	untie %register;
}


#our $validate_sub = \&validate;
our $validate_sub = \&sqlvalidate;

# For guest mode (if used), setup guest username
#   Could use a counter or a random suffix etc.
sub guest_user { return 'guest' }
our $guest_sub = \&guest_user;

1;

sub syslogit {
	my ($priority, $msg) = @_;

	setlogsock('unix');
	# $programname is assumed to be a global.  Also log the PID
	# and to CONSole if there's a problem.  Use facility 'user'.
	openlog("", 'pid,cons', 'user');
	syslog($priority, $msg);
	closelog();
	return 1;
}

