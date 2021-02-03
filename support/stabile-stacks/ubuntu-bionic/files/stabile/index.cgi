#!/usr/bin/perl

use Data::Dumper;
use Time::Local;
use Text::ParseWords;
use String::ShellQuote;
use File::Glob qw(bsd_glob);
require 'simplestack-lib.pl';

# Security check
if ((
        $ENV{REMOTE_ADDR} && ($ENV{REMOTE_ADDR} =~ /(^10\.\d+\.\d+\.\d+)/ || $ENV{REMOTE_ADDR} =~ /(^127\.0\.0\.1)/))
        || !$ENV{ANONYMOUS_USER}) {
; # OK
} else {
    print "Content-type: text/html\n\n";
    print qq|I'm sorry Dave, I'm afraid I can't do that $ENV{REMOTE_ADDR} $ENV{HTTP_X_FORWARDED_FOR}\n|;
    exit;
}

my $webminhome = '/usr/share/webmin';

# Globals
$internalip = get_internalip();
$externalip = get_externalip();
$appid = get_appid();

my $message;
#my $postscript;

# Read in libs for tabs
opendir(DIR,"tabs") or die "Cannot open tabs directory\n";
my @dir = readdir(DIR);
closedir(DIR);
sort @dir;
my @tabs;
my %tabsh;
push @tabs, 'security' if (-d "tabs/security");

my $appurl;
my $upgradeurl;
my $appinfo_ref = get_appinfo();
%appinfo = %$appinfo_ref;
if ($appid) {
    $appurl = "$appinfo{appstoreurl}#app-$appid";
    $upgradeurl = $appinfo{upgradelink};
}


my $spools_ref = list_simplestack_storagepools();
@spools = @$spools_ref;
$mounts = `cat /proc/mounts`;

foreach my $tab (@dir) {
    next if ($tab =~ /\./);
    push @tabs, $tab unless ($tab eq 'security');
    $tabsh{$tab} = $tab;
    require "tabs/$tab/$tab-lib.pl";
}

# Ask Webmin to parse input
ReadParse();

# If any input is submitted, perform requested actions

