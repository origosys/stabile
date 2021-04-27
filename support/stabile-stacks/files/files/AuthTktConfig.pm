#
# Config settings for mod_auth_tkt CGI scripts
# 
# Customise as required
#

package AuthTktConfig;

use strict;
use Authen::Simple::LDAP;

# CSS stylesheet to use (optional)
our $STYLESHEET = 'tkt.css';

# Page title (optional)
our $TITLE = 'File Browser';

# Fixed back location, overriding any set via back cookie or back arg
our $FIXED_BACK_LOCATION = '';

# Default back location, if none set via back cookie or back arg
our $DEFAULT_BACK_LOCATION = '/origo/elfinder/index.cgi';

# Boolean flag, whether to fallback to HTTP_REFERER for back location
our $BACK_REFERER = 0;

# For autologin, mode to fallback to if autologin fails ('login' or 'guest')
our $AUTOLOGIN_FALLBACK_MODE = 'login';

# Additional cookies to clear on logout e.g. PHPSESSID
our @NUKE_COOKIES = qw(PHPSESSID);

# Debug flag
our $DEBUG = 0;

# Username/password validation for login mode
#   (modify or point $validate_sub somewhere appropriate).
# The validation routine should return a true value (e.g. 1) if the 
#   given username/password combination is valid, and a false value
#   (e.g. 0) otherwise.
# This version uses Apache::Htpasswd and a standard htpasswd file.
sub validate
{
    my ($username, $password) = @_;
    my $internalip = `cat /tmp/internalip`;
    $internalip = `cat /etc/origo/internalip` if (-e '/etc/origo/internalip');
    my $dominfo = `samba-tool domain info \`cat $internalip\``;
    my $sambadomain = $1 if ($dominfo =~ /Domain\s+: (\S+)/);
    my @domparts = split(/\./, $sambadomain);
    my $userbase = "CN=users,DC=" . join(",DC=", @domparts);
    chomp $internalip;
    my $ldap = Authen::Simple::LDAP->new(
        binddn  => $username . '@' . $domparts[0],
        bindpw  => $password,
        host    => $internalip,
        basedn  => $userbase,
        filter  => '(&(objectClass=organizationalPerson)(objectClass=user)(sAMAccountName=%s))'
    );
    return ( $ldap->authenticate( $username, $password ) );
}
our $validate_sub = \&validate;

# For guest mode (if used), setup guest username
#   Could use a counter or a random suffix etc.
sub guest_user { return 'guest' }
our $guest_sub = \&guest_user;

1;

