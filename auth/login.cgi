#!/usr/bin/perl -w

# mod_auth_tkt sample login script - runs as a vanilla CGI, under
#   mod_perl 1 via Apache::Registry, and under mod_perl2 via 
#   ModPerl::Registry.
#
# This script can run in a few different modes, depending on how it is 
#   named. Copy the script to a cgi-bin area, and create appropriately 
#   named symlinks to access the different behaviours. 
# Modes:
#   - login mode (default): request a username and password and test via
#     $AuthTktConfig::validate_sub - if successful, issue an auth ticket 
#     and redirect to the back location
#   - autologin mode ('autologin.cgi'): [typically used to allow tickets 
#     across multiple domains] if no valid auth ticket exists, redirect
#     to the login (or guest) version; otherwise automatically redirect 
#     to the back location passing the current auth ticket as a GET 
#     argument. mod_auth_tkt (>= 1.3.8) will turn this new ticket into 
#     an auth cookie for the new domain if none already exists.
#   - guest mode ('guest.cgi'): [DEPRECATED - use TktAuthGuestLogin instead]
#     automatically issues an auth ticket a special username (as defined in 
#     $AuthTktConfig::guest_sub, default 'guest'), and redirect to the back 
#     location 
#

use File::Basename;
#use lib dirname($ENV{SCRIPT_FILENAME});
use lib ".";
use Apache::AuthTkt 0.03;
use AuthTktConfig;
use CGI qw(:standard);
use CGI::Cookie;
use URI::Escape;
use URI;
use Data::Dumper;
use File::Path;
use Digest::SHA qw(sha512_base64);