if ($in{action} && $in{tab} && $tabsh{$in{tab}}) {
    my $tab = $in{tab};
    my $res;
    $res = $tab->($in{action}, \%in) if (defined &$tab);
    if ($res =~ /^Content-type:/ || $res =~ /^X-ShellInABox/) { # Handle as JSON
        print $res;
        exit 0;
    } else { # Handle as regular cgi
        $message = $res;
    }
} elsif ($in{action} eq 'uninstall') {
    # Remove DNS entry if not a FQDN
    $message .= `curl -ks "https://$gw/stabile/networks?action=dnsdelete\&name=$externalip"` unless ($fname =~ /\./);
    # $message .= "<script>parent.systembuilder.system.close();</script>";
    # Look for more uninstall action at the end of this script

} elsif ($in{action} eq 'mountpools') {
    print "Content-type: application/json\n\n";
    my %activepools = mountPools();
#    print "Mounted storage pools:\n"
    print to_json(\%activepools, {pretty=>1 });
    exit 0;

} elsif ($in{action} eq 'initapps') {
    print "Content-type: text/html\n\n";
    for (my $i=0; $i <= 9; $i++) {
        next unless (-e "/mnt/fuel/pool$i");
        print "Cloning stabile-stacks from GitHub to /mnt/fuel/pool$i\n";
        mountPools();
        print `cd /mnt/fuel/pool$i; git clone https://github.com/origosys/stabile-stacks 2>&1`;
        last;
    }
    exit 0;

} elsif ($in{action} eq 'activateapps') {
    print "Content-type: text/html\n\n";
    print "Looking for images to activate\n";
    my $gpath = $in{path};
    for (my $i=0; $i <= 9; $i++) {
        next unless (-e "/mnt/fuel/pool$i");
        $gpath = "/mnt/fuel/pool$i/stabile-stacks/stabile-ubuntu/*.qcow2" unless ($gpath);
        for my $eachfile (glob($gpath)) {
            print "Trying to activate: $eachfile\n";
            print `curl -k "https://$gw/stabile/images?action=activate&image=$eachfile"`;
        }
        if (-e "/mnt/fuel/pool$i/images/") {
            $gpath = "/mnt/fuel/pool$i/images/*.qcow2" unless ($gpath);
            for my $eachfile (glob($gpath)) {
            print "Trying to activate: $eachfile\n";
                print `curl -k "https://$gw/stabile/images?action=activate&image=$eachfile"`;
            }
            $gpath = "/mnt/fuel/pool$i/images/*.vmdk" unless ($gpath);
            for my $eachfile (glob($gpath)) {
                print "Trying to activate: $eachfile\n";
                print `curl -k "https://$gw/stabile/images?action=activate&image=$eachfile"`;
            }
        }
    }
    exit 0;

} elsif ($in{action} eq 'upgrade') {
    print "Content-type: application/json\n\n";
    my $res;
    # Mount and prepare target dir
    my $json_text = `curl -ks "https://$gw/stabile/servers/this"`;
    my $rdom = from_json($json_text);
    my $uuid = $rdom->{uuid};
    my $dumploc;
    my $ok = 'OK';
    my %activepools = mountPools();
    foreach my $pool (values %activepools) {
        my $sid = $pool->{pool};
        if ($mounts =~ /\mnt\/fuel\/$sid/) { # pool mounted
            $dumploc = "/mnt/fuel/$sid/upgradedata/$uuid";
            `mkdir -p $dumploc`;
            $in{targetdir} = $dumploc;
            last;
        }
    }

    foreach my $tab (values %tabsh) {
        if (defined &$tab) {
            $tabres = $tab->('upgrade', \%in);
            $ok = 'ERROR' unless (!$tabres || $tabres =~ /^OK:/);
            $res .= "$tabres " if ($tabres);
        }
    }
    print qq|{"status": "$ok", "message": "$res"}|;
    exit 0;

} elsif ($in{action} eq  'savewebminservers') {
    print "Content-type: application/json\n\n";
    my $nets = list_simplestack_networks();
    foreach my $net (@$nets) {
        my $ip = $net->{internalip};
        my $res;
        if ($ip && $ip ne '--') {
            $res = save_webmin_server($ip);
        }
        print "OK: $res->{file}\n";
    }
    exit 0;

## This endpoint is used by stabile-ubuntu.pl, which is run as a startup script
} elsif ($in{action} eq 'savewebminserver') {
    my $ip = $in{ip};
    my $pass = $in{pass};
    $ip = $ENV{REMOTE_HOST} unless ($ip);
    print "Content-type: application/json\n\n";
    if ($ip) {
        $res = save_webmin_server($ip, $pass);
        print qq|{"status": "OK: $res->{file}"}|;
    } else {
        print qq|{"status": "No address"}|;
    }
    exit 0;

## This endpoint is used by stabile-ubuntu.pl, which is run as a startup script
} elsif ($in{action} eq 'registerwebminserver') {
    print "Content-type: application/json\n\n";
    my $mip;
    my $mserver = show_management_server();
    if ($mserver) {
        $mip = $mserver->{internalip};
    } elsif ($internalip) {
        $mip = $internalip;
        chomp $mip;
    }
    if (`grep admin /etc/webmin/miniserv.users`) {
        `perl -pi -e 's/admin\:.*/admin::0/' /etc/webmin/miniserv.users`;
    } else {
        `echo "admin::0" >> /etc/webmin/miniserv.users`;
    }
    if ($mip) {
        my $pass = `/usr/bin/openssl rand -base64 12`;
        chomp $pass;
        `$webminhome/changepass.pl /etc/webmin admin "$pass"`;
        $pass = uri_encode($pass);
        my $res = `curl "http://$mip:10000/stabile/index.cgi?action=savewebminserver&pass=$pass"`;
        print qq|[{"status": "OK: Registered at $mip"}, $res]|;
        # Jump through a few hoops to activate login
        $res = `curl -i -b testing=1 -d "user=admin&pass=$pass" -X POST "http://$internalip:10000/session_login.cgi"`;
        `curl -i -b testing=1 -d "user=admin&pass=$pass" -X POST "http://$internalip:10000/session_login.cgi"` unless ($res =~ /Set-Cookie: sid=/s);
    } else {
        print qq|{"status": "ERROR: Unable to locate admin server ip"}|;
    }
    exit 0;

}

