#!/usr/bin/perl -w


# mod_auth_tkt sample logout script
# 
# Note that this needs script needs to be available locally on all domains 
#   if using multiple domains (unlike login.cgi, which only needs to exist
#   on one domain).
#

use File::Basename;
#use lib dirname($ENV{SCRIPT_FILENAME});
use lib "./";
use Apache::AuthTkt 0.03;
use AuthTktConfig;
use CGI qw(:standard);
use URI::Escape;
use URI;
use Data::Dumper;
use strict;

# Clear up tainted environment
$ENV{PATH} = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin';
delete @ENV{'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};

# ------------------------------------------------------------------------
# Configuration settings in AuthTktConfig.pm

# ------------------------------------------------------------------------
# Main code begins
my $at = Apache::AuthTkt->new(conf => $ENV{MOD_AUTH_TKT_CONF});
my $q = CGI->new;
my ($server_name, $server_port) = split /:/, $ENV{HTTP_HOST};
$server_name ||= $ENV{SERVER_NAME};
$server_port ||= $ENV{SERVER_PORT};
my $AUTH_DOMAIN = $AuthTktConfig::COOKIE_BASE || $at->domain|| $server_name;
my $back = '';
$back = $AuthTktConfig::FIXED_BACK_LOCATION if $AuthTktConfig::FIXED_BACK_LOCATION;
$back ||= $q->cookie($at->back_cookie_name) if $at->back_cookie_name;
$back ||= $q->param($at->back_arg_name) if $at->back_arg_name;
$back = $AuthTktConfig::DEFAULT_BACK_LOCATION if $AuthTktConfig::DEFAULT_BACK_LOCATION;
#$back ||= $ENV{HTTP_REFERER} if $ENV{HTTP_REFERER} && $AuthTktConfig::BACK_REFERER;
if ($back && $back =~ m!^/!) {
  my $hostname = $server_name;
  my $port = $server_port;
  $hostname .= ':' . $port if $port && $port != 80 && $port != 443;
  $back = sprintf "http%s://%s%s", ($port == 443 ? 's' : ''), $hostname, $back;
} elsif ($back && $back !~ m/^http/i) {
  $back = 'http://' . $back;
}
$back = uri_unescape($back) if $back =~ m/^https?%3A%2F%2F/;
my $back_html = escapeHTML($back) if $back;

# Logout by resetting the auth cookie
my @cookies = cookie(-name => $at->cookie_name, -value => '', -expires => '-1h', -path => '/',
    ($AUTH_DOMAIN ? (-domain => $AUTH_DOMAIN) : ()));
push @cookies, map { cookie(-name => $_, -value => '', -expires => '-1h', path => '/',
    ($AUTH_DOMAIN ? (-domain => $AUTH_DOMAIN) : ()) ) } @AuthTktConfig::NUKE_COOKIES;


#my $user = $ENV{'REMOTE_USER'};
#my $account = $q->cookie('steamaccount') if ($q); # User is requesting access to another account
#if ($account ne $user) {
#    $user = $account;
#}
#$user = $1 if $user =~ /(.+)/; #untaint
#`pkill -TERM -f "$user~ui_update.cgi"`; # Kill ui_update which in turn removes tasks from /tmp

my $session = $q->param('s');
`pkill -f ~$session.tasks` if ($session);

my $redirected = 0;
if ( $q->param('js') ) {
  print $q->header(-content_type => "application/javascript", -cookie => \@cookies);
  print qq|document.cookie = '| . $at->cookie_name . qq|=; Domain=$AUTH_DOMAIN; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';\n|;
  exit;
} elsif ($back) {
  my $b = URI->new($back);
  # If $back domain doesn't match $AUTH_DOMAIN, add ticket reset to back
  if (!($b->host =~ /$AUTH_DOMAIN/i) && !($AUTH_DOMAIN !~ /$b->host/i)) {
    $back .= $b->query ? '&' : '?';
    $back .= $at->cookie_name . '=';
  }

  if ($AuthTktConfig::DEBUG) {
    print $q->header(-cookie => \@cookies);
  } else {
    # Set (local) cookie, and redirect to $back
    print $q->header(
      -cookie => \@cookies,
      -location => $back,
    );
    # For some reason, a Location: redirect doesn't seem to then see the cookie,
    #   but a meta refresh one does - weird
    print $q->start_html(
      -head => meta({
        -http_equiv => 'Pragma', -content => "no-cache"
      }),
#      -head => meta({
#        -http_equiv => 'refresh', -content => "0;URL=$back"
#        -http_equiv => 'refresh', -content => "0;URL=login"
#      })
    );
#    $redirected = 1;
  }
}

# If no $back, just set the auth cookie and hope for the best
else {
  print $q->header(-cookie => \@cookies);
}

my @style = ();
@style = ( '-style' => { src => $AuthTktConfig::STYLESHEET } )
  if $AuthTktConfig::STYLESHEET;
my $title = $AuthTktConfig::TITLE || "Logout Page";

unless ($redirected) {
  # If here, either some kind of error or no back ref found
  print $q->start_html(
      -head => meta({
        -http_equiv => 'Pragma', -content => "no-cache"
      }),
      -title => $title,
      @style,
    );
  print <<EOD;
<div align="center">
<!-- h1>$title</h1 -->
EOD
  if ($AuthTktConfig::DEBUG) {
    print <<EOD;
<pre>
back: $back
back_html: $back_html
</pre>
EOD
  }
  print <<EOD;
<p>You are now logged out of $AUTH_DOMAIN.</p>
<!-- script>document.location="login";</script -->
EOD
  print qq(<p><a href="$back_html">Previous Page</a></p>\n) if $back_html;
  print <<EOD;
</div>
</body>
</html>
EOD
}

# vim:sw=2:sm:cin