$ENV{PATH} = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin';
delete @ENV{'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};

# Main code begins
my $at = Apache::AuthTkt->new(conf => $ENV{MOD_AUTH_TKT_CONF});
my $q = CGI->new;
my ($server_name, $server_port) = split /:/, $ENV{HTTP_HOST} if $ENV{HTTP_HOST};
$server_name ||= $ENV{SERVER_NAME} if $ENV{SERVER_NAME};
$server_port ||= $ENV{SERVER_PORT} if $ENV{SERVER_PORT};

my $AUTH_DOMAIN = $at->domain || $server_name;
my @auth_domain = $AUTH_DOMAIN ? ( -domain => $AUTH_DOMAIN ) : ();
my $ticket = $q->cookie($at->cookie_name);
my $probe = $q->cookie('auth_probe');
my $back_cookie = $q->cookie($at->back_cookie_name) if $at->back_cookie_name;
my $have_cookies = $ticket || $probe || $back_cookie || '';
my $back = '';
$back = $AuthTktConfig::FIXED_BACK_LOCATION if $AuthTktConfig::FIXED_BACK_LOCATION;
$back ||= $back_cookie;
$back ||= $q->param($at->back_arg_name) if $at->back_arg_name;
#$back ||= $ENV{HTTP_REFERER} if $ENV{HTTP_REFERER} && $AuthTktConfig::BACK_REFERER;
$back ||= $AuthTktConfig::DEFAULT_BACK_LOCATION if $AuthTktConfig::DEFAULT_BACK_LOCATION;
if ($back && $back =~ m!^/!) {
  my $hostname = $server_name;
  my $port = $server_port;
  $hostname .= ':' . $port if $port && $port != 80 && $port != 443;
  $back = sprintf "http%s://%s%s", ($port == 443 ? 's' : ''), $hostname, $back;
} elsif ($back && $back !~ m/^http/i) {
  $back = 'http://' . $back;
}
$back = uri_unescape($back) if $back && $back =~ m/^https?%3A%2F%2F/;
my $back_esc = uri_escape($back) if $back;
my $back_html = escapeHTML($back) if $back;

my ($fatal, @errors);
my ($mode, $location, $suffix) = fileparse($ENV{SCRIPT_NAME}, '\.cgi', '\.pl');
$mode = 'autologin' if ($ENV{SCRIPT_NAME} =~ /autologin/);
$mode = 'login' unless ($mode eq 'guest' || $mode eq 'autologin');
my $self_redirect = $q->param('redirect') || 0;
$username = '';
$username = &trim(lc($q->param('username'))) if ($q->param('username'));
my $password = $q->param('password');
my $totp = $q->param('totp');
my $timeout = $q->param('timeout');
my $unauth = $q->param('unauth');
my $ip_addr = $at->ignore_ip ? '' : $ENV{REMOTE_ADDR};
my $redirected = 0;
my $validtoken = 0;

my $logo = "/stabile/static/img/logo.png";
my $logo_icon = "/stabile/static/img/logo-icon.png";
# my $logo_icon_32 = "/stabile/static/img/logo-icon-32.png";
$logo = "/stabile/static/img/logo-$AUTH_DOMAIN.png" if (-e "/var/www/stabile/static/img/logo-$AUTH_DOMAIN.png");
$logo_icon = "/stabile/static/img/logo-icon-$AUTH_DOMAIN.png" if (-e "/var/www/stabile/static/img/logo-icon-$AUTH_DOMAIN.png");

# Actual processing

my $installsystem = $q->param('installsystem');
my $systemcookie;
if ($installsystem) {
   $systemcookie = CGI::Cookie->new(
      -name => 'installsystem',
      -value => "$installsystem",
      -path => '/',
  );
};

my $tktusercookie = CGI::Cookie->new(
  -name => 'tktuser',
  -value => "",
  @auth_domain,
  -path => '/',
  -expires => '-1h'
);
my $auth_tktcookie = CGI::Cookie->new(
  -name => $at->cookie_name,
  -value => "",
  @auth_domain,
  -path => '/',
  -expires => '-1h'
);


# If no cookies found, first check whether cookies are supported
if (! $have_cookies && !$q->param('api')) {
  # If this is a self redirect warn the user about cookie support
  if ($self_redirect) {
    $fatal = "Your browser does not appear to support cookies or has cookie support disabled.<br />\nThis site requires cookies - please turn cookie support on or try again using a different browser.";
  }
  # If no cookies and not a redirect, redirect to self to test cookies
  else {
    my $extra = '';
    $extra .= 'timeout=1' if $timeout;
    $extra .= 'unauth=1' if $unauth;
    $extra .= "installsystem=$installsystem" if $installsystem;
    $extra = "&$extra" if $extra;

    my $cookie = CGI::Cookie->new(-name => 'auth_probe', -value => 1, @auth_domain);

    print redirect(
      -uri => sprintf("%s%s%s?redirect=%s&%s=%s%s",
                        $location, $mode, $suffix, $self_redirect + 1, $at->back_arg_name,
                        $back_esc || '', $extra),
      -cookie => [$cookie, $systemcookie],
    );

    #print $q->header(
    #  -cookie => [$cookie, $systemcookie],
    #);
    # For some reason, a Location: redirect doesn't seem to then see the cookie,
    #   but a meta refresh one does - go figure
    #print $q->start_html(
    #  -head => meta({
    #    -http_equiv => 'Pragma', -content => "no-cache"
    #  }),
    #  -head => meta({
    #    -http_equiv => 'refresh', -content => ("0;URL=" . sprintf("%s%s%s?redirect=%s&%s=%s%s",
    #      $location, $mode, $suffix, $self_redirect + 1, $at->back_arg_name,
    #      $back_esc || '', $extra))
    #}));
    $redirected = 1;
  }

} elsif ($mode eq 'autologin') {
  $ticket = $ticket || $q->param($at->cookie_name);
  # If we have a ticket, redirect to $back, including ticket as GET param
  if ($ticket && $back && ! $timeout) {
#    my $b = URI->new($back);
#    $back .= $b->query ? '&' : '?';
#    $back .= $at->cookie_name . '=' . $ticket;

    #print $q->redirect($back);
    my %params = $q->Vars;
    $steamaccount = $params{'account'};
    if ($steamaccount) {
      my $cookie = $q->cookie(-name => 'steamaccount',
          -value => $steamaccount,
          -path => '/',
          -secure => $at->require_ssl,
          @auth_domain,
      );
    # Let's extract username from ticket, rather than trusting param
      my $valid = $at->validate_ticket($ticket);
      unless (time - $valid->{ts} > 2*60*60) { # Default auth_tkt timeout is 2 hours
      #  $username = $valid->{uid};
      }
      $session = substr($ticket, 0, 6);
      set_cookie_redirect($ticket, $back, $cookie);
    } else {
      set_cookie_redirect($ticket, $back, $systemcookie);
    }
    $redirected = 1;

  }
  # Can't autologin - change mode to either guest or login
  else {
    $mode = $AuthTktConfig::AUTOLOGIN_FALLBACK_MODE;
  }
}

unless ($fatal || $redirected) {
  if (! $at) {
    $fatal = "AuthTkt error: " . $at->errstr;

  } elsif ($mode eq 'login') {
    if ($username && $password) {
      my ($valid, $tokens) = $AuthTktConfig::validate_sub->($username, $password, $totp);
      $validtoken = $valid;
      if ($valid == 2) { # User has 2fa enabled - present 2fa login screen
        push @errors, 'Indtast venigst din 2-faktor authentication kode';
      } elsif ($valid) {
#       my $user_data = join(':', encrypt($password), time(), ($ip_addr ? $ip_addr : ''));
        my $user_data = join(':', time(), ($ip_addr ? $ip_addr : ''));    # Optional
        my $tkt = $at->ticket(uid => $username, data => $user_data, 
          ip_addr => $ip_addr, tokens => $tokens, debug => $AuthTktConfig::DEBUG);
        if (! @errors) {
          $redirected = set_cookie_redirect($tkt, $back, $systemcookie);
          $fatal = "Login successful.";
        }
      }
      else {
        push @errors, "Invalid username or password.";
      }
    }
  } elsif ($mode eq 'guest') {
    # Generate a guest ticket and redirect to $back
    my $tkt = $at->ticket(uid => $AuthTktConfig::guest_sub->(), ip_addr => $ip_addr);
    if (! @errors) {
#      $redirected = $set_cookie_redirect->($tkt, $back, $systemcookie);
      $redirected = set_cookie_redirect($tkt, $back, $systemcookie);
      $fatal = "No back link found.";
    }
  }
}

my @style = ();
#@style = ( '-style' => { src => $AuthTktConfig::STYLESHEET } )
#  if $AuthTktConfig::STYLESHEET;
@style = ( '-style' => { src => '/stabile/static/css/style.css' } );
my $title = $AuthTktConfig::TITLE || "\u$mode Page";
unless ($redirected) {
  if ($q->param('api')) {
    print $q->header("application/json");
    print qq|{"status": "Error"}\n|;
    exit;
  }
    # If here, either some kind of error or a login page
  if ($fatal) {
    print $q->header(
        -cookie => [$systemcookie,$auth_tktcookie,$tktusercookie]
    ),
      $q->start_html(
        -head => meta({-http_equiv => 'Pragma', -content => "no-cache"}),
        -title => $title,
        @style,
      );
  } else {
    push @errors, qq(Your session has timed out.) if $timeout;
    push @errors, qq(You are not authorised to access this area.) if $unauth;
    my $foc = ($username?'1':'0');
    print $q->header(-status=>'401', -cookie => [$systemcookie,$auth_tktcookie,$tktusercookie]),
      $q->start_html(
        -head => [
            meta({-http_equiv => 'Pragma', -content => "no-cache"}),
            $q->Link({
               -rel => 'SHORTCUT ICON',
               -href =>$logo_icon,
            })
          ],
        -meta=>{'viewport'=>'width=device-width, initial-scale=1'},
        -link=>{'rel'=>'icon', 'href'=>$logo_icon, 'sizes'=>'192x192'},
        -title => $title,
        -class => 'login',
        -onLoad => "getFocus()",
        @style,
        -script => qq(
function getFocus() {
  document.forms[0].elements[$foc].focus();
  document.forms[0].elements[$foc].select();
}));
  }

  print <<EOD;
<div align="center">
EOD


  if ($AuthTktConfig::DEBUG) {
    my $cookie_name = $at->cookie_name;
    my $back_cookie_name = $at->back_cookie_name || '';
    my $back_arg_name = $at->back_arg_name || '';
    my $cookie_expires = $at->cookie_expires || 0;
    print <<EOD;
<pre>
server_name: $server_name
server_port: $server_port
domain: $AUTH_DOMAIN
mode: $mode
suffix: $suffix
cookie_name: $cookie_name
cookie_expires: $cookie_expires
back_cookie_name: $back_cookie_name
back_arg_name: $back_arg_name
back: $back
back_esc: $back_esc
back_html: $back_html
have_cookies: $have_cookies
ip_addr: $ip_addr
EOD
    if ($Apache::AuthTkt::VERSION >= 2.1) {
      printf "digest_type: %s\n", $at->digest_type;
    }
    print "</pre>\n";
  }

  if ($fatal) {
    print qq(<p class="error">$fatal</p>\n);
  }

  else {
    my $sha_pwd = $password;
    $sha_pwd = sha512_base64($password) unless (length($password) == 86);
    print qq(<p class="alert alert-info" style="width:400px; padding:10px; margin: 10px;"><span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span>\n), join(qq(<br />\n), @errors), "</p>\n"
      if @errors;
    print <<EOD;
<div id="auth-header">
    <a href="#"><img src="$logo" border="0" style="height:48px; vertical-align:middle; margin:20px;"/></a>
</div>
<form name="login" method="post" style="width:200px;" id="auth-form" accept-charset="utf-8">
EOD
    ;
    if ($validtoken == 2) {
      print <<EOD;
 			       <input type="hidden" name="username" id="username" value="$username">
                   <input type="hidden" name="password" id="password" value="$sha_pwd">
                   <img class="logo" src="/stabic/img/google_auth.png" style="margin-bottom: 20px;">
                   <input type="number" pattern="[0-9.]+" maxlength="6" minlength="6" name="totp" id="totp" class="form-control required password" aria-label="totp" aria-required="true" required="" placeholder="Authentication Token"  autofocus="on">
EOD
      ;
    } else {
      print <<EOD;
                  <input value="$username" type="text" name="username" class="form-control" placeholder="Username"/>
                  <input type="password" id="password" name="password" class="form-control" placeholder="Password"/>
EOD
    }
  print <<EOD;
<input type="submit" value="Login" class="btn btn-success btn-sm pull-right" />
EOD
    print qq(<input type="hidden" name="back" value="$back_html" />\n) if $back_html;
    print qq(</form>\n);
}
  print <<EOD;
</div>
</body>
</html>
EOD
}

# ------------------------------------------------------------------------
# Set the auth cookie and redirect to $back
sub set_cookie_redirect {
  my ($tkt, $bk, $systemcook) = @_;
  my @expires = $at->cookie_expires ?
    ( -expires => sprintf("+%ss", $at->cookie_expires) ) :
    ();
  my $cookie = CGI::Cookie->new(
    -name => $at->cookie_name,
    -value => $tkt,
    -path => '/',
    -secure => $at->require_ssl,
    @expires,
    @auth_domain
  );

  my $usercookie = CGI::Cookie->new(
    -name => 'tktuser',
    -value => $username,
    -path => '/',
    -secure => $at->require_ssl,
    @expires,
    @auth_domain
  );
  # Zap the guac cookie if redirecting to guacamole
  my $guaccookie = CGI::Cookie->new(
          -name => 'GUAC_AUTH',
          -value => '',
          -path => '/guacamole/'
  );

  #print header();
  #print "BACK: $back, ", $q->param($at->back_arg_name), ",", $at->back_arg_name, "\n";
  #my $installsystem = $q->param('installsystem');
  #my $systemcookie;
  #if ($installsystem) {
  #   $systemcookie = CGI::Cookie->new(
  #      -name => 'installsystem',
  #      -value => "$installsystem",
  #      -path => '/',
  #  );
  #}

 # If no $back, just set the auth cookie and hope for the best
  if (! $bk) {
    print $q->header( -cookie => [$cookie, $usercookie, $systemcook] );
    print $q->start_html, $q->p("Login successful"), $q->end_html;
    return 0;
  }

  my $bkobj = URI->new($bk);
  # If $back domain doesn't match $AUTH_DOMAIN, pass ticket via back GET param
  my $domain = $AUTH_DOMAIN || $server_name;
  if ($bkobj->host !~ m/\b$domain$/i) {
    $bk .= $bkobj->query ? '&' : '?';
    $bk .= $at->cookie_name . '=' . $tkt;
  }

  if ($q->param('api')) {
    print header(
        -content_type => "application/json",
        -cookie => [ $cookie, $usercookie, $systemcook ]
    );
    print qq|{"status": "OK", "cookie": "| . $at->cookie_name . qq|", "tkt": "$tkt"}\n|;
  } else {
    prepare_ui_update($username);
    $bk = '' if ($bk =~ /login/);
    my @cooks = [$cookie, $usercookie, $systemcook, $guaccookie];
#    push @cooks, $guaccookie if ($bk =~ /guacamole/);
    print redirect(
        -uri => $bk || '/stabile/',
        -cookie => @cooks,
    );
  }
  return 1;
};

sub trim($){
	my $string = shift;
	$string =~ s/^\s+//;
	$string =~ s/\s+$//;
	return $string;
}

sub prepare_ui_update {
  my $uname = shift;
  return unless $uname;
  # Update allowed port forwards and create links
  # AuthTktConfig::syslogit('info', "Now opening ssh ports for $uname...");
  # `/usr/local/bin/permitOpen "$uname"`;
  #mkpath('../cgi/ui_update') unless (-e '../cgi/ui_update');
  `/bin/ln -s ../ui_update.cgi ../cgi/ui_update/$uname~ui_update.cgi` unless (-e "../cgi/ui_update/$uname~ui_update.cgi");
  if ($session) {
    eval {
      `/bin/rm -f /tmp/$uname~*$session.*.tasks`; # Remove any tasks file from a previous session - no quotes
      `/usr/bin/pkill -f "$session."`;
      1;
    } or do {;};
  }
}