# Show a specific tab in the UI
if ($in{show} || $in{tab}) {
    my $tab = $in{show} || $in{tab};
    my $tabname = $tab;
    $tabname =~ tr/\./_/;
    $postscript .= qq|\$('#nav-tabs a[href="#$tabname"]').tab('show'); console.log("showing $tabname");\n|;
}

# Render HTML for output

my $alert;
$alert = qq|<div id="alert">\n|;
if ($message) {
    $alert .= <<END
    <div class="alert palette palette-orange fade in">
          <button type="button" class="close" data-dismiss="alert">×</button>
          <strong>$message</strong>
    </div>
    </div>
END
;
}
$alert .= qq|</div>\n|;

my $applink = '';
$applink = qq|<li><a href="$appurl" target="_blank">About this stack</a></li>| if ($appurl);
my $upgradelink = '';
my $upgradebadge = '';
if ($upgradeurl) {
    if ($appinfo{version} lt $appinfo{currentversion}) {
        $upgradelink = qq|<li><a href="#" onclick="confirmAction('upgrade','Your system will be unavailable while upgrading!');"><span style="background-color: #e74c3c;" class="badge">!</span> Upgrade this system</a></li>|;
        $upgradebadge = qq|<span class="badge" style="background-color: #e74c3c; top:-3px; left: 6px;  position: relative;" title="Upgrade available ($appinfo{version} -> $appinfo{currentversion})">!</span>|;
    } else {
        $upgradelink = qq|<li><a href="#" onclick="confirmAction('upgrade','Your stack will be unavailable while reinstalling!');">Reinstall this stack</a></li>|;
    }
}

my $tabs_li;
foreach my $tab (@tabs) {
    my $liactive = qq|class="active"| if (lc $tab eq 'security');
    $tabs_li .= $tab->('tab') || qq|<li $liactive><a href="#$tab" data-toggle="tab">$tab</a></li>\n|;
}

my $term_li = <<END
                <li>
                    <a href="$appinfo{terminallink}/" target="_blank">
                        to the online terminal
                    </a>
                </li>
END
;
$term_li = '' unless ($appinfo{terminallink});

my $head = <<END
<!DOCTYPE html>
<html lang="en" style="overflow-x: hidden;">
<head>
    <meta charset="utf-8">
    <title>$appinfo{name}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- Loading Bootstrap -->
    <link href="bootstrap/css/bootstrap.css" rel="stylesheet">
    <!-- Loading Flat UI -->
    <link href="css/flat-ui.css" rel="stylesheet">
    <link rel="shortcut icon" href="images/icons/favicon.ico">
    <!-- link href='https://fonts.googleapis.com/css?family=Lato:400,700' rel='stylesheet' type='text/css' -->
    <link href='css/Lato.css' rel='stylesheet' type='text/css'>
    <link rel="stylesheet" type="text/css" href="css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="strength/strength.css">
    <link rel="stylesheet" href="font-awesome/css/font-awesome.min.css">
    <!-- HTML5 shim, for IE6-8 support of HTML5 elements. All other JS at the end of file. -->
    <!--[if lt IE 9]>
    <script src="js/html5shiv.js"></script>
    <script src="js/respond.min.js"></script>
    <![endif]-->

    <style type="text/css">
        .btn.disabled {
            pointer-events: auto;
        }
        .btn {
            margin:2px;
            line-height: 1.3;
        }
        .dropdown-menu {
            left:inherit;
            right:0;
            border-radius:4px!important;
        }
        .dropdown-toggle .caret {
            margin-left: 0!important;
        }
        .navbar {
            margin-bottom: 6px;
            padding-left: 5px;
        }
        .close {
            line-height: 0.7;
        }
        .alert {
            margin: 10px auto 5px auto;
        /*    position:absolute;
            top:420px;
            left: 12px; */
            width: 90%
        }
        td {
            padding:2px;
        }
        .dataTables_info {
            font-size: 70%;
            margin-top:0;
        }
        .dataTable th {
            border-bottom: 1px solid #CCCCCC !important;
        }
        .dataTable tr:hover {
            cursor: pointer;
        }
        .fade {
        }
        .nav-tabs > li > span {
            display:none;
            cursor:pointer;
            position:absolute;
            right: 8px;
            top: 8px;
            color: red;
            content: '\\00D7';
        }
        .nav-tabs > li:hover > span {
            display: inline-block;
        }

        .closeText:hover {
            display: inline-block;
        }
        .closeText {
            content: '\\00D7';
            margin-left:6px;
            cursor:pointer;
            position:absolute;
            right: 6px;
            top: 8px;
            color: red;
            display: none;
        }
    </style>
