#!/usr/bin/perl -UTw
#
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

$ENV{PATH} = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin';
delete @ENV{'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};

use File::Basename;
#use lib dirname($ENV{SCRIPT_FILENAME});
use lib '/var/www/auth';
use Apache::AuthTkt 0.03;
use AuthTktConfig;
use CGI qw(:standard);
use CGI::Cookie;
use URI::Escape;
use URI;
use JSON;
use Digest::SHA qw(sha256_base64);
use strict;
use Expect;


# ------------------------------------------------------------------------
# Configuration settings in AuthTktConfig.pm

# ------------------------------------------------------------------------
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
$back ||= $AuthTktConfig::DEFAULT_BACK_LOCATION if $AuthTktConfig::DEFAULT_BACK_LOCATION;
$back ||= $ENV{HTTP_REFERER} if $ENV{HTTP_REFERER} && $AuthTktConfig::BACK_REFERER;
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

my ($fatal, @errors, @messages);
my ($mode, $location, $suffix) = fileparse($ENV{SCRIPT_NAME}, '\.cgi', '\.pl');
$mode = 'login' unless $mode eq 'guest' || $mode eq 'autologin' || $mode eq 'changepwd';
my $self_redirect = $q->param('redirect') || 0;
my $username = lc($q->param('username'));
my $password = $q->param('password');
my $timeout = $q->param('timeout');
my $unauth = $q->param('unauth');
push @messages, $q->param('message') if ($q->param('message'));
my $ip_addr = $at->ignore_ip ? '' : $ENV{REMOTE_ADDR};
#my $ip_addr = $ENV{REMOTE_ADDR};
my $redirected = 0;

# ------------------------------------------------------------------------
# Set the auth cookie and redirect to $back
my $set_cookie_redirect = sub {
  my ($tkt, $back) = @_;
  my @expires = $at->cookie_expires ? 
    ( -expires => sprintf("+%ss", $at->cookie_expires) ) :
    ();
  my $cookie = CGI::Cookie->new(
    -name => $at->cookie_name,
    -value => $tkt, 
    -path => '/',
    -secure => $at->require_ssl,
    @expires,
    @auth_domain,
  );

  # If no $back, just set the auth cookie and hope for the best
  if (! $back) {
    print $q->header( -cookie => $cookie );
    print $q->start_html, $q->p(Login successful), $q->end_html;
    return 0;
  }

  # Set (local) cookie, and redirect to $back
  print $q->header( -cookie => $cookie );
  return 0 if $AuthTktConfig::DEBUG;

  my $b = URI->new($back);
  # If $back domain doesn't match $AUTH_DOMAIN, pass ticket via back GET param
  my $domain = $AUTH_DOMAIN || $server_name;
  if ($b->host !~ m/\b$domain$/i) {
    $back .= $b->query ? '&' : '?';
    $back .= $at->cookie_name . '=' . $tkt;
  }

  # For some reason, using a Location: header doesn't seem to then see the 
  #   cookie, but a meta refresh one does - weird
  print $q->start_html(
    -head => meta({ -http_equiv => 'refresh', -content => "0;URL=$back" }),
    ), 
    $q->end_html;
  return 1;
};

# ------------------------------------------------------------------------
# Actual processing

# If no cookies found, first check whether cookies are supported
if (! $have_cookies) {
  # If this is a self redirect warn the user about cookie support
  if ($self_redirect) {
    $fatal = "Your browser does not appear to support cookies or has cookie support disabled.<br />\nThis site requires cookies - please turn cookie support on or try again using a different browser.";
  }
  # If no cookies and not a redirect, redirect to self to test cookies
  else {
    my $extra = '';
    $extra .= 'timeout=1' if $timeout;
    $extra .= 'unauth=1' if $unauth;
    $extra = "&$extra" if $extra;
    print $q->header(
      -cookie => CGI::Cookie->new(-name => 'auth_probe', -value => 1, @auth_domain),
    );
    # For some reason, a Location: redirect doesn't seem to then see the cookie,
    #   but a meta refresh one does - go figure
    print $q->start_html(
      -head => meta({
        -http_equiv => 'refresh', -content => ("0;URL=" . sprintf("%s%s%s?redirect=%s&%s=%s%s",
          $location, $mode, $suffix, $self_redirect + 1, $at->back_arg_name, 
          $back_esc || '', $extra))
    }));
    $redirected = 1;
  }
}

elsif ($mode eq 'autologin') {
  # If we have a ticket, redirect to $back, including ticket as GET param
  if ($ticket && $back && ! $timeout) {
    my $b = URI->new($back);
    $back .= $b->query ? '&' : '?';
    $back .= $at->cookie_name . '=' . $ticket;
    redirect($back);
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
  }
  elsif ($mode eq 'login') {
    if ($username) {
        if ($username eq 'g') { # Obsolete block
            my $tokens;
            my $btjson = `curl --silent "http://localhost:8888/api?method=get_folders"`;
            my $bthashref = from_json($btjson);
            my @folders = @{ $bthashref };
            my %bthash = map { $_->{secret} => $_->{dir} } @folders;
            if ($bthash{$password} || $bthash{sha256_base64($password)}) {
                my $user_data = join(':', time(), ($ip_addr ? $ip_addr : ''), $bthash{$password});
                my $tkt = $at->ticket(uid => $username, data => $user_data,
                  ip_addr => $ip_addr, tokens =>$tokens, debug => $AuthTktConfig::DEBUG);
                if (! @errors) {
                  $redirected = $set_cookie_redirect->($tkt, $back);
                  $fatal = "Login successful.";
                }
            }
        } else {
          my ($valid, $tokens) = $AuthTktConfig::validate_sub->($username, $password);
          if ($valid) {
    #       my $user_data = join(':', encrypt($password), time(), ($ip_addr ? $ip_addr : ''));
            my $user_data = join(':', time(), ($ip_addr ? $ip_addr : ''));    # Optional
            my $tkt = $at->ticket(uid => $username, data => $user_data,
              ip_addr => $ip_addr, tokens => $tokens, debug => $AuthTktConfig::DEBUG);
            if (! @errors) {
              $redirected = $set_cookie_redirect->($tkt, $back);
              $fatal = "Login successful.";
            }
          }
          else {
            push @errors, "Invalid username or password.";
          }
      }
    }
  }
  elsif ($mode eq 'changepwd') {
      if ($username && $password) {
          my $newpassword;
          if ($q->param('newpassword') && $q->param('newpassword') eq $q->param('newpassword2')) {
              $newpassword = $q->param('newpassword');
              my ($valid, $tokens) = $AuthTktConfig::validate_sub->($username, $password);
              if ($valid) {
                my $res = changeSambaPassword($username, $newpassword);
                push @errors, $res if ($res);
                if (! @errors) {
                  $fatal = "Password change successful!";
                  redirect(
                    "/auth/login.cgi?message=" . uri_escape($fatal)
                  );
                  $redirected = 1;
                }
              } else {
                push @errors, "Invalid username or password.";
              }
          } else {
                push @errors, "Passwords don't match!";
          }
      }
  }
  elsif ($mode eq 'guest') {
    # Generate a guest ticket and redirect to $back
    my $tkt = $at->ticket(uid => $AuthTktConfig::guest_sub->(), ip_addr => $ip_addr);
    if (! @errors) {
      $redirected = $set_cookie_redirect->($tkt, $back);
      $fatal = "No back link found.";
    }
  }
}

my @style = ();
@style = ( '-style' => { src => $AuthTktConfig::STYLESHEET } )
  if $AuthTktConfig::STYLESHEET;
my $title = $AuthTktConfig::TITLE || "\u$mode Page";
unless ($redirected) {
    my $error_msg = "Authorized use only";
    $error_msg = join(" ", @messages) if (@messages);
    $error_msg = join(" ", @errors) if (@errors);

    my $back = $back_html;
    $back = $1 if ($back =~ /(.+)index\.php$/);

    my $pwdfields = <<END
                    <tr><th style="text-align:right;">Password:</th><td><input type="password" name="password"  style="width:200px;" /></td></tr>
                    <tr><td colspan="2">
                    <button class="btn btn-default pull-right" type="submit">Login</button>
                    <br clear="both"><a class="small pull-right" style="font-size:70%; color:grey; margin-top:8px;" href="changepwd.cgi">change password</a>
END
;
    $pwdfields = <<END
                    <tr><th style="text-align:right;">Current password:</th><td><input type="password" name="password"  style="width:200px;" /></td></tr>
                    <tr><th style="text-align:right;">New password:</th><td><input type="password" name="newpassword"  style="width:200px;" /></td></tr>
                    <tr><th style="text-align:right;">New password (confirm):</th><td><input type="password" name="newpassword2"  style="width:200px;" /></td></tr>
                    <tr><td colspan="2">
                    <button class="btn btn-default pull-right" type="submit">Change</button>
                    <br clear="both"><a class="small pull-right" style="font-size:70%; color:grey; margin-top:8px;" href="login.cgi">log in</a>
END
if ($mode eq 'changepwd');

    my $elfinder = <<END
Content-type: text/html; charset=utf-8
Set-Cookie: auth_tkt=; Expires=Thu, 01-Jan-1970 00:00:01 GMT; Path=/;
Set-Cookie: auth_probe=1; Path=/;

<!DOCTYPE html
PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en-US" xml:lang="en-US">
<head>
    <title>Log in</title>
    <script type="text/javascript">//<![CDATA[

        function getFocus() {
            document.forms[0].elements[0].focus();
            document.forms[0].elements[0].select();
        }
    //]]></script>
    <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="/origo/elfinder/bootstrap/css/bootstrap.css" rel="stylesheet">
    <link href="/origo/elfinder/css/flat-ui.css" rel="stylesheet">
    <link rel="shortcut icon" href="/origo/elfinder/images/icons/favicon.ico">
    <link rel="stylesheet" href="/origo/elfinder/strength/strength.css">
    <link href='https://fonts.googleapis.com/css?family=Lato:400,700' rel='stylesheet' type='text/css'>
</head>
<body onload="getFocus()">
    <div style="width:600px; margin: 10px auto 0 auto; padding:6px;" class="panel panel-default">
        <nav role="navigation" class="navbar navbar-default">
            <h4 style="display:inline-block; vertical-align:middle;">
                <img width="38" height="43" style="margin:0 6px 6px 12px;" src="/origo/elfinder/img/origo-gray.png">File Browser
            </h4>
            <div class="label label-warning pull-right" style="white-space:normal;">$error_msg</div>
        </nav>
        <div align="center">
            <form name="login" method="post" noaction="/auth/login.cgi" class="passwordform" style="margin:10px;">
                <table style="border-spacing: 6px; border-collapse: separate;">
                    <tr><th style="text-align:right;">Username:</th><td><input type="text" name="username" style="width:200px;" /></td></tr>
$pwdfields
                    </td></tr>
                </table>
                <input type="hidden" name="back" value="$back" />
            </form>
        </div>
    </div>
</body>
</html>
END
;
    print $elfinder;


}

sub changeSambaPassword {
    my ($username, $newpassword) = @_;
    my $error;
    my $smbpasswd="/usr/bin/suid-smbpasswd";

    if (!$error ) { #&& $samba_user_check->expect(30, '-re', "$username:*")) {
        my $samba_passwd=Expect->spawn("$smbpasswd $username");
        $samba_passwd->slave->stty(qw(-echo));
        $samba_passwd->log_stdout(0);
        if ($samba_passwd) {
            unless($samba_passwd->expect(30, "New SMB password:")) { $error =  "Unable to change password!"; }
            print $samba_passwd "$newpassword\n";

            unless($samba_passwd->expect(30, "Retype new SMB password:")) { $error = "Unable to change password."; }
            print $samba_passwd "$newpassword\n";

            if ($samba_passwd->expect(30, '-re', "Failed to modify account")) { $error =  "ERROR: ". $samba_passwd->after(); }
            chomp $error if ($error);

            #Must soft close this file handle otherwise on some system
            #command may fail to complete.
            $samba_passwd->soft_close();
            `/etc/init.d/samba4 restart` unless ($error);
        } else {
            $error =  "Unable to start smbpasswd!";
        }

    }
    return $error;
}