</head>
<body>
<div class="container app-container">
    <nav class="navbar navbar-default" role="navigation">
        <h4 style="display:inline-block; vertical-align:middle; margin-bottom:0;">
            <img src="images/ubuntu-logo.png" style="margin:0 6px 6px 12px; width:45px;"> Welcome to $appinfo{name}
        </h4>
        <span style="margin:5px 0 10px 0; position:relative; float: right;">
            <span class="dropdown" >
                <button class="btn btn-primary dropdown-toggle dropdown" data-toggle="dropdown">Go<span class="caret"></span></button>
                <span class="dropdown-arrow dropdown-arrow-inverse"></span>
                <ul class="dropdown-menu dropdown-inverse" id="go_ul">
                    <li>
                        <a href="http://$externalip/" target="_blank" id="currentwp">
                            to default website
                        </a>
                    </li>
$term_li
                    <li>
                        <a href="https://$externalip:10001/" target="_blank">
                            to the Webmin console
                        </a>
                    </li>
                </ul>
            </span>
            <span class="dropdown">
                $upgradebadge
                <button class="btn btn-info fui-gear dropdown-toggle" data-toggle="dropdown" style="display:inline-block; margin:8px 20px 8px 8px;">
                    <span class="caret"></span>
                </button>
                <span class="dropdown-arrow dropdown-arrow-inverse"></span>
                <ul class="dropdown-menu dropdown-inverse">
                    $applink
                    $upgradelink
                    <li><a href="#" onclick="confirmAction('uninstall','')">Uninstall this stack</a></li>
                </ul>
            </span>
        </span>
    </nav>
    <ul class="nav nav-tabs" id="nav-tabs">
$tabs_li
    </ul>
    <div class="tab-content" id="tab-content" style="margin-top:6px;">
END
;

my $tabs_js;
foreach my $tab (@tabs) {
    $tabs_js .= $tab->('js') . "\n";
}

my $footer = <<END
$alert
    </div>
</div>
<!-- /.container -->

<div class="modal" id="confirmdialog" tabindex="-1" role="dialog" aria-hidden="true">
  <div class="modal-dialog modal-sm">
    <div class="modal-content">
      <!-- div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
        <h4 class="modal-title" id="myModalLabel">Are you sure?</h4>
      </div -->
      <div class="modal-body" id="confirm-body">
        <h4 class="modal-title" id="myModalLabel">Are you sure?</h4>
        <div id="confirmdialog_warning">
            This will destroy data!
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-default" data-dismiss="modal" id="confirm-no">No</button>
        <button type="button" class="btn btn-primary" id="confirmed" onclick="confirmAction('doit','');">Yes - go ahead</button>
      </div>
    </div>
  </div>
</div>

<!-- Load JS here for greater good =============================-->
<script src="js/jquery-1.8.3.min.js"></script>
<script src="js/jquery-ui-1.10.3.custom.min.js"></script>
<script src="js/jquery.ui.touch-punch.min.js"></script>
<script src="js/bootstrap.min.js"></script>
<script src="js/bootstrap-select.js"></script>
<script src="js/bootstrap-switch.js"></script>
<script src="js/flatui-checkbox.js"></script>
<script src="js/flatui-radio.js"></script>
<script src="js/jquery.tagsinput.js"></script>
<script src="js/jquery.placeholder.js"></script>
<script type="text/javascript" charset="utf8" src="js/jquery.dataTables.min.js"></script>
<script type="text/javascript" src="strength/strength.js"></script>
<script src="js/Chart.js"></script>

<script type='text/javascript'>
    var timeout;
    var updating;
    var interval;
    var cmdtries = 0;
    var testtries = 0;

    window.onunload = function() {
        console.log("Clearing timeouts");
        clearTimeout(timeout);
        clearTimeout(interval);
    }

    \$(document).ready(function () {
        if (\$("[rel=tooltip]").length) {
            \$("[rel=tooltip]").tooltip({delay: { show: 500, hide: 100 }});
        };

        \$("select").selectpicker({style: 'btn-primary btn-hg'});
        \$(".alert").alert();
        window.setTimeout(function() { // hide alert message
            \$(".alert").removeClass('in');
            \$(".alert").hide();
        }, 5000);

        $postscript
    });

    function salert(message) {
        \$("#alert").html('<div class="alert palette palette-orange fade in"><button type="button" class="close" data-dismiss="alert">×</button><strong>' + message + '</strong></div>');
        window.setTimeout(function() { // hide alert message
            \$(".alert").removeClass('in');
            \$(".alert").hide();
        }, 5000);
    };

    function confirmAction(action, warning) {
        if (action == 'uninstall' || action == 'upgrade') {
            \$('#confirmdialog').prop('actionform', action);
            if (warning) \$('#confirmdialog_warning').html(warning);
            \$('#confirmdialog').modal({'backdrop': false, 'show': true});
            return false;
        } else if (action == 'doit') {
            actionform = \$('#confirmdialog').prop('actionform');
            console.log("Firing", actionform);
            if (actionform == 'uninstall') {
                // setTimeout(function(){parent.systembuilder.system.close()},1000);
                \$("#confirmed, #confirm-no").attr("disabled", true);
                \$("#confirm-body").html("<h4>Stack is being uninstalled...</h4>");
                jQuery.get('index.cgi?action=uninstall');
            } else if (actionform == 'upgrade') {
                parent.systembuilder.system.upgrade("$internalip");
            } else {
                if (\$.isFunction(window[actionform])) {
                    window[actionform]();
                } else {
                    console.log("Submitting", actionform);
                    \$(actionform).submit();
                }
                \$('#confirmdialog').modal('hide');
            }
            return true;
        }
    };

    function spinner(item) {
        \$(item).prop("disabled", true ).html(\$(item).html() + ' <i class="fa fa-cog fa-spin"></i>');
        return false;
    }

    $tabs_js;

</script>
</body>
</html>
END
;

print "Content-type: text/html\n\n";
print $head;

foreach my $tab (@tabs) {
    print $tab->('form');
}

print $footer;

# This needs to go after printing out HTML, since server cannot print out after it is destroyed
if ($in{action} eq 'uninstall') {
    `curl -sk https://$gw/stabile/systems?action=removesystem`;

} elsif ($in{action} eq 'upgrade') {
    ;
}

# Mount storage pools and return hash with details
sub mountPools {
#    my $elfinderlinks;
    my %activepools;
    foreach my $pool (@spools) {
        next if ($pool->{id} == -1);
        next unless ($pool->{mountable});

        my $sid = "pool" . $pool->{id};
        my $sname = $pool->{name};
        my $spath = $pool->{path};
        my $shostpath = $pool->{hostpath};

        $activepools{$pool->{id}}->{id} = $pool->{id};
        $activepools{$pool->{id}}->{pool} = $sid;
        $activepools{$pool->{id}}->{name} = $sname;
        $activepools{$pool->{id}}->{path} = $spath;
        $activepools{$pool->{id}}->{hostpath} = $shostpath;

        # $elfinderlinks .= qq|<li><a href="#" onclick='openElfinder("$sid", "$suuid", "$sname");'>Files on $sname ($sid)</a></li>|;

        unless ($mounts =~ /\/mnt\/fuel\/$sid/) {
            `mkdir -p /mnt/fuel/$sid` unless (-e "/mnt/fuel/$sid");
            `ln -s /mnt/fuel /usr/share/webmin/stabile/fuel` unless (-e "/usr/share/webmin/stabile/fuel");
            my $me_ref =show_me();
            $user = $me_ref->{username};
            if ($shostpath eq 'local') {
                `mount $gw:$spath/$user/fuel /mnt/fuel/$sid`;
            } else {
                `mount $shostpath/$user/fuel /mnt/fuel/$sid`;
            }
            my $i = 0;
            $mounts = `cat /proc/mounts`;
            while (!($mounts =~ /\/mnt\/fuel/)) {
                sleep 1;
                $i++;
                $mounts = `cat /proc/mounts`;
                last if ($i >9);
            }
        }
    }
    return %activepools;
}
